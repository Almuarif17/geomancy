#!/usr/bin/env python3
"""Coverage scoreboard: what the library actually contains, as a number that cannot be flattered.

Run `python3 library/tools/score_coverage.py --write` to regenerate `kb/coverage.json` (deterministic, no
timestamps, so a fresh clone reproduces it byte-for-byte); `--check` is the gate CI and `validate.py` run;
`--record` appends a row to `notes/coverage_history.jsonl` - opt-in only, because a self-updating file in
`kb/` would make every build dirty.

Every figure is a count over shipped files, never a claim copied from prose, and every ratio is printed with
its numerator and denominator on purpose: a score without denominators is how a research project spends a
year feeling productive. The score is deliberately *not* a quality measure - it answers one question only:
how much of the space we said we would fill is filled. Low scores are the point of publishing this, because
they are the roadmap, and the roadmap is derived by the same sort that orders the numbers rather than written
by hand in a README.
"""
from __future__ import annotations

import argparse
import json
import re
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
KB = ROOT / "kb"
LIB = ROOT / "library"

# Targets are the numbers we committed to in docs/IP_STRATEGY.md and the outstanding backlog. They live here,
# in the file the gate reads, so "we said 60 outcomes" is checkable rather than nostalgic.
TARGETS = {
    "works_contributing": 16,      # every registry row disposited full/summarize (16 of 23 registered)
    "cross_work_keys": 300,        # keys with >=2 works: disagreement becomes visible, not anecdotal
    "quotable_rows": 1400,
    "grid_cells": 192,             # Calatarama thesis Table 8, complete
    "lataille_cells": 48,          # 16 figures x the 3 houses whose headings survive in the abridged print
    "figures_with_attributes": 16, # figures carrying the Calatarama `meaning` line (all 16 have a planet)
    "outcomes": 60,                # app-facing question types (12 houses x 5 + court)
    "techniques_implemented": 23,
    "rule_cases_proof": 29,        # every pin should become a proof
    "figures_attributed": 16,      # all 16, not 3
}

WEIGHTS = {
    "works_contributing": 0.18,
    "cross_work_keys": 0.18,
    "quotable_rows": 0.08,
    "grid_cells": 0.10,
    "lataille_cells": 0.05,
    "outcomes": 0.14,
    "techniques_implemented": 0.09,
    "rule_cases_proof": 0.10,
    "figures_with_attributes": 0.08,
}

# Remedies are the *next command*, not an aspiration. A move with no command attached is a wish.
REMEDIES = {
    # the numerator counts *extractor* work labels, which are not always registry ids; the denominator is
    # the registry's own fetchable set, so 7/16 is "7 labels contributed", not "9 works are ignored"
    "works_contributing": ("Fetch and extract the 9 registered works disposited full/summarize that still contribute no voice row - la Taille, Heydon, Agrippa's Opus, the three Arabic/Persian raml treatises, binsbergen's edition and the Barcelona MS.",
                           "python3 library/tools/sync_corpus.py --only <work-id> && python3 scripts/build_voices.py"),
    "cross_work_keys": ("Adopt one shared claim key across works so Agrippa, Cattan and Hartmann land on the same figure-in-house keys; disagreement stops being anecdotal around 300 shared keys.",
                         "python3 scripts/build_voices.py"),
    "quotable_rows": ("The cite_only rows are licence-gated, not lost: fetch the witness, then quote from the local copy once its bucket allows text.",
                      "python3 library/tools/sync_corpus.py --check && python3 scripts/build_voices.py"),
    "grid_cells": ("8 Calatarama cells are unread; Barcelona MS 84.7.4 f.50 is the fallback witness for Acquisitio in VIII.",
                   "python3 library/tools/check_calatarama_grid.py"),
    "lataille_cells": ("8 of 48 readable cells transcribed; the ceiling is the witness, not the effort - this abridged octavo lost most section headings to long-s OCR, so a fuller edition is needed.",
                       "python3 library/tools/sync_corpus.py --only lataille_geomancie"),
    "outcomes": ("Grow the question inventory from 22 to 60 routings using the Catalan and Castilian lists already in kb/.",
                 "python3 scripts/build_question_inventory.py"),
    "techniques_implemented": ("Two techniques are NAMED_ONLY: write the test, then pin it against the oracle.",
                               "python3 library/tools/run_rule_tests.py --list"),
    "rule_cases_proof": ("Convert the 9 pin cases to proof by adding a second independent witness per rule.",
                         "python3 library/tools/run_rule_tests.py --probe"),
    "figures_with_attributes": ("Seven figures have no `meaning` line in the Calatarama block (14 of 16 have cal_details at all); the 2 naming conflicts need a documented decision, not a merge.",
                                 "python3 library/tools/check_docs_consistency.py --report"),
}


