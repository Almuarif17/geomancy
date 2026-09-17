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
import argparse, json, os, pathlib, subprocess, sys, urllib.request, urllib.error

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

def sh(*cmd: str, check: bool = True) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"FAILED: {' '.join(cmd)}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return (r.stdout or "") + (r.stderr or "")


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
                 + " file(s), e.g. " + ", ".join(l[3:].strip() for l in moved[:3])
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
    sh("git", "tag", "-a", a.tag, "-m", f"geomancy-library {a.tag}", "--force")
    print("   ", sh("git", "push", "-f", "origin", "main").strip() or "main pushed")
    print("   ", sh("git", "push", "-f", "-q", "origin", f"refs/tags/{a.tag}").strip() or f"{a.tag} pushed")

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
