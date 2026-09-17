#!/usr/bin/env python3
"""Prose must not outlive the build it describes.

Two failure modes this exists for, both of which actually happened here:

1. **A generated file describing another generated file, one build stale.** `library/dataset/
   evaluation.json` reported 1,098 passages while `manifest.json` reported 1,140, because evaluation.json
   is written by a Makefile target that CI's freshness guard did not watch. Checked here, unconditionally.
2. **A README sentence that stayed true for three releases and then quietly stopped being true.** Fixed by
   making the number a build output: write `<!--num:passages-->1,140 passages` in the prose, and
   `--fix` keeps the digits correct while the HTML comment stays invisible when the markdown renders.

Why not just grep prose for "N passages" and police it? Because it produced eight findings on first run
and only two were real: "42 rules OCR'd from the fasciculus" counts a different unit, "29 across 22 rules"
counts cases, and a roadmap line about reaching 186/192 is a goal, not a claim. A gate that must be told
which of its findings are noise is not a gate. Marked numbers are checked; unmarked prose is a human's
business, and `--report` lists near-misses so a reviewer can decide to mark them.

CHANGELOG.md, PLAN.md and docs/RESEARCH_LEDGER.md are exempt from every check: they are dated records, and
rewriting history to match a later build destroys it.
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DS, KB = ROOT / "library" / "dataset", ROOT / "kb"
EXEMPT = {"CHANGELOG.md", "PLAN.md"}


def truth() -> dict:
    man = json.loads((DS / "manifest.json").read_text())
    grid = json.loads((KB / "calatarama_grid.json").read_text())
    figures = len([k for k in (yaml_load(KB / "figures.yaml").get("figures") or {}) if k])
    houses = len([k for k in (yaml_load(KB / "houses.yaml").get("houses") or {}) if k])
    outcomes = len([l for l in (DS / "index" / "by_outcome.jsonl").read_text().splitlines() if l.strip()])
    reg = [l for l in (ROOT / "registry" / "works.jsonl").read_text().splitlines() if l.strip()]
    cases = sum(1 for l in (KB / "rule_tests.yaml").read_text().splitlines() if l.strip().startswith("- rule:"))
    return {"passages": man["counts"]["passages"], "rules": man["counts"]["rules"],
            "figures": figures, "houses": houses, "grid_cells": sum(len(v["entries"]) for v in grid["grid"].values()),
            "grid_possible": len(grid["grid"]) * figures, "outcomes": outcomes,
            "works_registered": len(reg), "works_shipped": man["counts"]["works"], "rule_cases": cases,
            "voices": len([l for l in (ROOT / "kb" / "voices.jsonl").read_text().splitlines() if l.strip()]) if (ROOT / "kb" / "voices.jsonl").exists() else 0}


def yaml_load(p: pathlib.Path):
    import yaml
    return yaml.safe_load(p.read_text())


def targets():
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.suffix not in (".md", ".py") or ".git" in p.parts:
            continue
        if p.name in EXEMPT or p.parent.name in {"notes", "corpus"} or p == pathlib.Path(__file__):
            continue
        yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="rewrite every marked number to the build's value")
    ap.add_argument("--report", action="store_true", help="also list unmarked numeric claims that disagree")
    a = ap.parse_args()
    t = truth()
    pat = re.compile(r"<!--num:(\w+)-->\*{0,2}([\d,]+)\*{0,2}")
    changed, checked, bad = 0, 0, []
    for p in targets():
        txt = p.read_text()
        if "<!--num:" not in txt:
            continue
        def sub(m):
            nonlocal checked, changed
            key, val = m.group(1), m.group(2)
            checked += 1
            if key not in t:
                bad.append(f"{p.relative_to(ROOT)}: unknown key {key!r} (have: {', '.join(sorted(t))})")
                return m.group(0)
            want = f"{t[key]:,}" if "," in val else str(t[key])
            if val != want:
                changed += 1
                if not a.fix:
                    bad.append(f"{p.relative_to(ROOT)}: marked {key} says {val}, build says {want}")
            return m.group(0).replace(m.group(2), want)
        new = pat.sub(sub, txt)
        if a.fix and new != txt:
            p.write_text(new)
    # artefact-vs-artefact, always
    man = json.loads((DS / "manifest.json").read_text())
    evf = DS / "evaluation.json"
    if evf.exists():
        ev = json.loads(evf.read_text())
        for k in ("passages", "rules"):
            if ev.get(k) != man["counts"][k]:
                bad.append(f"library/dataset/evaluation.json {k}={ev.get(k)} but manifest.json says {man['counts'][k]}"
                           " - run: python3 engine/evaluate.py --json library/dataset/evaluation.json")
        if ev.get("passages_with_locator") not in (None, ev.get("passages")):
            bad.append(f"evaluation.json: {ev.get('passages_with_locator')}/{ev.get('passages')} passages carry a locator;"
                       " every shipped passage must, or the citation guarantee is false")
    if a.report:
        loose = re.compile(r"(?<![\w.])((?:1|2)?\d{3})\s+passages")
        for p in targets():
            for ln, line in enumerate(p.read_text().splitlines(), 1):
                if "<!--num:" in line:
                    continue
                for m in loose.finditer(line):
                    if int(m.group(1)) != t["passages"]:
                        print(f"  note  {p.relative_to(ROOT)}:{ln} states {m.group(1)} passages unmarked")
    print(f"docs consistency: {len(t)} units tracked, {checked} marked numbers, {changed} rewritten"
          + (" (--fix)" if a.fix else ""))
    if bad:
        print("DOCS CONSISTENCY: FAIL")
        for b in bad[:20]:
            print("  -", b)
        print(f"  fix with: python3 library/tools/check_docs_consistency.py --fix")
        return 1
    print("DOCS CONSISTENCY: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
