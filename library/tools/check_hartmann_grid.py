#!/usr/bin/env python3
"""Measure how much of Hartmann's 2,048-answer grid we have actually transcribed.

The grid is 8 attainable Judges x 16 cofigures x 16 questions (verified against the extracted rows,
2026-09-17 - the shape the data supports, not the 16x16x8 guess). This makes "we have 859 answers"
into something checkable: which cells, which blocks, what to OCR next.
"""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine"))
import deep_read as dr
cb = json.loads((ROOT / "kb/hartmann_casebook.json").read_text())
ans = cb["answers"]
attain = sorted(json.loads((ROOT / "kb/priors.json").read_text())["possible_judges"])
figs = list(dr.FIG.keys())
have = {(r["judge"], r["cofigure"], int(r["q"])) for r in ans}
total = len(attain) * len(figs) * 16
rows = [r for r in ans if r["judge"] not in attain]
print(f"extracted cells {len(have)} / {total}  ({100*len(have)/total:.1f}%)")
for j in attain:
    got = sum(1 for k in have if k[0] == j)
    print(f"   judge {j:16s} {got:3d}/256 " + ("<- whole block missing" if got == 0 else ""))
print(f"cells whose judge is NOT attainable (would break the parity theorem): {len(rows)}")
miss = [(j, c, q) for j in attain for c in figs for q in range(1, 17) if (j, c, q) not in have]
nxt = {}
for j, c, q in miss:
    nxt[(j, c)] = nxt.get((j, c), 0) + 1
top = sorted(nxt.items(), key=lambda x: -x[1])[:5]
print("largest holes (judge, cofigure) -> missing question cells:",
      ", ".join(f"{a}/{b}:{n}" for (a, b), n in top))
print("\nfill them with: scripts/ocr_ingest.py + scripts/extract_hartmann.py (see kb/hartmann_casebook.json _meta.next_extraction)")
sys.exit(1 if rows else 0)
