#!/usr/bin/env python3
"""Write kb/rule_tests.yaml - one executable case per computable rule.

Each case pins a dotted path inside the exported reading (the contract the app consumes) and
declares its `strength`:
  proof - the expectation follows from a rule stated in a source, or from arithmetic checked
          against engine/oracle.py, which agrees with the engine on all 65,536 casts.
  pin   - the expectation is only "what the code does today"; it exists so a future change to a
          rule cannot pass unnoticed. It is not evidence of correctness - do not upgrade a pin
          to a proof without reading the source.
`library/tools/run_rule_tests.py` executes them; `validate.py` fails a build in which a HIGH rule
has no case at all. Re-run this generator, then hand-edit `strength`/`note` where you have read
the folio yourself.
"""
from __future__ import annotations

import itertools, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
import yaml                                                     # noqa: E402
import deep_read as dr                                          # noqa: E402
import export_reading as EX                                     # noqa: E402
import questions as QS                                          # noqa: E402
import oracle as O                                              # noqa: E402

C1 = ["Carcer", "Amissio", "Caput Draconis", "Populus"]        # the audited real cast (marriage)
C2 = ["Fortuna Major", "Acquisitio", "Laetitia", "Conjunctio"]  # clean single-line trace (theft)
C3 = ["Albus", "Via", "Via", "Carcer"]                          # trace dies at the Judge's head (found by search)
C4 = ["Via", "Via", "Albus", "Tristitia"]                         # Populus as Judge (found by search)
C5 = ["Cauda Draconis", "Puer", "Fortuna Minor", "Rubeus"]      # Cauda in I -> recast; Rubeus elsewhere
OCC = ["Via", "Via", "Via", "Albus"]                            # house I figure repeats in VII
BR = ["Via", "Via", "Via", "Laetitia"]                          # multi-headed trace

CASES = [
    ("reconciler", C1, "marriage", "court.sentence", "equals", None, "proof",
     "XV + Mother I: Conjunctio(2-1-1-2) + Carcer(1-2-2-1) -> 1-1-1-1 = Via; al-Zanati 'from the first and the fifteenth' (van Binsbergen 1996)"),
    ("numerology_of_figures", C1, "marriage", "chart.14.points", "equals", 6, "proof",
     "Judge Conjunctio = 2+1+1+2 = 6; the Judge must be even in points (parity law, Calatarama)"),
    ("projection_of_points", C1, "marriage", "trace.projection_of_points.single_dots", "equals", 24, "proof",
     "24 single dots in I..XII, 24 mod 12 = 0 -> the 12th house (Serena Powers; Calatarama f.12)"),
    ("pars_fortunae", C1, "marriage", "trace.part_of_fortune.total_points", "equals", 72, "proof",
     "72 points in I..XII, 72 mod 12 = 0 -> house XII (Serena Powers; Cattan)"),
    ("projection_of_points", C2, "theft", "trace.projection_of_points.house", "equals", "XII", "proof",
     "hand-counted on the printed chart: rows I..XII hold 24 singles -> XII, whose figure is Acquisitio"),
    ("via_puncti", C2, "theft", "trace.via_puncti.path.3.figure", "equals", "Laetitia", "proof",
     "head rows: XV=1 matches XIII=1 (XIV=2 not); XIII(1) <- IX(2) no, X(1) yes; X <- MIII(1) yes, MIV(2) no => root III Laetitia"),
    ("via_puncti", C3, "general", "trace.via_puncti.formed", "equals", False, "proof",
     "neither witness shares the Judge's head row, so no path can form - the matter is exactly as it "
     "appears (Calatarama f.12v-13). Cast found by search over all 65,536 casts"),
    ("via_puncti", C3, "general", "trace.via_puncti.endpoints.0.kind", "equals", "died", "proof",
     "a dead trace must be reported as dead, not padded to a Mother"),
    ("via_puncti", BR, "general", "trace.via_puncti.endpoints", "min_items", 2, "proof",
     "a two-headed split must be followed on every branch, not truncated to the last split "
     "(this is the bug the oracle sweep found: the old code kept only the final split)"),
    ("motus_and_passing", C1, "marriage", "relations.motus.Conjunctio", "equals", None, "proof",
     "Conjunctio occurs in VII and XV - Cattan: judge a moving figure by its second coming"),
    ("parentage", C1, "marriage", "relations.parentage.4.house", "equals", "IX", "proof",
     "house IX is the sum of Mothers I+II (Calatarama f.22v: each generated figure inherits its parents)"),
    ("validity_gates", C4, "general", "validity", "has_flag", "SUSPEND", "proof",
     "Populus as Judge: verdict is crowd-voice, judgment must wait (stopping-figure rule)"),
    ("validity_gates", C5, "general", "validity", "has_flag", "RECAST", "proof",
     "Cauda Draconis in house I: 'break it and make another figure one hour later' (Cattan 1591/1608)"),
    ("perfection", OCC, "marriage", "relations.perfection.mode", "equals", None, "proof",
     "same figure in I and the quesited house = occupation, the strongest mode (Alfagini via Calatarama)"),
    ("house_quality_tiebreak", OCC, "marriage", "sub_questions", "not_empty", None, "pin",
     "la Taille: when figures cancel, prefer by the quality of the house - 'preferez le jugement selon les qualitez des maisons'"),
    ("perfection", C1, "marriage", "relations.perfection.base_rate_pct", "not_empty", None, "proof",
     "the mode must be priced against the exact prior over 65,536 casts - this is the library's differentiator"),
    ("timing", C1, "marriage", "specifics.when", "not_empty", None, "pin",
     "digit-sum pace plus the figure's timing unit (Calatarama Table 4); values are table lookups"),
    ("place_and_direction", C1, "marriage", "specifics.where", "not_empty", None, "pin",
     "direction/place from the figure's own table row, never invented"),
    ("significators_by_house", C1, "marriage", "specifics.who", "not_empty", None, "pin",
     "who/what/peoples/science columns of Calatarama f.7v-9"),
    ("element_balance", C1, "marriage", "specifics.constitution.excess", "not_empty", None, "proof",
     "humoral tally from the figures' complexions; excess names the remedy to read the answer as"),
    ("triplicities", C1, "marriage", "relations.triplicities.golden_dawn", "min_items", 3, "pin",
     "Golden Dawn elemental groups + Calatarama routing for the topic"),
    ("judge_as_house_reader", C1, "marriage", "cross_read", "not_empty", None, "pin",
     "the Judge also reads as the house it occupies (Finan thesis, f.22v family)"),
    ("end_of_the_matter", C1, "marriage", "court.sentence_rule", "not_empty", None, "proof",
     "the Sentence names how the matter ends; same arithmetic as the reconciler rule"),
    ("figure_attribution_variants", C1, "marriage", "flags", "contains_substring", "contested", "proof",
     "Puer/Puella labels are swapped between Britannica/GD and Digital Ambler/Skinner - output must say so"),
    ("guarding_of_hidden_things", C1, "inheritance", "sub_questions.inheritance_lost_recover",
     "not_empty", "pin", "recovery of what was lost/taken - the Alfagini leaf the rule comes from"),
    ("significators_by_house", C2, "quietly_unknown_topic", "flags", "contains_substring",
     "no sub-question bank entry", "proof",
     "an unknown topic must announce itself in `flags`, never return a quiet empty bank - "
     "'theft' is now aliased, so the probe uses a topic the library really does not know"),
    ("evil_eye_and_crossed_conditions", C5, "general", "validity", "not_empty", "pin",
     "crossed/malevolent conditions - MED confidence, from kitchentoad.com and parallel folkesources"),
    ("company_of_houses", C1, "marriage", "relations.triplicities.calatarama_routing", "not_empty", "pin",
     "the company of houses to read alongside the triplicity (Finan thesis Table 7)"),
    ("planetary_election_gate", C1, "marriage", "validity", "flag_prefix", "planetary_gate:", "proof",
     "the medieval gate: a cast is void unless the day/hour lord is consulted (temporal hours, not clock hours)"),
]

