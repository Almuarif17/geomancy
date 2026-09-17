#!/usr/bin/env python3
"""Extraction-integrity gate for the Calatarama universal grid.

A figure absent from one house is a source gap. A figure absent from EVERY house is almost always a
bug in the extractor - that is how `Carcer` disappeared from all ten tabulated tables in 0.2.0 while
the appendix named it eleven times. This script cannot tell a lacuna from a bug by itself, so it
checks the things that are knowable: labels left unmatched, houses missing entirely, and a figure whose
rulings vanish wholesale. Run it from the repo root.
"""
from __future__ import annotations
import json, pathlib, sys, collections

ROOT = pathlib.Path(__file__).resolve().parents[2]
GRID = ROOT / "kb" / "calatarama_grid.json"
FIGS = ROOT / "kb" / "figures.yaml"
HOUSES = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def figures() -> list[str]:
    import yaml
    d = yaml.safe_load(FIGS.read_text())
    f = d["figures"]
    return list(f) if isinstance(f, dict) else [x["name"] for x in f]


def main() -> int:
    g = json.loads(GRID.read_text())
    grid, meta = g["grid"], g.get("_meta", {})
    figs = figures()
    problems: list[str] = []
    cov = meta.get("coverage", {})
    un = {k: v for k, v in (cov.get("unmatched_labels") or meta.get("unmatched_labels") or {}).items()
          if len(k) >= 4 and k[:1].isupper()}
    if un:
        problems.append(f"unresolved bracketed labels in the appendix: {un}")
    cells = sum(len(v["entries"]) for v in grid.values())
    if cells < 180:
        problems.append(f"only {cells} cells present; 184 expected - re-run scripts/extract_calatarama_grid.py")
    for h in HOUSES:
        if h not in grid and h != "I":
            problems.append(f"house {h} has no table at all: check the header pattern (VIII and X are headed irregularly)")
    per = collections.Counter()
    for h, v in grid.items():
        for f in v["entries"]:
            per[f] += 1
    for f in figs:
        if per[f] == 0:
            problems.append(f"figure {f} appears in NO house - the extractor is dropping it, not the source")
    absent_everywhere = [h for h, v in grid.items() if len(v["entries"]) == 0]
    if absent_everywhere:
        problems.append(f"houses with zero rows parsed: {absent_everywhere}")
    long_cells = [(h, f, len(t)) for h, v in grid.items() for f, t in v["entries"].items() if len(t) > 400]
    for h, f, n in long_cells:
        problems.append(f"cell {h}/{f} is {n} chars - slice probably ran past the table into commentary")
    short = {h: sorted(set(figs) - set(v["entries"])) for h, v in grid.items() if set(figs) - set(v["entries"])}
    notes = set()
    for d in meta.get("editorial_notes", []):
        for f in [x.strip() for x in d["figure"].split(",")]:      # one note may cover several figures
            notes.add(d["house"] + "/" + f)
    doc = {"cells": cells, "houses": len([h for h in grid if grid[h]["entries"]]), "figures": len(figs),
           "short_by_house": short, "documented_in_editorial_notes": sorted(notes)}
    print(json.dumps(doc, indent=1)[:1400])
    if problems:
        print("\nCALATARAMA GRID GATE: FAIL")
        for p in problems:
            print("  -", p)
        return 1
    documented = {f"{h}/{x}" for h, xs in short.items() for x in xs}
    if not documented <= set(notes):
        print("\nCALATARAMA GRID GATE: FAIL")
        print("  - short houses not explained in _meta.editorial_notes:", sorted(documented - set(notes)))
        return 1
    n_houses = doc["houses"]
    n_doc = len(documented)
    msg = ("CALATARAMA GRID GATE: PASS (" + str(cells) + " cells, " + str(n_houses)
           + " houses, " + str(n_doc) + " absences all explained in editorial_notes)")
    print("\n" + msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
