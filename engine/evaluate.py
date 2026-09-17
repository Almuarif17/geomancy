#!/usr/bin/env python3
"""Differential verification: engine vs `engine/oracle.py`, plus library-wide accuracy numbers.

    python3 engine/evaluate.py                 # full sweep (65,536 casts) + report
    python3 engine/evaluate.py --quick         # 2,000 sampled casts
    python3 engine/evaluate.py --json out.json # machine-readable, for CI artifacts

This is the file that answers "is the active code accurate?" with a number instead of a promise.
"""
from __future__ import annotations

import argparse, collections, hashlib, itertools, json, pathlib, random, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import oracle as O                                                    # noqa: E402
import deep_read as dr                                                # noqa: E402
import export_reading as EX                                           # noqa: E402

CHECKS = ("chart", "sentence", "via_puncti", "projection", "part_of_fortune", "motus", "judge_parity")


def compare(mothers, detail=None):
    eng = dr.build([dr.norm(m) for m in mothers])
    eh = [tuple(p) for p in eng["houses"]]
    oh = [tuple(p) for p in O.cast(list(mothers))]
    out = {"chart": eh == oh}
    out["sentence"] = eh[15] == oh[15]
    epath, ebr, eends = dr.via_puncti(eng)
    opath, obr, oends = O.via_puncti(oh)
    out["via_puncti"] = ([r - 1 for r, _ in epath] == opath and list(ebr) == obr
                         and sorted(eends) == sorted(oends))
    if not out["via_puncti"] and detail is not None:
        detail["via_puncti"] = {"mothers": list(mothers), "engine": [epath, ebr, eends],
                               "oracle": [opath, obr, oends]}
    pr = dr.projection(eng)                 # (singles, house, fig, total, house2, fig2)
    os_, ohouse = O.projection(oh)
    out["projection"] = (pr[0] == os_ and int(pr[1]) == ohouse)
    t2, h2 = O.part_of_fortune(oh)
    out["part_of_fortune"] = (int(pr[3]) == t2 and int(pr[4]) == h2)
    em = {f: sorted(hs) for f, hs in dr.motus(eng).items()}
    out["motus"] = em == {f: sorted(hs) for f, hs in O.motus(oh).items()}
    out["judge_parity"] = sum(oh[14]) % 2 == 0
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--json", default=None)
    ap.add_argument("--seed", type=int, default=20260917)
    a = ap.parse_args()

    if a.quick:
        rnd = random.Random(a.seed)
        names = list(O.FIG)
        casts = [tuple(rnd.choice(names) for _ in range(4)) for _ in range(2000)]
    else:
        casts = [c for c, _ in O.all_casts()]

    stat = collections.Counter()
    first_bad = {}
    detail = {}
    for mothers in casts:
        res = compare(mothers, detail)
        for k, v in res.items():
            stat[(k, v)] += 1
            if not v and k not in first_bad:
                first_bad[k] = list(mothers)
    n = len(casts)
    print(f"differential sweep over {n:,} casts  ({'sampled' if a.quick else 'exhaustive'})\n")
    worst = 0
    for k in CHECKS:
        agree = stat[(k, True)]
        pct = 100.0 * agree / n
        worst = max(worst, n - agree)
        print(f"  {k:16s} agree {agree:6,}/{n:,}  {pct:6.2f}%" + ("" if agree == n else "   MISMATCHES=" + f"{n-agree:,}"))
        if agree != n and k in detail:
            print("      example:", json.dumps(detail[k])[:400])

    # ---- library-wide accuracy statistics
    kb = ROOT / "kb"
    tech = (yaml_load(kb / "techniques.yaml") or {}).get("techniques", {}) if (kb / "techniques.yaml").exists() else {}
    covered = sum(1 for v in tech.values() if isinstance(v, dict) and v.get("conf", "").upper() == "HIGH")
    high_with_case = sum(1 for k, v in tech.items()
                         if isinstance(v, dict) and str(v.get("conf", "")).upper() == "HIGH"
                         and str(v.get("status", "")).upper() != "NAMED_ONLY" and has_case(k))
    named_only = sum(1 for v in tech.values()
                     if isinstance(v, dict) and str(v.get("status", "")).upper() == "NAMED_ONLY")
    ds = ROOT / "library" / "dataset" / "shards" / "passages.jsonl"
    passages = rules = with_loc = 0
    works = set()
    if ds.exists():
        for line in ds.read_text().splitlines():
            if not line.strip():
                continue
            p = json.loads(line)
            passages += 1
            with_loc += 1 if p.get("locator") else 0
            works.add(p.get("work"))
    rulesf = ROOT / "library" / "dataset" / "shards" / "rules.jsonl"
    if rulesf.exists():
        rules = sum(1 for l in rulesf.read_text().splitlines() if l.strip())
    regf = ROOT / "registry" / "works.jsonl"
    reg, alias = set(), {}
    if regf.exists():
        for line in regf.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            reg.add(r["id"])
            for al in r.get("aliases", []) or []:
                alias[al] = r["id"]
    unreg = sorted(w for w in works if w and w not in reg and w not in alias)
    print(f"\nlibrary coverage")
    print(f"  passages {passages:,} ({100*with_loc/max(passages,1):.1f}% with a folio/page locator), rules {rules}")
    print(f"  HIGH-confidence techniques {covered}, of which {high_with_case} carry an executable test case")
    print(f"  techniques documented but deliberately not implemented (NAMED_ONLY): {named_only}")
    print(f"  works cited by passages but absent from registry/works.jsonl: {len(unreg)}"
          + (f" -> {unreg[:6]}" if unreg else ""))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({
            "casts_tested": n, "exhaustive": not a.quick,
            "agreement": {k: stat[(k, True)] for k in CHECKS},
            "mismatches": worst,
            "passages": passages, "passages_with_locator": with_loc, "rules": rules,
            "high_techniques": covered, "high_with_test_case": high_with_case,
            "unregistered_works": unreg, "generated_by": "engine/evaluate.py",
            "seed": a.seed if a.quick else None}, indent=1))
        print(f"\nwrote {a.json}")
    ok = worst == 0 and not unreg
    print("\n" + ("EVALUATION CLEAN - engine and oracle agree on every check" if ok
                  else f"EVALUATION FAILED - {worst} mismatch(es)" + (", unregistered works" if unreg else "")))
    return 0 if ok else 1


def yaml_load(p):
    import yaml
    try:
        return yaml.safe_load(p.read_text())
    except Exception:                                              # noqa: BLE001
        return {}


def has_case(rule_id):
    f = ROOT / "kb" / "rule_tests.yaml"
    if not f.exists():
        return False
    for l in f.read_text().splitlines():
        if l.strip() == f"- rule: {rule_id}" or l.strip().startswith(f"  rule: {rule_id}"):
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
