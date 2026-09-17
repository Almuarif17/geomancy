#!/usr/bin/env python3
"""The gate that keeps a free corpus shippable.

Fails the build if anything copyrighted has crept into the bundle, if a passage has lost its
provenance, or if the interpretation engine's own checks break. Wire this to a pre-commit hook and a
CI job: it is the only thing that lets you add 500 books at speed and still sleep.

Usage: python3 library/tools/validate.py [--build library/dataset]
"""
import argparse, json, pathlib, re, subprocess, sys, sqlite3

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
ap = argparse.ArgumentParser(); ap.add_argument("--build", default=str(ROOT / "library/dataset"))
A = ap.parse_args()
out = pathlib.Path(A.build)
fails = []

def chk(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

db = out / "geomancy.sqlite"
chk("dataset is built", db.exists(),
    str(db) if db.exists() else "no geomancy.sqlite yet - run `make build` (it is generated, not tracked in git)")
if db.exists():
    con = sqlite3.connect(db); cur = con.cursor()
    works = dict(cur.execute("SELECT key, shippable_text FROM works").fetchall())
    # 1. licence gate
    bad = [w for (w,) in cur.execute("SELECT DISTINCT work FROM passages").fetchall() if not works.get(w)]
    chk("every passage's work is licensed for full text", not bad, str(bad[:3]))
    banned = re.compile(r"(?i)skinner|greer|regardie|enochian-dictionary")
    hits = [w for w in works if banned.search(w)]
    chk("no in-copyright author appears as a text source", not hits, str(hits))
    # 2. provenance gate
    n_no_loc = cur.execute("SELECT count(*) FROM passages WHERE locator IS NULL OR locator=''").fetchone()[0]
    n_no_conf = cur.execute("SELECT count(*) FROM passages WHERE confidence IS NULL OR confidence=''").fetchone()[0]
    chk("every passage carries a locator", n_no_loc == 0, f"{n_no_loc} missing")
    chk("every passage carries a confidence flag", n_no_conf == 0, f"{n_no_conf} missing")
    # 2b. Grid cells are terse by design (Calatarama and la Taille are tables; Hartmann is a lookup).
    #     Narrative rules - a quaestio, a motion ruling, an OCR pointer - must be at least a clause,
    #     because a truncated narrative row means an extractor slipped, not that the source is brief.
    TERSE_OK = ("answer_cell", "figure_in_house_ruling")
    q = "SELECT count(*) FROM passages WHERE kind NOT IN (%s) AND length(text)<20" % ",".join(
        "'" + k + "'" for k in TERSE_OK)
    short = cur.execute(q).fetchone()[0]
    chk("narrative rules are at least a clause long (grid cells exempt)", short == 0, f"{short} truncated")

    # 3. substance
    tot = cur.execute("SELECT count(*) FROM passages").fetchone()[0]
    kinds = dict(cur.execute("SELECT kind, count(*) FROM passages GROUP BY kind").fetchall())
    rules = cur.execute("SELECT count(*) FROM rules").fetchone()[0]
    rules_hi = cur.execute("SELECT count(*) FROM rules WHERE conf='HIGH'").fetchone()[0]
    chk("passage count above floor", tot >= 900, f"{tot} passages")
    chk("rules above floor and majority HIGH", rules >= 20 and rules_hi >= 12,
        f"{rules} rules, {rules_hi} HIGH")
    chk("rule keys unique + snake_case", all(re.fullmatch(r"[a-z0-9_]+", k) for (k,) in
        cur.execute("SELECT id FROM rules").fetchall()))
    con.close()

# 4. the engine's own checks must pass, or the data is decoration
r = subprocess.run([sys.executable, str(ROOT / "engine" / "test_deep_read.py")],
                   capture_output=True, text=True, cwd=str(ROOT))
chk("interpretation engine tests", r.returncode == 0, (r.stdout.strip().splitlines() or [""])[-1])

# 5. manifest integrity
mf = out / "manifest.json"
if mf.exists():
    m = json.loads(mf.read_text())
    chk("manifest lists licence policy", m.get("licence_summary", {}).get("policy", "").startswith("full text"))
    ob = (m.get("licence_summary") or {}).get("outbound_licence") or {}
    chk("manifest states the OUTBOUND terms in three layers",
        ob.get("layers") == 3 and "NC" in str((ob.get("curated") or {}).get("licence"))
        and (ob.get("cc0") or {}).get("licence") == "CC0-1.0",
        f"got {ob.get('layers')} layers, curated={str((ob.get('curated') or {}).get('licence'))[:40]}")
    chk("manifest records what was never used",
        len(m.get("licence_summary", {}).get("never_used", [])) > 0,
        str(len(m.get("licence_summary", {}).get("never_used", []))) + " blocked uploads recorded")
else:
    chk("manifest exists", False)


# ---------------------------------------------------------------- v0.2 gates
DISPOSITIONS = {"full", "summarize", "cite", "drop"}
BUCKETS = {"A", "B", "C"}
regf = ROOT / "registry" / "works.jsonl"
if regf.exists():
    rows = [json.loads(l) for l in regf.read_text().splitlines() if l.strip()]
    ids = {r["id"] for r in rows}
    alias = {a: r["id"] for r in rows for a in (r.get("aliases") or [])}
    chk("registry parses", len(rows) >= 15, f"{len(rows)} works registered")
    bad_b = [r["id"] for r in rows if r.get("licence_bucket") not in BUCKETS]
    bad_d = [r["id"] for r in rows if r.get("disposition") not in DISPOSITIONS]
    chk("every row has a legal licence_bucket + disposition", not bad_b and not bad_d,
        f"bad bucket={bad_b[:3]} bad disp={bad_d[:3]}")
    over = [r["id"] for r in rows if r.get("disposition") == "full" and r.get("licence_bucket") != "A"]
    chk("nothing is carried in full without being public domain", not over, f"violations: {over[:4]}")
    nohost = [r["id"] for r in rows if r.get("disposition") in {"full", "summarize"}
              and not r.get("host")]
    chk("carry/summarise rows name a host", not nohost, str(nohost[:4]))
    nostab = [r["id"] for r in rows if r.get("disposition") in {"full", "summarize"} and not r.get("why_trusted")]
    chk("every fetched work says why its host is trusted", not nostab, str(nostab[:4]))
    pf = LIB / "dataset/shards/passages.jsonl"
    if pf.exists():
        works = {json.loads(l).get("work") for l in pf.read_text().splitlines() if l.strip()}
        orphans = sorted(w for w in works if w and w not in ids and w not in alias)
        chk("every cited work is registered", not orphans, f"unregistered: {orphans[:5]}")
else:
    chk("registry/works.jsonl exists", False, "the corpus has no control plane")

rt = ROOT / "kb" / "rule_tests.yaml"
if rt.exists():
    r = subprocess.run([sys.executable, str(LIB / "tools/run_rule_tests.py")], capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or [""])[-1]
    chk("executable rule cases pass", r.returncode == 0, last[:120])
    n = sum(1 for l in rt.read_text().splitlines() if l.strip().startswith("- rule:"))
    chk("rule cases exist", n > 0, f"{n} cases")
else:
    chk("kb/rule_tests.yaml exists", False, "no rule is demonstrated, only described")

dc = LIB / "tools/check_docs_consistency.py"
if dc.exists():
    r = subprocess.run([sys.executable, str(dc)], capture_output=True, text=True)
    tail = " | ".join((r.stdout.strip().splitlines() or ["(no output)"])[-2:])[:200]
    if r.returncode != 0:
        tail += "  ||  " + " | ".join((r.stderr.strip().splitlines() or [""])[-1:])[:150]
    chk("prose counts match the build", r.returncode == 0, tail)

ap = ROOT / "app" / "test_app.py"
if ap.exists():
    r = subprocess.run([sys.executable, str(ap)], capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1][:170]
    if r.returncode != 0:
        tail += "  ||  " + " | ".join((r.stderr.strip().splitlines() or [""])[-1:])[:150]
    chk("reader app: routes answer, citations survive, page stays self-contained", r.returncode == 0, tail)

mcp = ROOT / "server" / "mcp_geomancy.py"
if mcp.exists():
    for mode, what in (("--self-test", "protocol surface (17 checks)"),
                       ("--transport-test", "real stdio pipes, framing and garbage tolerance")):
        r = subprocess.run([sys.executable, str(mcp), mode], capture_output=True, text=True)
        tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1][:150]
        if r.returncode != 0:
            tail += "  ||  " + " | ".join((r.stderr.strip().splitlines() or [""])[-1:])[:120]
        chk(f"MCP server: {what}", r.returncode == 0, tail)

