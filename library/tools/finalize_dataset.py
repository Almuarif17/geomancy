#!/usr/bin/env python3
"""Close the digest loop: manifest.json after the indexes, bundles.json after the manifest.

Build order matters here. build_dataset.py hashes the index files; engine/retrieve.py --build then
rewrites them; and bundles.json digests manifest.json. Run this as the last build step and a fresh clone
reproduces the shipped tree byte-for-byte, which is what the CI guard "Generated artefacts must be
committed" checks. Doing it in the wrong order is how v0.2.1-v0.2.2 CI went red while every local gate
passed: the shipped manifests described an older build.
"""
from __future__ import annotations
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def run(*cmd: str) -> None:
    r = subprocess.run([sys.executable, *cmd], cwd=ROOT)
    if r.returncode:
        sys.exit(f"FAILED: {' '.join(cmd)}")


run("library/tools/build_dataset.py", "--manifest-only")
run("engine/retrieve.py", "--bundles-only")
print("dataset is finalised: manifest then bundles, in that order")
