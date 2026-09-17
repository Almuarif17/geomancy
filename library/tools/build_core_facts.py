#!/usr/bin/env python3
"""Emit `library/dataset/core_facts.json` - the CC0 layer, and the only layer that can honestly be CC0.

Why this file exists separately: the licence split (see LICENSING.md) is only meaningful if the
"free for anyone, forever" layer is a *specific set of bytes* that we can prove we are entitled to give
away. What we are entitled to give away is what we computed ourselves plus what is definitionally true:

  * the sixteen figures as bit patterns, with their point counts and names;
  * the house numbering and the quesited-house routing we derived from the manual's own table;
  * the consequences of the arithmetic over all 65,536 casts: which judges are attainable, the parity law,
    the empirical judge population, the per-house figure priors, the surprisal table.

What is NOT here: any translated ruling, any paraphrase, any adjudication note. Those come from named
authors through a specific edition and are the curated layer (CC BY-NC + commercial licence). Keeping the
two in different files is what makes the distinction enforceable instead of a paragraph of intent.

Deterministic by construction: sorted keys, no timestamps, no paths, and the statistics are read from
`kb/priors.json` / `kb/calibration.json` (which `engine/evaluate.py` re-verifies exhaustively), so a rebuild
is byte-identical and the CI freshness guard stays quiet.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
KB = ROOT / "kb"
OUT = ROOT / "library" / "dataset" / "core_facts.json"


def main() -> int:
    import yaml
    figures_raw = yaml.safe_load((KB / "figures.yaml").read_text())["figures"]
    houses_raw = yaml.safe_load((KB / "houses.yaml").read_text())
    priors = json.loads((KB / "priors.json").read_text())
    calibration = json.loads((KB / "calibration.json").read_text())

    figures = {}
    for name, d in figures_raw.items():
        figures[name] = {"pattern": list(d.get("pattern") or []), "points": d.get("points"),
                         "element": d.get("element"), "quality": d.get("quality"), "motion": d.get("motion")}

    pj = priors.get("possible_judges")
    # priors.json stores either a list of names or a mapping keyed by judge; accept both, but never fall
    # back to calibration["attainable_figures_per_house"], whose keys are HOUSES - reading it as the Judge
    # set printed I..XVI and looked exactly like a plausible answer.
    attainable = sorted(pj) if isinstance(pj, list) else sorted((pj or {}).keys())
    if attainable and not all(a in figures_raw for a in attainable):
        sys.exit(f"possible_judges are not figure names: {attainable[:6]}")
    per_house = {k: v for k, v in sorted((calibration.get("attainable_figures_per_house") or {}).items(),
                                         key=lambda x: str(x[0]))}
    judge_pop = {k: {"n": v.get("n"), "pct": v.get("pct")} for k, v in (calibration.get("judge_population") or {}).items()}

    doc = {
        "schema": "geomancy.core_facts/1.0",
        "licence": "CC0-1.0",
        "licence_note": ("To the extent possible under law, the maintainers of geomancy-library waive all "
                         "copyright and related rights to this file. It contains only definitions and "
                         "arithmetic derived from them. Attribution is requested, not required."),
        "generated_by": "library/tools/build_core_facts.py",
        "provenance_of_numbers": {
            "figures.pattern": "definition of the sixteen figures as four rows of one or two dots",
            "statistics": "kb/priors.json and kb/calibration.json, produced by engine/build_priors.py",
            "verification": "library/dataset/evaluation.json (65,536/65,536 against an independent oracle)",
        },
        "cast_space": {"mothers": 4, "figures": 16, "total_casts": priors.get("total_casts"),
                       "bits_per_cast": 16, "parity_law": ("the Judge is always even-pointed; the eight odd-pointed "
                                                           "figures can never be a Judge"),
                       "attainable_judges": attainable,
                       "attainable_judges_note": ("derived: adding two mothers/nieces pairs mod parity yields only "
                                                  "even-pointed figures in the Judge seat, verified over every cast"),
                       "attainable_figures_per_house": per_house,
                       "judge_population": judge_pop,
                       "surprisal_bits_by_house": calibration.get("surprisal_bits_by_house")},
        "figures": figures,
        "houses": {str(k): {"name": (v or {}).get("name"), "significator": (v or {}).get("significator")}
                   for k, v in sorted(houses_raw.get("houses", {}).items(), key=lambda x: str(x[0]))},
        "question_to_house": {k: v for k, v in sorted((houses_raw.get("question_to_house") or {}).items())},
    }
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"core_facts: {len(figures)} figures, {len(doc['houses'])} houses, "
          f"{len(doc['question_to_house'])} routings, {OUT.stat().st_size:,} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
