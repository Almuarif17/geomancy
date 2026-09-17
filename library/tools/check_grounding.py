#!/usr/bin/env python3
"""Grounding gate: the citation machinery is only worth having if something attacks it.

Checks, in order:

1. **Licence integrity of every voice.** A row may carry quote text only if its work is registered with
   disposition `full`. cite-only works carry a locator and nothing else. This is the rule that keeps a
   public dataset shippable inside someone else's paid app.
2. **Citable-ness.** Every voice has a locator and a registered `work_id`; ids are unique, because ids are
   how a reader checks us.
3. **The assembler produces a valid reading** on three fixture casts, and `engine/ground.py validate()`
   says so.
4. **The auditor rejects the four ways a reading goes wrong** - an uncited claim, a citation to a voice
   that does not exist, a claim about a figure that is not in the cast, and asserted certainty. A validator
   that has never been shown a bad input is decoration; this one has.
5. **Schema conformance** of the shipped contract, when jsonschema is installed.

Run from the repo root, or via `python3 library/tools/validate.py`, which is what CI runs.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    problems: list[str] = []
    voices = [json.loads(l) for l in (ROOT / "kb" / "voices.jsonl").read_text().splitlines() if l.strip()]
    reg = {}
    for l in (ROOT / "registry" / "works.jsonl").read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            reg[r["id"]] = r

    ids = set()
    for i, v in enumerate(voices):
        if v["id"] in ids:
            problems.append(f"voice id not unique: {v['id']}")
        ids.add(v["id"])
        if v.get("work_id") not in reg:
            problems.append(f"{v['id']}: work_id {v.get('work_id')!r} is not registered in registry/works.jsonl")
        if not v.get("locator"):
            problems.append(f"{v['id']}: no locator - an unlocatable claim cannot be checked, so it cannot ship")
        row_work = reg.get(v.get("work_id"), {})
        if v.get("quote") and row_work.get("disposition") != "full":
            problems.append(f"{v['id']}: ships quote text but its work is disposition="
                            f"{row_work.get('disposition')!r}; strip the text and cite it")
        if v.get("cite_only") and v.get("quote"):
            problems.append(f"{v['id']}: marked cite_only yet carries a quote")
        if v.get("polarity") and not v.get("polarity_reliability"):
            problems.append(f"{v['id']}: has a polarity lean with no reliability tag (an unmeasured source "
                            "reads as 'neutral' and turns silence into false agreement)")

    idx = ROOT / "library" / "dataset" / "index" / "by_voice.jsonl"
    if not idx.exists():
        problems.append("index/by_voice.jsonl missing - run: python3 engine/retrieve.py --build")
    else:
        rows = [json.loads(l) for l in idx.read_text().splitlines() if l.strip()]
        if len(rows) != len({r["key"] for r in rows}):
            problems.append("by_voice.jsonl has duplicate keys")
        n_dis = sum(1 for r in rows if r.get("disagreement"))
        for r in rows:
            if r.get("disagreement") and len(r.get("voices", [])) < 2:
                problems.append(f"{r['key']}: disagreement claimed with one voice")

    from engine import ground
    vb = ground.VoiceBook()
    fixtures = [{"mothers": ["Via", "Populus", "Acquisitio", "Amissio"], "topic": "marriage"},
                {"mothers": ["Carcer", "Tristitia", "Amissio", "Puer"], "topic": "lost_things"},
                {"mothers": ["Fortuna Major", "Laetitia", "Albus", "Caput Draconis"], "topic": "wealth_money"}]
    from engine import deep_read as D
    n_claims = 0
    for f in fixtures:
        c = D.build(f["mothers"])
        chart = {"houses": {i + 1: D.fig(p) for i, p in enumerate(c["houses"][:12])},
                 "judge": D.fig(c["judge"]), "sentence": D.fig(c["sentence"])}
        reading = ground.assemble(chart, f["topic"], vb)
        aud = ground.validate(reading, vb)
        n_claims += len(reading["claims"])
        if not aud["ok"]:
            problems.append(f"fixture {f['topic']}: assembler produced an invalid reading: {aud['problems'][:3]}")

    # the auditor must fail on each of the four real ways this goes wrong
    bad = [
        ("uncited claim", {"claims": [{"type": "sourced_ruling", "text": "Fortune favours you", "cites": {"voice_ids": []}}]}),
        ("unknown citation", {"claims": [{"type": "sourced_ruling", "text": "Albus in I: gain",
                                          "cites": {"voice_ids": ["figure_in_house:Albus:1:not_a_source"]}}]}),
        ("figure not in cast", {"chart": {"1": "Albus"}, "claims": [{"type": "sourced_ruling",
                                     "text": "Carcer in I: detention", "cites": {"voice_ids": [voices[0]["id"]]}}]}),
        ("asserted certainty", {"claims": [{"type": "sourced_ruling", "mode": "gloss",
                                            "text": "You will recover the stolen goods", "cites": {"voice_ids": [voices[0]["id"]]}}]}),
    ]
    for label, payload in bad:
        res = ground.validate(payload, vb)
        if res["ok"]:
            problems.append(f"the auditor accepted a deliberately bad reading ({label}); it is not enforcing anything")

    sch = ROOT / "library" / "schema" / "grounded_reading.json"
    if sch.exists():
        try:
            import jsonschema
            c = D.build(fixtures[0]["mothers"])
            reading = ground.assemble({"houses": {i + 1: D.fig(p) for i, p in enumerate(c["houses"])}},
                                     "marriage", vb)
            jsonschema.validate(reading, json.loads(sch.read_text()))
        except ImportError:
            print("  (jsonschema not installed: schema conformance not exercised)")
        except Exception as e:
            problems.append(f"a real reading fails our own schema: {str(e)[:180]}")

    print(f"grounding gate: {len(voices)} voices, {n_claims} claims assembled from {len(fixtures)} casts, "
          f"{len(bad)} attacks on the auditor, {len(reg)} registered works")
    if problems:
        print("GROUNDING: FAIL")
        for p in problems[:20]:
            print("  -", p)
        return 1
    print("GROUNDING: PASS  (every shipped claim is locatable; the auditor rejects uncited, unknown-cited, "
          "off-cast and certainty-asserting output)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
