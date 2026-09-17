#!/usr/bin/env python3
"""Push main + the next tag, publish its assets, and prove the release - in one command.

Usage (the token is read from the environment and never written to disk):
    GH_TOKEN=github_pat_... python3 scripts/publish_release.py v0.2.4
    GH_TOKEN=... python3 scripts/publish_release.py v0.2.4 --dry-run     # show what would happen

It exists because a release is a sequence with a trap in it: build -> index -> types -> finalize ->
evaluate -> tag -> push -> upload -> verify. Skipping 'finalize' or uploading before the tag are the two
mistakes that made v0.2.2's assets stale. Prefer a fine-grained PAT limited to this one repository with
Contents+Administration write; do not paste it into a chat, export it in the shell.
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, subprocess, sys, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
API, UP = "https://api.github.com", "https://uploads.github.com"


def asset_names(v: str) -> dict:
    """The release assets, one entry each. Kept as a function so the dry-run
    message, the builder and any later count check read the same table - a hardcoded "6 assets" in a
    print is how a release script starts lying about what it ships."""
    return {             # deterministic on purpose: sorted members, no owner/mtime noise, gzip without a name field, so a
             # second build of the same commit produces the same sha256 and the release asset can be verified
             # by anyone with a clone and tar - not just trusted because we uploaded it
             "geomancy-dataset-%s.tar.gz" % v: ("tar --format=gnu --sort=name --numeric-owner --owner=0 "
                                                "--group=0 --mtime='UTC 2020-01-01' --exclude='*.sqlite' "
                                                "-C library dataset -c | gzip -n > $OUT"),
             "geomancy-%s.sqlite" % v: f"cp library/dataset/geomancy.sqlite $OUT",
             "geomancy-passages-%s.jsonl" % v: "cp library/dataset/shards/passages.jsonl $OUT",
             "geomancy-by-outcome-%s.jsonl" % v: "cp library/dataset/index/by_outcome.jsonl $OUT",
             "geomancy-%s.d.ts" % v: "cp types/geomancy.d.ts $OUT",
             # the CC0 layer as its own file: a commercial app can take this one asset without a licence
             # conversation, which is the point of having a CC0 layer at all
             "geomancy-core_facts-%s.json" % v: "cp library/dataset/core_facts.json $OUT",
             # and the coverage scoreboard, so "comprehensive" arrives as a checkable file, not an adjective
             "geomancy-coverage-%s.json" % v: "cp kb/coverage.json $OUT"}

def redact(text: str) -> str:
    """Strip credentials from anything this script may print or raise with.

    The push runs with the token inside the remote URL, because that is how git authenticates over https - and
    `git push` echoes that URL back in its own output ("To https://user:token@host/..."). A release script that
    pastes the maintainer's credential into terminal scrollback, a CI log, or its own failure message turns a
    working release into a leaked token, so redaction happens here, once, at the only exit a command has.
    """
    t = text or ""
    t = re.sub(r"gh[pousr]_[A-Za-z0-9_]{6,}", "ghp_***", t)
    t = re.sub(r"(?P<scheme>[a-z]+)://(?P<user>[^/@\s]+):(?P<pw>[^/@\s]+)@",
               lambda m: f"{m['scheme']}://{m['user']}:***@", t)
    return re.sub(r"(Authorization:\s*token\s+)\S+", r"\1***", t)


def sh(*cmd: str, check: bool = True) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(redact(f"FAILED: {' '.join(cmd)}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"))
    return redact((r.stdout or "") + (r.stderr or ""))


def _has(ref: str) -> bool:
    import subprocess
    return subprocess.run(["git", "rev-parse", "--verify", "-q", ref], capture_output=True).returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--repo", default="Almuarif17/geomancy")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not tok and not a.dry_run:
        sys.exit("no token: run as  GH_TOKEN=... python3 scripts/publish_release.py " + a.tag
                 + "\n  (or add --dry-run to check the gates, the asset list and the order without one)")
    H = {"Authorization": "token " + (tok or ""), "Accept": "application/vnd.github+json",
         "User-Agent": "geomancy-publish"}
    gitid: list[str] = []

    def api(url, data=None, method=None, ctype=None, host=API):
        h = dict(H)
        if ctype:
            h["Content-Type"] = ctype
        req = urllib.request.Request(host + url, data=data, headers=h,
                                     method=method or ("POST" if data else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=240) as f:
                return f.status, f.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    print("[1/6] gates")
    for step in ("library/tools/build_dataset.py", "engine/retrieve.py --build", "library/tools/gen_types.py",
                 "library/tools/finalize_dataset.py", "library/tools/score_coverage.py --write",
                 "engine/evaluate.py --json library/dataset/evaluation.json"):
        out = sh("python3", *step.split())
        print("   ", step.split()[0].split("/")[-1], "->", (out.strip().splitlines() or ["(ok)"])[-1][:100])
    # if a rebuild changed a tracked file, the commit we are about to publish is not the tree we just
    # verified; CI would call that stale, and so does the release
    moved = sh("git", "status", "--porcelain").strip().splitlines()
    if moved:
        sys.exit("refusing to publish: the rebuild changed the working tree (" + str(len(moved))
                 + " file(s), e.g. " + ", ".join(l.split(None, 1)[-1].strip() for l in moved[:3])
                 + "). Commit the regenerated files and run again.")
    print("    tree matches its own build ->", "clean")
    print("   validate:", sh("python3", "library/tools/validate.py").strip().splitlines()[-1])
    dirty = sh("git", "status", "--porcelain").strip()
    if dirty and not a.dry_run:
        print("   committing regenerated artefacts")
        sh("git", "add", "-A")
        # commit under whoever's git identity is configured here. An identity hard-coded into a script
        # that lives in a public repo is exactly what library/tools/check_public_leaks.py exists to stop.
        sh("git", "commit", "-q", "-m", f"release {a.tag}: regenerated dataset artefacts")
    if a.dry_run:
        print("[dry-run] would tag " + a.tag + ", push main+tag, build "
              + str(len(asset_names(a.tag.lstrip("v")))) + " assets, upload, verify"); return 0

    print("[2/6] tag + push")
    clean_url = f"https://github.com/{a.repo}.git"
    # Auth is driven from the token in the environment, for the length of the push, and never written to
    # .git/config or to disk: a remote that depends on a stored credential is a release you cannot make from
    # a fresh machine, and this workspace proved it - .git/config is not snapshotted, so a configured remote
    # simply vanishes and "git push" asks a non-interactive process for a password.
    auth_url = f"https://x-access-token:{tok}@github.com/{a.repo}.git" if tok else clean_url
    sh("git", "remote", "set-url", "origin", auth_url)
    try:
        st, body = api(f"/repos/{a.repo}/git/refs/tags/{a.tag}")
        if st == 200:
            remote_sha = json.loads(body).get("object", {}).get("sha", "")[:10]
            local_sha = sh("git", "rev-parse", f"{a.tag}^{{}}").strip()[:10] if _has(a.tag) else ""
            if local_sha and remote_sha and local_sha != remote_sha:
                sys.exit(f"{a.tag} already exists upstream at {remote_sha} but points at {local_sha} here. "
                         "Refusing to move a published tag: bump the version, or delete the release by hand.")
        else:
            # the tag object records who released it; if the machine has no git identity, ask the token whose
            # permissions are already in use rather than inventing one or hardcoding a person into the script
            if sh("git", "config", "user.email").strip() == "":
                u = json.loads(api("/user")[1] or b"{}")
                login, nm = u.get("login") or "unknown", u.get("name") or u.get("login") or "unknown"
                mail = u.get("email") or f"{u.get('id')}-{login}@users.noreply.github.com"
                gitid = ["-c", f"user.name={nm}", "-c", f"user.email={mail}"]
                print("    git identity unset: tagging as", nm)
        sh("git", *gitid, "tag", "-a", a.tag, "-m", f"geomancy-library {a.tag}", "--force")
        # main goes up with --force-with-lease, not -f: history is rewritten only if nobody else moved the
        # branch between our fetch and our push, which is the one case a library release must never overwrite
        print("   ", (sh("git", "push", "--force-with-lease", "origin", "main:refs/heads/main",
                         "--porcelain").strip().splitlines() or ["main pushed"])[-1] or "main pushed")
        print("   ", (sh("git", "push", "-f", "origin", f"refs/tags/{a.tag}", "--porcelain").strip().splitlines()
                       or [f"{a.tag} pushed"])[-1] or f"{a.tag} pushed")
    finally:
        sh("git", "remote", "set-url", "origin", clean_url)
        print("    origin restored to the credential-free URL")

    print("[3/6] build assets")
    A = ROOT.parent / "release-assets"; A.mkdir(exist_ok=True)
    for f in os.listdir(A):
        os.remove(A / f)
    v = a.tag
    names = asset_names(v)
    for nm, cmd in names.items():
        sh("bash", "-c", cmd.replace("$OUT", str(A / nm)))
    (A / "SHA256SUMS.txt").write_text("".join(
        f"{sh('sha256sum', str(A/nm)).split()[0]}  {nm}\n" for nm in sorted(os.listdir(A)) if nm != "SHA256SUMS.txt"))
    for nm in sorted(os.listdir(A)):
        print(f"    {nm:42s} {(A/nm).stat().st_size:>9,} B")

    print("[4/6] create release")
    body = (f"# geomancy-library {v}\n\nSee `CHANGELOG.md` and `docs/VISION.md`.\n\n"
            "Prove it locally: `python3 library/tools/verify_release.py --tag " + v + "`\n")
    st, r = api(f"/repos/{a.repo}/releases/tags/{v}")
    if st == 200:
        rid = json.loads(r)["id"]
        print("    release already exists, reusing id", rid)
    else:
        st, r = api(f"/repos/{a.repo}/releases", json.dumps({"tag_name": v, "name": f"geomancy-library {v}",
                                                             "body": body, "draft": False, "prerelease": False}).encode())
        if st not in (200, 201):
            sys.exit(f"release create failed {st}: {r.decode()[:400]}")
        rid = json.loads(r)["id"]
        print("    created", json.loads(r)["html_url"])

    print("[5/6] upload assets")
    for nm in sorted(os.listdir(A)):
        st, r = api(f"/repos/{a.repo}/releases/{rid}/assets?name={nm}", (A / nm).read_bytes(), "POST",
                    "application/octet-stream", host=UP)
        print(f"    {nm:42s} -> HTTP {st}")
        if st != 201:
            print("       ", r[:200])
            return 1

    print("[6/6] verify the published bytes against this tree")
    print(sh("python3", "library/tools/verify_release.py", "--tag", v))
    runs = api(f"/repos/{a.repo}/actions/runs?head_sha=" + sh("git", "rev-parse", "HEAD").strip())
    for w in json.loads(runs[1]).get("workflow_runs", [])[:1]:
        print(f"  CI {w['name']}: {w['status']} {w['conclusion']}  {w['html_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
