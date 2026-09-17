#!/usr/bin/env python3
"""Execute the `test_case` carried by each technique in kb/techniques.yaml.

A rule is only "computable" if it can be demonstrated, so every HIGH-confidence technique must
ship a case: a cast, a topic, a dotted path into the exported reading, and the value it must have.
`library/tools/validate.py` refuses a build where a HIGH rule has no passing case - that is what
stops the prose and the code from drifting apart.

    python3 library/tools/run_rule_tests.py            # all cases
    python3 library/tools/run_rule_tests.py --list     which rules are covered
    python3 library/tools/run_rule_tests.py --probe    dump every rule output for the first case
"""
from __future__ import annotations

import argparse, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT))

import yaml                                                   # noqa: E402
import export_reading as EX                                    # noqa: E402

TECH = ROOT / "kb" / "techniques.yaml"


def walk(obj, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                raise KeyError(f"{dotted}: cannot index a list with {part!r}") from None
        elif isinstance(cur, dict):
            if part not in cur:
                raise KeyError(f"{dotted}: no key {part!r} (have {sorted(cur)[:8]})")
            cur = cur[part]
        else:
            raise KeyError(f"{dotted}: {part!r} is not a container")
    return cur


def ok(got, pred, want) -> bool:
    """Six predicates - enough to state a rule's outcome without inventing a query language."""
    if pred == "equals":
        return got == want
    if pred == "contains":
        return want in (got or [])
    if pred == "contains_substring":
        if isinstance(got, str):
            return want in got
        return any(want in str(x) for x in (got or []))
    if pred == "not_empty":
        return bool(got) and got not in ({}, [], "", None)
    if pred == "min_items":
        try:
            return len(got) >= int(want)
        except TypeError:
            return False
    if pred == "has_flag":
        return any(isinstance(x, dict) and x.get("flag") == want for x in (got or []))
    if pred == "flag_prefix":
        return any(isinstance(x, dict) and str(x.get("flag", "")).startswith(want) for x in (got or []))
    raise ValueError(f"unknown predicate {pred!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()
    data = yaml.safe_load(TECH.read_text())
    if not isinstance(data, dict) or "techniques" not in data:
        print(f"FATAL: {TECH.relative_to(ROOT)} must parse as a mapping with a 'techniques:' key")
        print("       (upstream's scaffold had a corrupted file that parsed as a bare list)")
        return 2
    techs = data["techniques"]
    rows = [(k, v) for k, v in techs.items() if isinstance(v, dict)]
    rt = ROOT / "kb" / "rule_tests.yaml"
    cases = []
    if rt.exists():
        for c in yaml.safe_load(rt.read_text()).get("cases", []):
            c = dict(c); c["_id"] = c.pop("rule")
            cases.append(c)
    if cases:
        print(f"kb/rule_tests.yaml: {len(cases)} cases across {len({c['_id'] for c in cases})} rules\n")
        npass = nfail = 0
        for c in cases:
            try:
                r = EX.reading(c["mothers"], c.get("topic", "general"),
                              c.get("day"), c.get("hour"), bool(c.get("night")))
                got = walk(r, c["path"]) if c.get("path") else None
                if ok(got, c.get("predicate", "equals"), c.get("value")):
                    npass += 1
                    print(f"  PASS  {c['_id']:28s} [{c.get('strength','pin'):5s}] {c['path']} -> {json.dumps(got)[:52]}")
                else:
                    nfail += 1
                    print(f"  FAIL  {c['_id']:28s} {c['path']}: {c.get('predicate')} {json.dumps(c.get('value'))[:40]}"
                          f" but got {json.dumps(got)[:60]}")
            except Exception as e:                                  # noqa: BLE001
                nfail += 1
                print(f"  FAIL  {c['_id']:28s} case raised {type(e).__name__}: {str(e)[:90]}")
        if not a.list and not a.probe:
            print(f"\nrule cases: {npass} pass, {nfail} fail "
                  f"(proof={sum(1 for c in cases if c.get('strength')=='proof')}, "
                  f"pin={sum(1 for c in cases if c.get('strength')=='pin')})")
            if nfail:
                return 1
            return 0
    if a.list:
        for k, v in sorted(rows):
            tc = v.get("test_case")
            print(f"  {k:26s} conf={v.get('conf','?'):11s} test_case={'yes' if tc else 'NO'}")
        print(f"{len(rows)} techniques")
        return 0
    if a.probe:
        first = next((v for _, v in sorted(rows) if v.get("test_case")), None)
        r = EX.reading(first["test_case"]["mothers"], first["test_case"].get("topic", "general"))
        print(json.dumps(r, indent=2)[:4000])
        return 0

    npass = nfail = nskip = 0
    failures = []
    for k, v in sorted(rows):
        tc = v.get("test_case")
        if not tc:
            nskip += 1
            if str(v.get("conf", "")).upper() in {"HIGH", "MED"} and v.get("kind") != "named_only":
                failures.append((k, "no test_case but confidence " + str(v.get("conf"))))
            continue
        try:
            r = EX.reading(tc["mothers"], tc.get("topic", "general"),
                           tc.get("day"), tc.get("hour"), bool(tc.get("night")))
            got = walk(r, tc["path"])
            if ok(got, tc["equals"]):
                npass += 1
                print(f"  PASS  {k:26s} {tc['path']} = {json.dumps(got)[:44]}")
            else:
                nfail += 1
                failures.append((k, f"{tc['path']}: expected {json.dumps(tc['equals'])[:60]}, got {json.dumps(got)[:60]}"))
        except Exception as e:                                          # noqa: BLE001
            nfail += 1
            failures.append((k, f"case raised {type(e).__name__}: {e}"))
    for k, why in failures:
        print(f"  FAIL  {k:26s} {why}")
    print(f"\nnatural-language rules with a passing executable case: {npass} | failing: {nfail} "
          f"| untested (LOW/NAMED_ONLY allowed): {nskip}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