def check_commands(components: dict) -> list[str]:
    """A scoreboard that prints a command which does not exist teaches people to ignore the scoreboard.

    Every ``next_command`` must be ``python3 <repo script> [--flag ...]`` with the script tracked on disk and
    each flag appearing literally in it. Placeholders in angle brackets are exempt by definition.
    """
    bad = []
    for name, c in components.items():
        cmd = c.get("next_command", "")
        for part in cmd.split("&&"):
            toks = [t for t in part.strip().split() if t]
            if not toks or toks[0] != "python3" or len(toks) < 2:
                bad.append(f"{name}: {cmd!r} is not a plain python3 <script> invocation")
                continue
            script = pathlib.Path(toks[1])
            if not (ROOT / script).exists():
                bad.append(f"{name}: {script} does not exist")
                continue
            text = (ROOT / script).read_text()
            for fl in [t for t in toks[2:] if t.startswith("--")]:
                if f'"{fl}"' not in text and f"'{fl}'" not in text:
                    bad.append(f"{name}: {script} never declares {fl}")
    return bad


def count(path: pathlib.Path) -> int:
    return sum(1 for l in path.read_text().splitlines() if l.strip()) if path.exists() else 0


def compute() -> dict:
    voices = [json.loads(l) for l in (KB / "voices.jsonl").read_text().splitlines() if l.strip()]
    by_key: dict[str, set] = {}
    for v in voices:
        by_key.setdefault(f"{v['family']}:{v['key']}", set()).add(v["work"])
    reg = [json.loads(l) for l in (ROOT / "registry/works.jsonl").read_text().splitlines() if l.strip()]
    fetchable = [r for r in reg if r.get("disposition") in {"full", "summarize"}]

    # voices.jsonl labels rows by the extractor's short name (`cattan1608`, `lataille`), the registry keys by
    # id (`cattan_1608`, `lataille_geomancie`). Joining them on raw equality reported 0 of 16 works as
    # contributing, which is a bug that reads like a devastating finding - so normalise, then match by
    # containment, and keep the mapping in the output so the claim is checkable.
    def norm(x: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (x or "").lower())

    labels = {norm(w) for w in {v["work"] for v in voices}}
    contrib_ids, missing_ids = set(), set()
    for r in fetchable:
        rid = norm(r["id"])
        # containment both ways only; a prefix heuristic here once credited every "cattan15xx"/"cattan16xx"
        # work to whichever of the two was fetched first, which is the kind of generosity a score must not have
        hit = any(l and (l in rid or rid in l) for l in labels)
        (contrib_ids if hit else missing_ids).add(r["id"])
    works_num = len(contrib_ids)

    cal = json.loads((KB / "calatarama_grid.json").read_text())["grid"]
    cal_cells = sum(len(h.get("entries") or {}) for h in cal.values())
    lat_raw = json.loads((KB / "lataille_grid.json").read_text())["grid"]
    # the file is a list of {figure, house, ruling_fr} rows, not a house->entries map like calatarama
    lat_cells = sum(1 for r in (lat_raw if isinstance(lat_raw, list) else lat_raw.values())
                    if (r.get("ruling_fr") or r.get("ruling") or "").strip())

    tech = yaml.safe_load((KB / "techniques.yaml").read_text())["techniques"]
    implemented = sum(1 for v in tech.values() if str(v.get("status", "")) != "NAMED_ONLY")
    cases = yaml.safe_load((KB / "rule_tests.yaml").read_text())["cases"]
    proof = sum(1 for c in cases if c.get("strength") == "proof")
    figs = yaml.safe_load((KB / "figures.yaml").read_text())["figures"]
    attributed = sum(1 for f in figs.values() if (f.get("cal_details") or {}).get("meaning"))
    out = LIB / "dataset/index/by_outcome.jsonl"
    n_out = count(out)
    n_by_voice = count(LIB / "dataset/index/by_voice.jsonl")
    dis = 0
    if n_by_voice:
        dis = sum(1 for l in (out.parent / "by_voice.jsonl").read_text().splitlines() if l.strip()
                  and json.loads(l).get("disagreement"))

    nums = {
        "works_contributing": works_num,
        "cross_work_keys": sum(1 for k, w in by_key.items() if len(w) > 1),
        "quotable_rows": sum(1 for v in voices if (v.get("quote") or "").strip()),
        "grid_cells": cal_cells,
        "lataille_cells": lat_cells,
        "outcomes": n_out,
        "techniques_implemented": implemented,
        "rule_cases_proof": proof,
        "figures_with_attributes": attributed,
    }
    components = {}
    for name, num in sorted(nums.items()):
        # for works_contributing the remedy is generated from the computed set below, never typed: a
        # hand-written list of work names goes stale silently the day the registry changes
        den = TARGETS[name]
        ratio = round(num / den, 4) if den else 0.0
        rem, cmd = REMEDIES[name]
        extra = {}
        if name == "works_contributing":
            extra = {"contributing_works": sorted(contrib_ids), "missing_works": sorted(missing_ids),
                     "note": ("count = registered works disposited full/summarize that have at least one row "
                              "in kb/voices.jsonl after joining the extractors' short labels to registry ids")}
            c_rem = (f"Fetch and extract the {len(missing_ids)} registered work(s) disposited full/summarize "
                     f"that still contribute no voice row: {', '.join(sorted(missing_ids))}.")
            rem = c_rem
        components[name] = {"count": num, "target": den, "ratio": ratio, **extra,
                            "weight": WEIGHTS[name], "achieved": min(1.0, ratio),
                            "remedy": rem, "next_command": cmd}
    score = round(sum(c["weight"] * c["achieved"] for c in components.values()) * 100, 1)
    return {
        "schema": "geomancy-coverage/1",
        "score_of_100": score,
        "weights_sum": round(sum(WEIGHTS.values()), 6),
        "components": components,
        # worst first, computed - the list is the roadmap, so it must not be hand-ordered
        "ranked_moves": [n for n, _ in sorted(((k, c["ratio"]) for k, c in components.items()),
                                               key=lambda x: (x[1], x[0]))],
        "reported_only": {
            "voices_rows": len(voices),
            "claim_keys": len(by_key),
            "measurable_cross_source_disagreements": dis,
            "works_registered": len(reg),
            "works_fetchable_by_bucket": len(fetchable),
            "rule_cases_total": len(cases),
            "techniques_named": len(tech),
            "figures": len(figs),
        },
        "reading_guide": ("ratio = current/target, uncapped, so a component over target is visible; score = "
                          "sum(weight * min(1, ratio)) * 100. The score is completeness against our own "
                          "targets, not accuracy or trustworthiness. Disagreement counts are reported, never "
                          "scored: a library can only score well by suppressing them, which is the failure "
                          "mode this file exists to prevent."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="write kb/coverage.json")
    ap.add_argument("--check", action="store_true", help="fail if kb/coverage.json differs from a rebuild")
    ap.add_argument("--record", action="store_true", help="append this run to notes/coverage_history.jsonl")
    ap.add_argument("--top", type=int, default=5, help="how many ranked moves to print")
    args = ap.parse_args()

    data = compute()
    blob = json.dumps(data, indent=2, sort_keys=True) + "\n"
    dest = KB / "coverage.json"
    bad_cmds = check_commands(data["components"])
    if bad_cmds:
        print("COVERAGE: FAIL - scoreboard commands are not real")
        for b in bad_cmds:
            print("  -", b)
        return 1
    if args.write:
        dest.write_text(blob)
        print(f"kb/coverage.json written ({len(blob):,} B), score {data['score_of_100']}/100")
        return 0
    if args.check:
        if not dest.exists():
            print("COVERAGE: FAIL - kb/coverage.json missing; run: python3 library/tools/score_coverage.py --write")
            return 1
        if dest.read_text() != blob:
            print("COVERAGE: FAIL - kb/coverage.json is stale against the shipped files")
            print("  run: python3 library/tools/score_coverage.py --write")
            return 1

    print(f"coverage score: {data['score_of_100']}/100  (completeness vs our own targets, not accuracy)")
    for name in sorted(data["components"]):
        c = data["components"][name]
        bar = "#" * int(round(24 * c["achieved"]))
        print(f"  {name:24s} {c['count']:>5}/{c['target']:<5} {int(c['ratio']*100):>4}%  w{c['weight']:.2f} {bar}")
    r = data["reported_only"]
    print("  reported (unscored):", ", ".join(f"{k}={v}" for k, v in sorted(r.items())))
    print(f"\nnext {min(args.top, len(data['ranked_moves']))} moves, worst component first:")
    for i, name in enumerate(data["ranked_moves"][:args.top], 1):
        c = data["components"][name]
        print(f"  {i}. {name} ({int(c['ratio']*100)}% of target) - {c['remedy']}")
        print(f"     $ {c['next_command']}")
    if args.record:
        hist = ROOT / "notes/coverage_history.jsonl"
        row = {"score": data["score_of_100"],
               "counts": {k: v["count"] for k, v in data["components"].items()}}
        lines = [l for l in (hist.read_text().splitlines() if hist.exists() else []) if l.strip()]
        if lines and json.loads(lines[-1])["counts"] == row["counts"]:
            print(f"\n{hist.name}: unchanged (identical counts), nothing appended")
        else:
            lines.append(json.dumps(row, sort_keys=True))
            hist.write_text("\n".join(lines) + "\n")
            print(f"\nappended to {hist.relative_to(ROOT)} ({len(lines)} rows)")
    print("COVERAGE: PASS" if (not args.check or dest.exists() and dest.read_text() == blob) else "COVERAGE: FAIL")
    return 0 if (not args.check or dest.read_text() == blob) else 1


if __name__ == "__main__":
    sys.exit(main())
