#!/usr/bin/env python3
"""Licence-scope gate: every tracked path belongs to exactly one declared layer.

A licence that lives only in a README paragraph is a wish. `LICENSING.md` carries a fenced `scope` block,
one line per layer, `LAYER-glob,glob,...`, and this script enforces three things:

  * **no orphans** - a tracked file that no layer claims is silently MIT, which is precisely how the curated
    layer used to be licensed "CC BY 4.0" in prose while the code licence covered it in law;
  * **no double claims** - a file in two layers has no determinable licence;
  * **the CC0 layer stays small and true** - `library/dataset/core_facts.json` is the only CC0 file, it
    must exist, must declare `CC0-1.0` internally, and must contain only definitions and arithmetic.

Adding a directory is therefore a licensing decision with a failing build until it is made, not a
footnote someone notices in a year.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIC = ROOT / "LICENSING.md"

# repo furniture that carries no data licence: legal/infra/meta files, deliberately exempt
META = {"LICENSE", "LICENSE.md", "LICENSING.md", "LICENSE_DATA.md", "LICENSE_POLICY.md", ".gitignore",
        ".gitattributes", ".editorconfig", "requirements.txt", "SECURITY.md", "PRIVACY.md", "UPSTREAM.md",
        "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", ".pre-commit-config.yaml", "NOTICE"}


def scope() -> dict[str, list[str]]:
    txt = LIC.read_text()
    block = txt.split("```scope", 1)[1].split("```", 1)[0]
    out: dict[str, list[str]] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        layer, _, globs = line.partition("=")
        out[layer.strip()] = [g.strip() for g in globs.split(",") if g.strip()]
    return out


def matches(path: str, globs: list[str]) -> list[str]:
    hit = []
    for g in globs:
        if g.endswith("/"):
            if path.startswith(g):
                hit.append(g)
        elif path == g:
            hit.append(g)
        elif "*" in g and pathlib.PurePosixPath(path).match(g):
            hit.append(g)
    return hit


def main() -> int:
    if not LIC.exists():
        print("LICENCE SCOPE: FAIL\n  - LICENSING.md missing: the repo has no declared outbound licence")
        return 1
    sc = scope()
    if not sc:
        print("LICENCE SCOPE: FAIL\n  - no ```scope block in LICENSING.md")
        return 1
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    orphans: list[str] = []
    doubles: list[tuple[str, list[str]]] = []
    for p in tracked:
        if pathlib.PurePosixPath(p).name in META or p in META:
            continue
        hits = []
        for layer, globs in sc.items():
            if matches(p, globs):
                hits.append(layer)
        if not hits:
            orphans.append(p)
        elif len(set(hits)) > 1:
            doubles.append((p, sorted(set(hits))))

    problems: list[str] = []
    if orphans:
        sample = sorted({str(pathlib.PurePosixPath(o).parts[0] if len(pathlib.PurePosixPath(o).parts) > 1 else o)
                         for o in orphans})
        problems.append(f"{len(orphans)} tracked path(s) claimed by no layer, e.g. {sample[:6]} "
                        f"({len(orphans)} files) - declare them in LICENSING.md's scope block")
    if doubles:
        problems.append(f"{len(doubles)} path(s) claimed by more than one layer, e.g. "
                        + ", ".join(f"{p} in {h}" for p, h in doubles[:3]))

    core = ROOT / "library" / "dataset" / "core_facts.json"
    if not core.exists():
        problems.append("library/dataset/core_facts.json missing - run: python3 library/tools/build_core_facts.py")
    else:
        d = json.loads(core.read_text())
        if d.get("licence") != "CC0-1.0":
            problems.append(f"core_facts.json declares {d.get('licence')!r}, expected CC0-1.0")
        cc0_glob = sc.get("L2-cc0") or []
        if "library/dataset/core_facts.json" not in cc0_glob:
            problems.append("LICENSING.md: L2-cc0 must claim library/dataset/core_facts.json and nothing else")
        if len(cc0_glob) != 1:
            problems.append(f"L2-cc0 must be exactly one file, lists {len(cc0_glob)}")
        blob = json.dumps(d, sort_keys=True)
        for banned in ("f.50", "house VIII", "ruling_fr", "quote"):
            if banned in blob:
                problems.append(f"core_facts.json contains {banned!r}: the CC0 layer may hold definitions and "
                                "arithmetic only - a translated ruling is the curated layer")

    for l, g in sc.items():
        if l.endswith("-code"):
            bad = [x for x in g if x.startswith(("kb/", "library/dataset/")) and x != "library/dataset/openapi.yaml"]
            if bad:
                problems.append(f"{l} may not claim data paths {bad}: code licence must not swallow the dataset")

    print(f"licence scope: {len(sc)} layers, {len(tracked)} tracked files")
    for l, g in sorted(sc.items()):
        n = sum(1 for p in tracked if p not in META and matches(p, g))
        print(f"    {l:12s} {len(g):>2} glob(s) -> {n:>4} files")
    if problems:
        print("LICENCE SCOPE: FAIL")
        for pr in problems:
            print("  -", pr)
        return 1
    print("LICENCE SCOPE: PASS  (every tracked path is licensed by exactly one layer; CC0 is one file of arithmetic)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
