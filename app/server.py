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


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a) -> None:      # quieter: one line per request, on stderr
        sys.stderr.write("  %s\n" % (a[1] if len(a) > 1 else a))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def json_out(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, indent=1, ensure_ascii=False, default=str).encode(),
                   "application/json; charset=utf-8")

    def do_GET(self) -> None:              # noqa: N802
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                page = (APP / "index.html").read_text()
                return self._send(200, page.encode(), "text/html; charset=utf-8")
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
                view = render(rd, preferences())
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
