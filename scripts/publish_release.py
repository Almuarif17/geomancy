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
    if not tok:
        sys.exit("no token: run as  GH_TOKEN=... python3 scripts/publish_release.py " + a.tag)
    H = {"Authorization": "token " + tok, "Accept": "application/vnd.github+json", "User-Agent": "geomancy-publish"}

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
                 "library/tools/finalize_dataset.py", "engine/evaluate.py --json library/dataset/evaluation.json"):
        out = sh("python3", *step.split())
        print("   ", step.split()[0].split("/")[-1], "->", (out.strip().splitlines() or ["(ok)"])[-1][:100])
    print("   validate:", sh("python3", "library/tools/validate.py").strip().splitlines()[-1])
    dirty = sh("git", "status", "--porcelain").strip()
    if dirty and not a.dry_run:
        print("   committing regenerated artefacts")
        sh("git", "add", "-A")
        sh("git", "-c", "user.name=Ahmad", "-c", "user.email=ahmad.muarif17@gmail.com",
           "commit", "-q", "-m", f"release {a.tag}: regenerated dataset artefacts")
    if a.dry_run:
        print("[dry-run] would tag " + a.tag + ", push main+tag, build 6 assets, upload, verify"); return 0

    print("[2/6] tag + push")
    sh("git", "tag", "-a", a.tag, "-m", f"geomancy-library {a.tag}", "--force")
    print("   ", sh("git", "push", "-f", "origin", "main").strip() or "main pushed")
    print("   ", sh("git", "push", "-f", "-q", "origin", f"refs/tags/{a.tag}").strip() or f"{a.tag} pushed")

    print("[3/6] build assets")
    A = ROOT.parent / "release-assets"; A.mkdir(exist_ok=True)
    for f in os.listdir(A):
        os.remove(A / f)
    v = a.tag
    names = {"geomancy-dataset-%s.tar.gz" % v: f"tar --exclude='*.sqlite' -czf $OUT geomancy-dataset-{v}.tar.gz -C library dataset",
             "geomancy-%s.sqlite" % v: f"cp library/dataset/geomancy.sqlite $OUT",
             "geomancy-passages-%s.jsonl" % v: "cp library/dataset/shards/passages.jsonl $OUT",
             "geomancy-by-outcome-%s.jsonl" % v: "cp library/dataset/index/by_outcome.jsonl $OUT",
             "geomancy-%s.d.ts" % v: "cp types/geomancy.d.ts $OUT"}
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