sc = LIB / "tools/score_coverage.py"
if sc.exists():
    r = subprocess.run([sys.executable, str(sc), "--check"], capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or ["(no output)"])[0][:120]
    chk("coverage scoreboard is fresh against the shipped files", r.returncode == 0, tail)

ls = LIB / "tools/check_licence_scope.py"
if ls.exists():
    r = subprocess.run([sys.executable, str(ls)], capture_output=True, text=True)
    tail = " | ".join((r.stdout.strip().splitlines() or ["(no output)"])[-2:])[:200]
    if r.returncode != 0:
        tail += "  ||  " + " | ".join((r.stderr.strip().splitlines() or [""])[-1:])[:150]
    chk("licence scope: every tracked path is declared by exactly one layer", r.returncode == 0, tail)

gr = LIB / "tools/check_grounding.py"
if gr.exists():
    r = subprocess.run([sys.executable, str(gr)], capture_output=True, text=True)
    tail = " | ".join((r.stdout.strip().splitlines() or ["(no output)"])[-2:])[:200]
    if r.returncode != 0:
        tail += "  ||  " + " | ".join((r.stderr.strip().splitlines() or [""])[-1:])[:150]
    chk("grounding: every claim citable, licence-safe, and the auditor bites", r.returncode == 0, tail)

