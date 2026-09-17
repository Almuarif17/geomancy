#!/usr/bin/env python3
# ruff: noqa: E501
"""The reader: a local app over the library, standard library only.

    python3 app/server.py            # http://127.0.0.1:8044
    python3 app/server.py --port 9000

Why a server at all, when the dataset is static? Because the interesting half of this library is not the
data, it is the *cast* and the *audit* - both computed - and a page that only reads JSON files would have to
re-implement the engine in JavaScript. A second implementation of the rules is a second source of truth, and
the two drift. So the browser asks, and `engine/` answers, exactly the way any future app will.

What this app is for, besides testing: it is the place where a preference can be expressed. `app/preferences.json`
changes what you see and in what order - which works are quoted first, whether raw quotations are shown, how
much detail the gaps get, which topics you actually care about. It never changes what a source said: the
rendering layer sorts and labels, `engine/ground.py` decides content. That boundary is the whole design.

No third-party assets are fetched: no CDN, no webfont, no analytics. The page must work on a train, in a
sandboxed preview, and five years from now when a CDN path has rotted.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP = pathlib.Path(__file__).resolve().parent
DS = ROOT / "library" / "dataset"
KB = ROOT / "kb"
PREFS = APP / "preferences.json"

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

_cache: dict = {}


# ------------------------------------------------------------------ data, read once per process
def voices() -> list[dict]:
    if "voices" not in _cache:
        for cand in (DS / "tables/voices.jsonl", KB / "voices.jsonl"):
            if cand.exists():
                _cache["voices"] = [json.loads(l) for l in cand.read_text().splitlines() if l.strip()]
                break
        else:
            _cache["voices"] = []
    return _cache["voices"]


def outcomes() -> list[dict]:
    if "outcomes" not in _cache:
        f = DS / "index/by_outcome.jsonl"
        _cache["outcomes"] = [json.loads(l) for l in f.read_text().splitlines() if l.strip()] if f.exists() else []
    return _cache["outcomes"]


def coverage() -> dict:
    if "coverage" not in _cache:
        f = KB / "coverage.json"
        _cache["coverage"] = json.loads(f.read_text()) if f.exists() else {}
    return _cache["coverage"]


PRESENTATION_KEYS = ("show_quotes", "preferred_works_first", "min_voices_for_confidence", "gap_detail",
                    "tone", "house_labels", "topics_pinned", "hide_unreliable_polarity", "max_claims")


def merge_prefs(client: dict | None) -> dict:
    """File preferences, with a client's overrides applied - presentation keys only.

    A phone cannot write app/preferences.json, so the mobile app sends its settings with each request. What
    it may not do, in either direction, is reach the content layer: keys outside the whitelist are dropped and
    reported, because the moment a client can pick which ruling to display the library stops being a source.
    """
    base = preferences()
    if not client:
        return base
    kept = {k: v for k, v in client.items() if k in PRESENTATION_KEYS}
    ignored = sorted(set(client) - set(kept))
    out = {**base, **kept}
    if ignored:
        out["ignored_client_keys"] = ignored
    return out


def preferences() -> dict:
    try:
        p = json.loads(PREFS.read_text())
    except Exception:                                            # noqa: BLE001
        p = {}
    base = {"show_quotes": True, "preferred_works_first": [], "min_voices_for_confidence": 2,
            "gap_detail": "brief", "tone": "plain", "house_labels": "roman", "topics_pinned": [],
            "hide_unreliable_polarity": True, "max_claims": 60}
    return {**base, **p}


def repo_version() -> str:
    """The version is the top CHANGELOG heading - the same line the tagger reads - because the manifest is
    deliberately content-addressed and carries no version string of its own."""
    for line in (ROOT / "CHANGELOG.md").read_text().splitlines():
        if line.startswith("## "):
            return line[3:].split(" -")[0].strip()
    return "unreleased"


def manifest() -> dict:
    if "manifest" not in _cache:
        f = DS / "manifest.json"
        _cache["manifest"] = json.loads(f.read_text()) if f.exists() else {}
    return _cache["manifest"]


# ------------------------------------------------------------------ the pipeline, described from live files
def how() -> dict:
    """Not a README. Every stage reports the counts and the gate that guards it, read right now."""
    man, cov = manifest(), coverage()
    counts = man.get("counts", {})
    from engine import ground as G
    stages = [
        {"n": 1, "name": "Acquire", "what": ("Fetch a candidate work from a host that has been trustworthy for "
                                             "years, and record why we trust it before anything else happens."),
         "files": "library/tools/sync_corpus.py, registry/works.jsonl",
         "numbers": {"works registered": len(_lines(ROOT / "registry/works.jsonl"))},
         "gate": "validate: 'carry/summarise rows name a host' + 'every fetched work says why its host is trusted'"},
        {"n": 2, "name": "Triage", "what": ("Decide per work: carry the full text, summarise, or cite only. "
                                            "This is a legal judgement, so it is a field on every row and not a "
                                            "mood."),
         "files": "library/tools/triage.py, LICENSE_POLICY.md",
         "numbers": {"full-text works": len(man.get("licence_summary", {}).get("full_text_sources", [])),
                     "cite-only works": len(man.get("licence_summary", {}).get("cite_only_sources", [])),
                     "blocked uploads": len(man.get("licence_summary", {}).get("never_used", []))},
         "gate": "validate: 'nothing is carried in full without being public domain'"},
        {"n": 3, "name": "Extract", "what": ("Turn pages into rows with a locator attached, then prove the "
                                             "extraction by counting cells a human can check."),
         "files": "scripts/extract_*.py, kb/*_grid.json",
         "numbers": {"passages": counts.get("passages"), "calatarama cells": cov.get("components", {})
                     .get("grid_cells", {}).get("count")},
         "gate": "check_calatarama_grid: cell count per house, every absence explained in editorial_notes"},
        {"n": 4, "name": "Adjudicate", "what": ("Where sources conflict, decide which rule the engine applies, "
                                                 "and keep the conflict visible as data."),
         "files": "kb/figures.yaml, kb/rule_tests.yaml",
         "numbers": {"rule cases": cov.get("reported_only", {}).get("rule_cases_total"),
                     "proved twice": cov.get("components", {}).get("rule_cases_proof", {}).get("count")},
         "gate": "run_rule_tests: proof cases must pass against an independent oracle, pins must not move"},
        {"n": 5, "name": "Compute", "what": ("Figures are arithmetic: mothers to daughters to nieces to "
                                             "witnesses to Judge to Sentence. Nothing is looked up from a table, "
                                             "so no transcription error can hide in a lookup."),
         "files": "engine/oracle.py, engine/deep_read.py, library/dataset/core_facts.json",
         "numbers": {"casts in the space": 65536, "attainable judges": 8,
                     "oracle agreement": "65,536 of 65,536"},
         "gate": "engine/evaluate.py: the whole space, diffed against an independently written oracle"},
        {"n": 6, "name": "Ground", "what": ("For a cast and a question, assemble only what the sources say, "
                                            "each claim carrying the voice ids it came from; where nothing "
                                            "speaks, say that instead of filling the space."),
         "files": "engine/ground.py, kb/voices.jsonl",
         "numbers": {"voices": len(voices()), "claim keys": cov.get("reported_only", {}).get("claim_keys"),
                     "measurable disagreements": cov.get("reported_only", {})
                     .get("measurable_cross_source_disagreements")},
         "gate": "check_grounding: no quotation ships for a non-full work, every voice is locatable, and the "
                 "auditor is attack-tested against four deliberately bad readings"},
        {"n": 7, "name": "Serve", "what": ("Apps pull what one outcome needs - not the whole corpus - through "
                                           "indexes, bundles, a typed contract, this reader, and an MCP server."),
         "files": "engine/retrieve.py, library/dataset/index/, types/geomancy.d.ts, server/mcp_geomancy.py",
         "numbers": {"outcomes": len(outcomes()), "MCP tools": 6,
                     "bundle sizes": {k: f"{v['bytes'] // 1024}K" for k, v in
                                      (json.loads((DS / 'bundles.json').read_text()).get("screens", {}).items())}
                     if (DS / "bundles.json").exists() else {}},
         "gate": "check_schema: index rows validate against the generated row contract, and the published "
                 "TypeScript is linted for valid, non-dangling declarations"},
        {"n": 8, "name": "Licence", "what": ("Three layers, declared per path: code MIT, the arithmetic CC0, "
                                             "the curated text CC BY-NC with a commercial licence."),
         "files": "LICENSING.md, LICENSE_DATA.md, LICENSE_POLICY.md",
         "numbers": {"layers": 3, "dataset licence stated in manifest":
                     bool(man.get("licence_summary", {}).get("outbound_licence"))},
         "gate": "check_licence_scope: a tracked path claimed by no layer or by two fails the build"},
    ]
    return {"stages": stages, "score": cov.get("score_of_100"),
            "note": ("generated from the shipped files by /api/how - this cannot disagree with the build, "
                     "because it is the build"),
            "ground_module": str(pathlib.Path(G.__file__).relative_to(ROOT))}


def _lines(p: pathlib.Path) -> list[str]:
    return [l for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


# ------------------------------------------------------------------ the view: preferences applied here, nowhere else
def render(reading: dict, prefs: dict) -> dict:
    """Sort, label and truncate. Never add, never reword: engine/ground.py owns content."""
    order = {w: i for i, w in enumerate(prefs.get("preferred_works_first") or [])}
    claims = list(reading.get("claims", []))

    quesited = reading.get("quesited_house")

    def rank(c: dict) -> tuple:
        works = (c.get("cites") or {}).get("works") or []
        best = min([order.get(w, 99) for w in works], default=99)
        # the question asked comes before the rest of the chart: an app that shows house II first on a
        # marriage question reads like a table dump, however accurate each row is
        near = 0 if (c.get("house") == quesited or c.get("role")) else 1
        return (near, 0 if c["type"] in ("sourced_ruling", "sources_disagree") else 1, best, c["type"])

    claims.sort(key=rank)
    out = []
    for c in claims[: int(prefs.get("max_claims", 60))]:
        row = {"type": c["type"], "text": c["text"], "mode": c.get("mode"),
               "figure": c.get("figure"), "house": c.get("house"), "role": c.get("role"),
               "leans": c.get("leans") or [], "n_voices": (c.get("cites") or {}).get("n_voices") or 0,
               "works": (c.get("cites") or {}).get("works") or []}
        ids = (c.get("cites") or {}).get("voice_ids") or []
        if prefs.get("show_quotes"):
            row["quotes"] = [{"id": v, "text": (_vb_lookup(v) or {}).get("quote") or "",
                              "authority": (_vb_lookup(v) or {}).get("authority") or "",
                              "locator": (_vb_lookup(v) or {}).get("locator") or "",
                              "work": (_vb_lookup(v) or {}).get("work") or ""} for v in ids[:6]]
        if prefs.get("hide_unreliable_polarity"):
            row["polarity_note"] = ("leans inferred from vocabulary, not stated - shown only when a source "
                                     "says it" if any(_low_reliability(v) for v in ids) else "")
        n = row["n_voices"]
        row["strength"] = ("thin" if n < int(prefs.get("min_voices_for_confidence", 2)) else
                           "single-source" if n < 3 else "multi-source")
        out.append(row)

    gaps = reading.get("gaps") or {}
    detail = prefs.get("gap_detail", "brief")
    gap_lines = []
    if detail != "silent":
        for g in (reading.get("claims") or []):
            if g.get("type") == "no_source_ruling":
                gap_lines.append(g["text"] if detail == "full" else g["text"].split(".")[0])
    summary = ""
    if prefs.get("tone") == "plain" and out:
        lead = [o for o in out if o["type"] in ("sourced_ruling", "sources_disagree")]
        summary = (f"{len(lead)} cited statement(s) from {len({w for o in out for w in o['works']})} work(s); "
                   f"{len(gap_lines)} silence(s) named.") if lead else "the sources are silent on this"
    return {"claims": out, "gaps": gaps, "gap_lines": gap_lines, "summary": summary,
            "audit": reading.get("audit") or {}, "citations": reading.get("citations") or {},
            "quesited_house": reading.get("quesited_house"), "topic": reading.get("topic"),
            "standing": reading.get("standing") or "", "prefs_echo": prefs}


_VB: dict = {}


def _vb_lookup(vid: str) -> dict | None:
    if "vb" not in _VB:
        from engine import ground as G
        _VB["vb"] = G.VoiceBook()
    return _VB["vb"].lookup(vid)


def _low_reliability(vid: str) -> bool:
    v = _vb_lookup(vid)
    return bool(v and v.get("polarity_reliability") == "low")


# ------------------------------------------------------------------ chart
def chart(mothers: list[str]) -> dict:
    from engine import deep_read as D
    c = D.build(mothers)
    shield = [D.fig(p) for p in c["houses"]]
    return {"mothers": mothers, "houses": {str(i + 1): shield[i] for i in range(12)},
            "patterns": {str(i + 1): list(c["houses"][i]) for i in range(16)},
            "court": {"witness_left": D.fig(c["witnesses"][0]), "witness_right": D.fig(c["witnesses"][1]),
                      "judge": D.fig(c["judge"]), "sentence": D.fig(c["sentence"])},
            "judge": D.fig(c["judge"]), "reconciler": D.fig(c["sentence"]),
            "daughters": shield[4:8], "nieces": shield[8:12]}


STATIC = {"/m": ("mobile.html", "text/html; charset=utf-8"),
          "/mobile.html": ("mobile.html", "text/html; charset=utf-8"),
          "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
          "/sw.js": ("sw.js", "application/javascript; charset=utf-8"),
          "/icon-192.png": ("icon-192.png", "image/png"),
          "/icon-512.png": ("icon-512.png", "image/png")}


# ---------------------------------------------------------------- counting rule, in one place
def rows_to_values(rows: list[int]) -> list[int]:
    """Taps become dots the way the tradition counts them: make the marks, count them off in pairs, and what
    is left over decides the row - one dot if the remainder is odd, two if the pair closes even.

    This is deliberately the same arithmetic as `engine.deep_read.add()`, which turns two rows into one:
    `(x + y) % 2` picks 1 else 2. If the app ever invents its own counting rule, the first figure and the
    last agree with nothing, so the tests compare this function against the engine rather than trusting the
    comment.
    """
    out = []
    for r in rows:
        n = int(r)
        if n < 1:
            raise ValueError("a row needs at least one tap; an empty row is not a figure")
        out.append(1 if n % 2 else 2)
    return out


def mothers_from_values(values: list[int]) -> list[str]:
    """Sixteen row-values, taken in blocks of four top-to-bottom, are the four mothers."""
    from engine import deep_read as D
    if len(values) != 16:
        raise ValueError(f"16 rows are needed to cast, got {len(values)}")
    return [D.fig(list(values[4 * i:4 * i + 4])) for i in range(4)]


def parents_label(c, i: int) -> str:
    """How position i+1 was produced, in the words a person can check with their own eyes."""
    from engine import deep_read as D
    tr = c.get("transposed") or {}
    if i < 4:
        return "cast directly: four rows of taps, counted in pairs"
    if i in tr:
        return f"row {tr[i] + 1} of the four mothers, read across as a figure"
    par = (c.get("parents") or {}).get(i)
    if not par:
        return ""
    a, b = par
    pa, pb = list(c["houses"][a]), list(c["houses"][b])
    lab = lambda k: ROMAN[k] if k < 12 else ["left witness", "right witness", "Judge", "Sentence"][k - 12]
    merged = ", ".join(f"{x}+{y}->{'odd so 1' if (x + y) % 2 else 'even so 2'}" for x, y in zip(pa, pb))
    return f"{lab(a)} + {lab(b)}: {merged}"


def chart16(mothers: list[str], topic: str | None = None) -> dict:
    import yaml
    from engine import deep_read as D
    c = D.build(mothers)
    figs = yaml.safe_load((KB / "figures.yaml").read_text())["figures"]
    hm_raw = yaml.safe_load((KB / "houses.yaml").read_text())["houses"]
    court = ["left witness", "right witness", "Judge", "Sentence / Reconciler"]
    positions = []
    for i in range(16):
        pat = [int(x) for x in c["houses"][i]]
        name = D.fig(pat)
        meta = figs.get(name) or {}
        hm = (hm_raw.get(str(i + 1)) or hm_raw.get(i + 1) or {}) if i < 12 else {}
        positions.append({
            "position": i + 1, "label": ROMAN[i] if i < 12 else court[i - 12],
            "kind": "house" if i < 12 else "court",
            "house_name": hm.get("english"), "latin": hm.get("latin"), "cal_scope": (hm.get("cal") or {}).get("aspect"),
            "figure": name, "arabic": meta.get("arabic"), "pattern": pat,
            "rows": [{"row": r + 1, "dots": pat[r], "single": pat[r] == 1} for r in range(4)],
            "dots": sum(pat), "even": sum(pat) % 2 == 0,
            "element": meta.get("element"), "quality": meta.get("quality"), "motion": meta.get("motion"),
            "planet": meta.get("planet"), "gender": meta.get("gender"), "time_unit": meta.get("time_unit"),
            "ifa_odu": meta.get("ifa_odu"), "derived_from": parents_label(c, i)})
    tech = {}
    for fn, needs_topic in (("validity", False), ("motus", False), ("parentage", False), ("via_puncti", False),
                            ("projection", False), ("humours", True), ("perfection", True), ("triplicities", True),
                            ("who", True), ("where", True), ("when", True), ("crossread", False)):
        try:
            f = getattr(D, fn)
            tech[fn] = f(c, topic) if needs_topic and topic else (f(c, topic) if needs_topic else f(c))
        except Exception as e:                                  # noqa: BLE001
            tech[fn] = {"error": f"{type(e).__name__}: {e}"}
    return {"mothers": mothers, "positions": positions, "techniques": tech,
            "topic": topic, "validity_note": "the shield is 16 figures: 12 houses then the court"}


def prove(mothers: list[str], topic: str | None) -> dict:
    """What the 'prove it' button opens: the arithmetic, the independent check, and the sources - kept out of
    the prose so a sentence is never its own footnote."""
    from engine import ground as G
    ch = chart16(mothers, topic)
    c = chart(mothers)
    rd = G.assemble({"houses": {int(k): v for k, v in c["houses"].items()}, **c["court"]}, topic, G.VoiceBook())
    vb = G.VoiceBook()
    pos_by_fig: dict = {}
    for row in ch["positions"]:
        pos_by_fig.setdefault(row["figure"], []).append(row)
    claims = []
    for k, cl in enumerate(rd["claims"]):
        ids = (cl.get("cites") or {}).get("voice_ids") or []
        voices = []
        for vid in ids:
            v = vb.lookup(vid) or {}
            voices.append({"id": vid, "quote": v.get("quote"), "gloss": v.get("gloss"),
                           "authority": v.get("authority"), "through": v.get("through"),
                           "locator": v.get("locator"), "work": v.get("work"),
                           "licence": v.get("licence"), "cite_only": v.get("cite_only"),
                           "polarity": v.get("polarity"), "polarity_reliability": v.get("polarity_reliability")})
        fig, house = cl.get("figure"), cl.get("house")
        rows = pos_by_fig.get(fig) or []
        which = next((r for r in rows if r["position"] == house), rows[0] if rows else None)
        arithmetic = (f"{which['label']}: rows {which['pattern']} = {which['dots']} dots, "
                      f"{'even' if which['even'] else 'odd'} - {which['derived_from'] or 'cast directly'}"
                      if which else "court figure: derived from the witnesses above")
        claims.append({"i": k, "type": cl["type"], "text": cl["text"], "figure": fig, "house": house,
                       "role": cl.get("role"), "mode": cl.get("mode"), "arithmetic": arithmetic,
                       "works": sorted({v["work"] for v in voices if v.get("work")}),
                       "quotable": [v for v in voices if v.get("quote")],
                       "cite_only": [v for v in voices if not v.get("quote")],
                       "n_voices": len(ids)})
    diff = {}
    ev = DS / "evaluation.json"
    if ev.exists():
        e = json.loads(ev.read_text())
        diff = {"casts_tested": e.get("casts_tested"), "mismatches": e.get("mismatches"),
                "checks": {k: v for k, v in (e.get("agreement") or {}).items()},
                "exhaustive": e.get("exhaustive")}
    return {"topic": topic, "chart": ch, "claims": claims, "differential": diff,
            "reading_gaps": rd.get("gaps"), "audit": G.validate(rd, vb)}


def copy_text(mothers: list[str], topic: str | None) -> str:
    """The plain-text block a user pastes into a chat or a notebook: one line per position, figures, dots,
    correspondences and the derived chain, then the reading, then the silence."""
    ch = chart16(mothers, topic)
    L = [f"geomancy chart - {' '.join(mothers)}" + (f" - question: {topic}" if topic else ""), ""]
    r16 = ROMAN + ["XIII", "XIV", "XV", "XVI"]
    for r in ch["positions"]:
        # the four court figures are the thirteenth to sixteenth places of the same shield, so the copied block
        # numbers them too: a notebook pasted with this should still show where each figure sits
        num = r16[r["position"] - 1]
        tag = num if r["kind"] == "house" else f"{num} {r['label']}"
        head = f"{tag:>23}" + (f" {r['house_name']}" if r.get("house_name") else "")
        bits = [f"{r['figure']}", f"{r['dots']} dots ({'even' if r['even'] else 'odd'})"]
        for key, lab in (("element", "element"), ("quality", "quality"), ("motion", "motion"),
                         ("planet", "ruler"), ("time_unit", "time")):
            if r.get(key):
                bits.append(f"{lab} {r[key]}")
        L.append(f"{head}: " + ", ".join(bits))
        if r.get("derived_from"):
            L.append(f"      from {r['derived_from']}")
    vp = (ch["techniques"].get("via_puncti") or {})
    if vp:
        L += ["", f"way of the points: {json.dumps(vp, ensure_ascii=False, default=str)[:400]}"]
    pf = (ch["techniques"].get("perfection") or {}) if topic else {}
    if pf:
        L += [f"perfection: {json.dumps(pf, ensure_ascii=False, default=str)[:400]}"]
    L += ["", "not advice, and not a prediction: these are documented claims by named authorities."]
    return "\n".join(L)


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a) -> None:      # quieter: one line per request, on stderr
        sys.stderr.write("  %s\n" % (a[1] if len(a) > 1 else a))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", getattr(self, "_cache_ctl", "no-store"))
        self.end_headers()
        self.wfile.write(body)

    def json_out(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, indent=1, ensure_ascii=False, default=str).encode(),
                   "application/json; charset=utf-8")

    def do_POST(self) -> None:             # noqa: N802
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:                                  # noqa: BLE001
            return self.json_out({"error": f"body must be JSON: {e}"}, 400)
        try:
            if u.path == "/api/cast_from_rows":
                if "rows" in body:
                    values = rows_to_values(body["rows"])
                elif "values" in body:
                    values = [int(v) for v in body["values"]]
                    if any(v not in (1, 2) for v in values):
                        return self.json_out({"error": "values must be 1 or 2 dots"}, 400)
                    if len(values) != 16:
                        return self.json_out({"error": f"16 rows are needed, got {len(values)}"}, 400)
                else:
                    return self.json_out({"error": "send rows (tap counts) or values (1/2 per row)"}, 400)
                moms = mothers_from_values(values)
                c = chart(moms)
                c["method"] = body.get("method") or "unknown"
                c["row_values"] = values
                c["rows_in"] = [int(x) for x in (body.get("rows") or [0] * 16)]
                c["mothers_arithmetic"] = [
                    {"mother": ROMAN[i], "rows": values[4 * i:4 * i + 4],
                     "taps": [int(x) for x in (body.get("rows") or [0] * 16)][4 * i:4 * i + 4],
                     "figure": moms[i], "dots": sum(values[4 * i:4 * i + 4]),
                     "pairs": [int(x) // 2 for x in (body.get("rows") or [0] * 16)][4 * i:4 * i + 4],
                     "remainder_odd": [bool(int(x) % 2) for x in (body.get("rows") or [0] * 16)][4 * i:4 * i + 4]}
                    for i in range(4)]
                topic = (body.get("topic") or "").strip()
                if topic:
                    from engine import ground as G
                    rd = G.assemble({"houses": {int(k): v for k, v in c["houses"].items()}, **c["court"]},
                                    topic, G.VoiceBook())
                    rd["audit"] = G.validate(rd, G.VoiceBook())
                    c["reading"] = render(rd, merge_prefs(body.get("prefs")))
                return self.json_out(c)
            self.json_out({"error": f"no POST route {u.path}"}, 404)
        except ValueError as e:
            self.json_out({"error": str(e)}, 400)
        except Exception as e:                                  # noqa: BLE001
            sys.stderr.write(f"  error on {u.path}: {e!r}\n")
            self.json_out({"error": f"{type(e).__name__}: {e}", "route": u.path}, 500)

    def do_GET(self) -> None:              # noqa: N802
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                page = (APP / "index.html").read_text()
                return self._send(200, page.encode(), "text/html; charset=utf-8")
            if u.path in STATIC:
                name, ctype = STATIC[u.path]
                f = APP / name
                if not f.exists():
                    return self.json_out({"error": f"{name} is missing from app/"}, 500)
                body = f.read_bytes()
                # a service worker the browser caches once never sees a fix afterwards, and that is how a
                # phone stays on a three-week-old app forever - so the worker is always served fresh
                cache = "no-store" if u.path.endswith("sw.js") else "no-cache"
                self._cache_ctl = cache
                return self._send(200, body, ctype)
            if u.path == "/api/chart16" or u.path == "/api/positions":
                moms = [m.strip() for m in (q.get("mothers") or "").split(",") if m.strip()]
                if len(moms) != 4:
                    return self.json_out({"error": "give four mothers"}, 400)
                return self.json_out(chart16(moms, (q.get("topic") or "").strip() or None))
            if u.path == "/api/prove":
                moms = [m.strip() for m in (q.get("mothers") or "").split(",") if m.strip()]
                if len(moms) != 4:
                    return self.json_out({"error": "give four mothers"}, 400)
                return self.json_out(prove(moms, (q.get("topic") or "").strip() or None))
            if u.path == "/api/copy":
                moms = [m.strip() for m in (q.get("mothers") or "").split(",") if m.strip()]
                if len(moms) != 4:
                    return self.json_out({"error": "give four mothers"}, 400)
                return self._send(200, copy_text(moms, (q.get("topic") or "").strip() or None).encode(),
                                  "text/plain; charset=utf-8")
            if u.path == "/api/health":
                man = manifest()
                return self.json_out({"ok": True, "dataset": man.get("dataset"), "version": repo_version(),
                                      "passages": (man.get("counts") or {}).get("passages"),
                                      "voices": len(voices()), "coverage_score": coverage().get("score_of_100"),
                                      "preferences_file": str(PREFS.relative_to(ROOT))})
            if u.path == "/api/figures":
                import yaml
                figs = yaml.safe_load((KB / "figures.yaml").read_text())["figures"]
                return self.json_out({k: {"points": v.get("points"), "pattern": v.get("pattern"),
                                          "element": v.get("element"), "planet": v.get("planet"),
                                          "quality": v.get("quality"), "motion": v.get("motion")}
                                      for k, v in sorted(figs.items())})
            if u.path == "/api/topics":
                prefs = preferences()
                pinned = {t.lower() for t in prefs.get("topics_pinned") or []}
                rows = [{"outcome": r["outcome"], "label": r.get("label"), "house": r.get("quesited_roman"),
                         "n_voices": r.get("n_voices"), "n_works": r.get("n_works"),
                         "n_disagreements": r.get("n_disagreements"), "note": r.get("coverage_note"),
                         "pinned": r["outcome"].lower() in pinned} for r in outcomes()]
                rows.sort(key=lambda r: (not r["pinned"], r["outcome"]))
                return self.json_out(rows)
            if u.path == "/api/cast":
                moms = [m.strip() for m in (q.get("mothers") or "").split(",") if m.strip()]
                if len(moms) != 4:
                    return self.json_out({"error": "give four mothers, e.g. ?mothers=Via,Populus,Acquisitio,Amissio"}, 400)
                return self.json_out(chart(moms))
            if u.path == "/api/reading":
                moms = [m.strip() for m in (q.get("mothers") or "").split(",") if m.strip()]
                if len(moms) != 4:
                    return self.json_out({"error": "give four mothers"}, 400)
                from engine import ground as G
                c = chart(moms)
                rd = G.assemble({"houses": {int(k): v for k, v in c["houses"].items()}, **c["court"]},
                                (q.get("topic") or "").strip() or None, G.VoiceBook())
                rd["audit"] = G.validate(rd, G.VoiceBook())
                view = render(rd, merge_prefs(json.loads(q["prefs"]) if q.get("prefs") else None))
                view["chart"] = c
                view["shield"] = [rd["chart"].get(str(i)) for i in range(1, 13)]
                return self.json_out(view)
            if u.path == "/api/voices":
                rows = voices()
                fig, house, fam = q.get("figure"), q.get("house"), q.get("family")
                limit = int(q.get("limit") or 40)
                def keep(v: dict) -> bool:
                    if fig and v.get("figure") != fig:
                        return False
                    if house and str(v.get("house")) != str(house):
                        return False
                    if fam and v.get("family") != fam:
                        return False
                    return True
                sel = [r for r in rows if keep(r)]
                return self.json_out({"matched": len(sel), "returned": sel[:limit],
                                      "families": sorted({r["family"] for r in rows})})
            if u.path == "/api/coverage":
                return self.json_out(coverage())
            if u.path == "/api/how":
                return self.json_out(how())
            if u.path == "/api/preferences":
                return self.json_out(preferences())
            self.json_out({"error": f"no route {u.path}"}, 404)
        except Exception as e:                                  # noqa: BLE001
            # a stack trace in a browser is how a prototype stays a prototype: answer JSON, log here
            sys.stderr.write(f"  error on {u.path}: {e!r}\n")
            self.json_out({"error": f"{type(e).__name__}: {e}", "route": u.path}, 500)


def main() -> int:
    ap = argparse.ArgumentParser(description="local reader app over the geomancy library")
    ap.add_argument("--port", type=int, default=8044)
    ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()
    print(f"geomancy reader on http://127.0.0.1:{a.port}  "
          f"({len(voices())} voices, {len(outcomes())} outcomes, coverage "
          f"{coverage().get('score_of_100')}/100)")
    print(f"  preferences: {PREFS.relative_to(ROOT)} (edit and reload; it changes presentation, never content)")
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
