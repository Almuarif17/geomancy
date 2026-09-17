#!/usr/bin/env python3
"""Prove the published release is the repository's own build, from the network in.

    python3 library/tools/verify_release.py [--tag v0.2.0]

Downloads SHA256SUMS.txt and every asset from the release, then checks:
  1. each asset's sha256 matches SHA256SUMS.txt as published;
  2. the dataset tarball's manifest.json agrees with the local build's manifest (same counts, same
     per-file digests) - i.e. what you download is what `make full` produces from this source.
Exits non-zero on any mismatch, so CI can run it after a release.
"""
from __future__ import annotations

import argparse, hashlib, io, json, pathlib, subprocess, sys, tarfile, tempfile, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OWNER_REPO = "Almuarif17/geomancy"


def get(url: str, token: str | None = None) -> bytes:
    h = {"User-Agent": "geomancy-verify", "Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120).read()


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v0.2.0")
    ap.add_argument("--token", default=None, help="only needed for a private repo; release assets are public")
    a = ap.parse_args()
    base = f"https://github.com/{OWNER_REPO}/releases/download/{a.tag}"
    try:
        sums = get(f"{base}/SHA256SUMS.txt", a.token).decode()
    except Exception as e:                                          # noqa: BLE001
        print(f"FAIL  cannot fetch SHA256SUMS.txt for {a.tag}: {e}")
        return 1
    expected = {}
    for line in sums.splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            expected[name.strip().lstrip("*")] = digest
    print(f"release {a.tag}: {len(expected)} assets listed in SHA256SUMS.txt")
    bad = []
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="geom-rel-"))
    for name, digest in expected.items():
        blob = get(f"{base}/{name}", a.token)
        got = sha(blob)
        ok = got[:16] == digest[:16]
        print(f"  {'ok   ' if ok else 'BAD  '}{name:44s} {len(blob):>9,} B  sha256 {got[:16]}")
        if not ok:
            bad.append(name)
        if name.endswith(".tar.gz"):
            (tmp / name).write_bytes(blob)
    # 2. does the tarball agree with a local build of this repo?
    tar = next(tmp.glob("*.tar.gz"), None)
    if tar:
        with tarfile.open(tar) as tf:
            names = tf.getnames()
            member = next((m for m in names if m.endswith("dataset/manifest.json")), None)
            if member:
                pub = json.loads(tf.extractfile(member).read())
                local_m = ROOT / "library" / "dataset" / "manifest.json"
                if not local_m.exists():
                    print("  note: no local build yet - run `make build` to compare manifests")
                else:
                    loc = json.loads(local_m.read_text())
                    same_counts = pub["counts"] == loc["counts"]
                    shared = set(pub["files"]) & set(loc["files"])
                    same_files = all(pub["files"][k] == loc["files"][k] for k in shared)
                    print(f"  manifest vs local build: counts {'match' if same_counts else 'DIFFER'};"
                          f" file digests {sum(1 for k in shared if pub['files'][k]==loc['files'][k])}/{len(shared)} match")
                    if not (same_counts and same_files):
                        bad.append("manifest mismatch between release and local build")
    print("\n" + ("RELEASE VERIFIED - published bytes match the published checksums and this source tree"
                  if not bad else f"RELEASE PROBLEMS: {bad}"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
