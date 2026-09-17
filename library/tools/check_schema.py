#!/usr/bin/env python3
"""Validate the published artefacts against the schemas in library/dataset/schema/.

The contract is only real if it is checked: this is what stops a new extract from silently shipping a
passage without a locator, or a reader that no longer satisfies the app-facing schema.
"""
import json, pathlib, sys
try:
    import jsonschema
except ImportError:
    print("jsonschema missing: pip install jsonschema"); sys.exit(2)
LIB = pathlib.Path(__file__).resolve().parents[1]   # .../library
ROOT = LIB.parent
ok = True
psh = json.loads((LIB / "schema/passage.json").read_text())
rows = [json.loads(l) for l in (LIB / "dataset/shards/passages.jsonl").read_text().splitlines() if l.strip()]
bad = 0
for r in rows:
    try: jsonschema.validate(r, psh)
    except Exception as e:
        bad += 1
        if bad <= 3: print("passage invalid:", str(e)[:130])
print(f"passages: {len(rows)} checked, {bad} invalid")
ok &= bad == 0
rp = LIB / "schema/reading.json"
if rp.exists():
    sch = json.loads(rp.read_text())
    for name in (str(ROOT / "examples" / "reading.example.json"),):
        f = pathlib.Path(name)
        if not f.exists():
            continue
        try:
            jsonschema.validate(json.loads(f.read_text()), sch); print(f"reading {name}: valid")
        except Exception as e:
            ok = False; print(f"reading {name}: INVALID - {str(e)[:200]}")

# rules + manifest + the outcome indexes the app reads
import json as _j
rf = LIB / "schema/rule.json"
if rf.exists():
    rsch = _j.loads(rf.read_text()); bad = 0; n = 0
    rp = LIB / "dataset/shards/rules.jsonl"
    if rp.exists():
        for l in rp.read_text().splitlines():
            if not l.strip(): continue
            n += 1
            try: jsonschema.validate(_j.loads(l), rsch)
            except Exception as e:
                bad += 1
                if bad <= 3: print("rule invalid:", str(e)[:130])
        print(f"rules: {n} checked, {bad} invalid"); ok &= bad == 0
    mf = LIB / "dataset/manifest.json"
    if mf.exists():
        try:
            jsonschema.validate(_j.loads(mf.read_text()), _j.loads((LIB / "schema/manifest.json").read_text()))
            print("manifest: valid")
        except Exception as e:
            ok = False; print("manifest INVALID:", str(e)[:160])
for name in ("by_figure", "by_house", "by_outcome"):
    f = LIB / "dataset/index" / f"{name}.jsonl"
    if not f.exists():
        ok = False; print(f"index/{name}.jsonl: MISSING - run `python3 engine/retrieve.py --build`")
        continue
    rows = [_j.loads(l) for l in f.read_text().splitlines() if l.strip()]
    empty = sum(1 for r in rows if not any(v for v in r.values()))
    print(f"index/{name}.jsonl: {len(rows)} rows, {empty} wholly empty")
    ok &= bool(rows) and empty == 0
print("SCHEMA CHECKS " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