gg = LIB / "tools/check_calatarama_grid.py"
if gg.exists():
    r = subprocess.run([sys.executable, str(gg)], capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or [""])[-1]
    if r.returncode != 0:
        # CI once failed this gate with no explanation because only stdout was read; a tool that
        # cannot report why it failed is a worse gate than no gate.
        err = " | ".join((r.stderr.strip().splitlines() or ["(no output)"])[-2:])[:220]
        last = (last + "  ||  " + err).strip(" |")
    chk("calatarama grid integrity (no figure dropped from every house)", r.returncode == 0, last[:230])

techf = ROOT / "kb" / "techniques.yaml"
if techf.exists():
    try:
        tdata = yaml.safe_load(techf.read_text())
        t = (tdata or {}).get("techniques", {}) if isinstance(tdata, dict) else {}
        chk("techniques.yaml is a mapping with a techniques: key", bool(t),
            "a bare list here is how the upstream scaffold broke")
        missing = [k for k, v in t.items() if not (v or {}).get("source")]
        chk("every technique cites a source", not missing, str(missing[:4]))
        lowconf = [k for k, v in t.items() if (v or {}).get("conf") == "HIGH"
                    and str((v or {}).get("status", "")).upper() != "NAMED_ONLY"]
        covered = set()
        if rt.exists():
            covered = {yaml.safe_load(rt.read_text())["cases"][i].get("rule")
                       for i in range(len(yaml.safe_load(rt.read_text())["cases"]))}
        uncov = [k for k in lowconf if k not in covered]
        chk("every HIGH rule has a case (implemented rules only)", not uncov, f"uncovered: {uncov[:5]}")
    except Exception as e:                                              # noqa: BLE001
        chk("techniques.yaml parses", False, str(e)[:120])

ev = subprocess.run([sys.executable, str(ROOT / "engine/evaluate.py"), "--quick"],
                    capture_output=True, text=True)
chk("engine agrees with the independent oracle (sampled sweep)", ev.returncode == 0,
    (ev.stdout.strip().splitlines() or [""])[-1][:110])

for rel in ("library/dataset/index/by_outcome.jsonl", "library/dataset/bundles.json"):
    f = ROOT / rel
    ok_ = f.exists() and f.stat().st_size > 200
    chk(f"{rel} shipped", ok_, "" if ok_ else "run: python3 engine/retrieve.py --build")
for rel in ("types/geomancy.d.ts", "library/dataset/openapi.yaml"):
    chk(f"{rel} generated", (ROOT / rel).exists(), "run: python3 library/tools/gen_types.py")

lk = subprocess.run([sys.executable, str(LIB / "tools/check_public_leaks.py")], capture_output=True, text=True)
chk("no identity, credential or personal-casting leakage", lk.returncode == 0,
    (lk.stdout.strip().splitlines() or [""])[-1][:110])

print("\n" + ("BUILD IS CLEAN" if not fails else f"{len(fails)} gate(s) failed: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