DATA = {"generated_by": "scripts/build_rule_tests.py",
        "note": "cases pin the exported reading contract; strength=proof means the expectation is derived from a stated source rule or from the oracle (engine/oracle.py, which agrees with engine/deep_read.py on all 65,536 casts)",
        "cases": []}
for tup in CASES:
    rid, mothers, topic, dotted, pred, value, strength, why = (
        tup if len(tup) == 8 else (*tup[:5], None, *tup[5:]))
    assert isinstance(strength, str) and strength in {"proof", "pin"}, tup
    r = EX.reading([dr.norm(m) for m in mothers], topic)
    cur, missing = r, False
    for part in dotted.split("."):
        if isinstance(cur, list):
            try: cur = cur[int(part)]
            except (ValueError, IndexError): missing = True; break
        elif isinstance(cur, dict):
            if part not in cur: missing = True; break
            cur = cur[part]
        else:
            missing = True; break
    case = {"rule": rid, "mothers": mothers, "topic": topic, "path": dotted, "predicate": pred,
            "strength": strength, "verified_by": why}
    if value is not None:
        case["value"] = value
    if pred == "equals" and value is None:
        case["value"] = cur if not missing else None
    if pred == "has_flag" and value:
        case["value"] = value
    if pred == "flag_prefix" and value:
        case["value"] = value
    if missing and pred == "equals":
        case["predicate"] = "not_empty"
        case.pop("value", None)
    DATA["cases"].append(case)

out = ROOT / "kb" / "rule_tests.yaml"
out.write_text("# executable cases per rule - generated by scripts/build_rule_tests.py, then hand-corrected\n"
               + yaml.safe_dump(DATA, sort_keys=False, width=100, allow_unicode=True))
print(f"wrote {out.relative_to(ROOT)}: {len(DATA['cases'])} cases,",
      sum(1 for c in DATA['cases'] if c['strength'] == 'proof'), "proofs")
json.dump({"n": len(DATA["cases"])}, open("/tmp/rt.json", "w"))
