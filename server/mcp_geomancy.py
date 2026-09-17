#!/usr/bin/env python3
# ruff: noqa: E501
"""MCP server for the geomancy library - JSON-RPC 2.0 over stdio, no dependencies.

    python3 server/mcp_geomancy.py            # speak MCP on stdin/stdout
    python3 server/mcp_geomancy.py --self-test # one scripted session, no client needed

Why this file exists: the paid competitors in this niche already advertise an MCP endpoint, so an agent that
wants geomancy finds *them* first. The difference is not that we answer - it is what we hand back with the
answer. Every reading this server returns carries per-claim citations to a named work and folio, marks which
parts of the corpus are silent, and refuses to quote a source we may not quote. `score_answer` inverts the
usual relationship: rather than letting a model talk, the library grades the model's prose and reports the
sentences that have no source under them.

Transport notes, because they are the part people get wrong: MCP's stdio transport is newline-delimited JSON
(one message per line, no Content-Length framing), stdout is reserved for protocol traffic, so diagnostics go
to stderr. Requests are answered in order. Nothing here opens a socket, reads the network, or writes a file.

Protocol surface: initialize / ping / tools/list / tools/call / resources/list / resources/read. `initialized`
and other `notifications/*` messages are accepted and ignored. Sampling, prompts, roots and completion are
deliberately not implemented - answering `notifications/*` for an unknown capability is how servers look
healthy while every client feature silently fails, so unsupported methods get an explicit -32601 instead.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROTOCOL = "2024-11-05"
SERVER = {"name": "geomancy-library", "version": "0.2.5"}
KB = ROOT / "kb"
DS = ROOT / "library" / "dataset"

_ERR_PARSE, _ERR_METHOD, _ERR_PARAMS, _ERR_INTERNAL = -32700, -32601, -32602, -32603


def log(*a) -> None:
    print("[mcp]", *a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- lazily-built, read-only views
_state: dict = {}


def state() -> dict:
    if not _state:
        import yaml
        from engine import deep_read as D
        from engine import ground as G

        # the canonical name set is the library's own figure table, not whatever the engine happens to
        # expose - deep_read has no NAMES attribute, and a server that validates against a guess accepts
        # typos and rejects real figures
        figures = sorted(yaml.safe_load((KB / "figures.yaml").read_text())["figures"])
        _state.update({"D": D, "G": G, "vb": G.VoiceBook(), "figures": figures,
                       "voices": [json.loads(l) for l in (KB / "voices.jsonl").read_text().splitlines()
                                  if l.strip()]})
    return _state


def chart_of(mothers: list[str]) -> dict:
    """Four mothers in -> the full figure assignment, by computation, never by lookup table."""
    st = state()
    D = st["D"]
    bad = [m for m in mothers if m not in st["figures"]]
    if bad or len(mothers) != 4:
        raise ValueError(f"mothers must be exactly 4 known figures; got {mothers!r}"
                         + (f" (unknown: {bad})" if bad else "")
                         + f"; valid names: {', '.join(st['figures'])}")
    c = D.build(list(mothers))
    # c["houses"] is the whole 16-figure shield in generative order: mothers I-IV, daughters V-VIII,
    # nieces IX-XII, then the two witnesses, the Judge and the Sentence. Only the first twelve are houses;
    # numbering the court as houses XIII-XVI is the error this function had, and it silently feeds a reader
    # a "figure in house XV" ruling that no source contains.
    shield = [D.fig(pat) for pat in c["houses"]]
    if len(shield) != 16:
        raise ValueError(f"deep_read.build returned {len(shield)} figures, expected the 16-figure shield")
    court = {"witness_left": D.fig(c["witnesses"][0]), "witness_right": D.fig(c["witnesses"][1]),
             "judge": D.fig(c["judge"]), "sentence": D.fig(c["sentence"])}
    chart = {"input": {"mothers": list(mothers)},
             "houses": {i + 1: shield[i] for i in range(12)},
             "mothers": shield[0:4],
             "daughters": dict(zip(["V", "VI", "VII", "VIII"], shield[4:8])),
             "nieces": dict(zip(["IX", "X", "XI", "XII"], shield[8:12])),
             **court, "reconciler": court["sentence"], "court": court, "shield": shield}
    if _args_flags["patterns"]:
        chart["shield_patterns"] = [list(map(int, pat)) for pat in c["houses"]]
    return chart


# include_patterns is a rendering option for t_cast; threading it through every caller's signature would
# mean four near-identical kwargs, so it rides on a one-entry module flag set only inside the cast tool.
_args_flags: dict = {"patterns": False}


class args_flags:
    def __init__(self, patterns: bool = False):
        self.prev = _args_flags["patterns"]
        self.patterns = bool(patterns)

    def __enter__(self):
        _args_flags["patterns"] = self.patterns
        return _args_flags

    def __exit__(self, *exc):
        _args_flags["patterns"] = self.prev
        return False


# ---------------------------------------------------------------- tools
def t_cast(args: dict) -> dict:
    with args_flags(args.get("include_patterns")):
        return chart_of(args.get("mothers") or [])


def t_reading(args: dict) -> dict:
    st = state()
    chart = chart_of(args.get("mothers") or [])
    topic = (args.get("topic") or "").strip() or None
    reading = st["G"].assemble(chart, topic, st["vb"])
    audit = st["G"].validate(reading, st["vb"])
    reading["audit"] = audit
    reading["standing"] = ("Documented claims from named authorities, with folio locators. Silent where the "
                           "sources are silent. Not a prediction, not advice.")
    if topic:
        reading["quesited"] = topic
    return reading


def t_score(args: dict) -> dict:
    st = state()
    answer = args.get("answer")
    if not isinstance(answer, (str, dict)) or not answer:
        raise ValueError("answer must be a non-empty string of prose or a claims object")
    res = st["G"].score(answer, st["vb"])
    res["verdict"] = ("grounded" if res.get("ok") and res.get("grounding_rate", 0) >= 80 else
                      "partially grounded" if res.get("grounding_rate", 0) >= 40 else "ungrounded")
    res["note"] = ("scored against kb/voices.jsonl; citations must be [work:key] ids that exist in that file, "
                   "and certainty language outside a quotation fails the audit")
    return res


def t_voices(args: dict) -> dict:
    st = state()
    fig, fam = args.get("figure"), args.get("family")
    house, key = args.get("house"), args.get("key")
    limit = max(1, min(int(args.get("limit") or 40), 500))
    topic = (args.get("topic") or "").strip().lower()

    def ok(v: dict) -> bool:
        if fig and v.get("figure") not in (fig, str(fig)):
            return False
        if fam and v.get("family") != fam:
            return False
        if house is not None and str(v.get("house")) not in {str(house)}:
            return False
        if key and key.lower() not in str(v.get("key", "")).lower():
            return False
        if topic and topic not in json.dumps(v, ensure_ascii=False).lower():
            return False
        return True

    rows = [v for v in st["voices"] if ok(v)]
    out = []
    for v in rows[:limit]:
        out.append({k: v[k] for k in ("id", "family", "key", "figure", "house", "attribute", "value",
                                      "quote", "gloss", "authority", "through", "locator", "work",
                                      "licence", "cite_only", "confidence", "polarity", "polarity_basis",
                                      "polarity_reliability") if k in v})
    return {"matched": len(rows), "returned": len(out), "limit": limit, "voices": out,
            "reading_rule": "quote is verbatim from the named work and licence-permitted; cite_only rows carry "
                            "a locator and no text on purpose; polarity_reliability low means the lean is "
                            "inferred from one language's vocabulary, not stated"}


def t_coverage(args: dict) -> dict:
    cov = json.loads((KB / "coverage.json").read_text())
    keep = {"schema", "score_of_100", "components", "ranked_moves", "reported_only", "reading_guide"}
    out = {k: v for k, v in cov.items() if k in keep}
    if not args.get("full"):
        out["components"] = {k: {x: y for x, y in c.items() if x != "note"}
                             for k, c in out["components"].items()}
    return out


def t_pack(args: dict) -> dict:
    """Everything an LLM needs to write a grounded reading, in one call."""
    st = state()
    chart = chart_of(args.get("mothers") or []) if args.get("mothers") else {}
    topic = (args.get("topic") or "").strip() or None
    voices = []
    if chart:
        for name, fig in chart["houses"].items():
            voices += [v for v in st["voices"]
                       if v.get("figure") == fig and (v.get("house") in {name, str(name), None})]
        voices += [v for v in st["voices"] if v.get("judge") == chart.get("judge")]
    seen, uniq = set(), []
    for v in voices:
        if v.get("id") not in seen:
            seen.add(v.get("id"))
            uniq.append(v)
    return {"instructions": st["G"].PROMPT, "chart": chart, "quesited": topic,
            "voices": uniq[:120], "n_voices": len(uniq),
            "output_schema": json.loads((ROOT / "library" / "schema" / "grounded_reading.json").read_text()),
            "licence_reminder": "curated text (quotes, glosses, rulings) is CC BY-NC 4.0; a revenue-bearing "
                                "product needs the commercial licence - see LICENSING.md"}


TOOLS = {
    "cast_from_mothers": {
        "description": "Build a full geomancy chart from four mothers: 12 houses, 4 daughters, two witnesses, "
                       "the Judge and the Sentence. Computed, never looked up.",
        "inputSchema": {"type": "object", "properties": {
            "mothers": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4,
                        "description": "four figure names, e.g. Via, Populus, Acquisitio, Amissio"},
            "include_patterns": {"type": "boolean", "description": "also return the raw dot patterns"}},
            "required": ["mothers"]}},
    "grounded_reading": {
        "description": "Assemble a source-attributed reading of a cast for a topic: every claim carries the "
                       "voice ids, work and folio it came from, and the audit reports uncited or off-cast claims.",
        "inputSchema": {"type": "object", "properties": {
            "mothers": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
            "topic": {"type": "string", "description": "the quesited matter, e.g. marriage, voyage, lawsuit"}},
            "required": ["mothers"]}},
    "score_answer": {
        "description": "Grade prose (usually another app's LLM output) against the voice index: grounding rate, "
                       "uncited assertions, invented citations, off-cast figures, certainty language.",
        "inputSchema": {"type": "object", "properties": {
            "answer": {"type": "string", "description": "prose; cite inline as [work:key]"},
            "mothers": {"type": "array", "items": {"type": "string"}},
            "topic": {"type": "string"}}, "required": ["answer"]}},
    "voices_for": {
        "description": "The attributed voices on a claim: rows from kb/voices.jsonl filtered by figure, house, "
                       "family or text, each with quote/gloss, authority, edition, locator, licence and polarity.",
        "inputSchema": {"type": "object", "properties": {
            "figure": {"type": "string"}, "house": {"type": ["integer", "string"]},
            "family": {"type": "string", "description": "e.g. figure_in_house, look_rule, judge_and_cofigure"},
            "key": {"type": "string"}, "topic": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 500}}}},
    "coverage": {
        "description": "How much of the corpus is actually in the library: the scoreboard, its denominators, "
                       "and the computed next moves. Published so nobody has to trust a boast.",
        "inputSchema": {"type": "object", "properties": {
            "full": {"type": "boolean", "description": "include per-work join notes"}}}},
    "grounding_pack": {
        "description": "One call that hands a language model everything needed to write a grounded reading: "
                       "the instructions, the cast, the relevant voices, and the output schema to satisfy.",
        "inputSchema": {"type": "object", "properties": {
            "mothers": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
            "topic": {"type": "string"}}, "required": ["mothers"]}},
}

RESOURCES = {
    "geomancy://licensing": (ROOT / "LICENSING.md", "text/markdown"),
    "geomancy://core_facts": (DS / "core_facts.json", "application/json"),
    "geomancy://coverage": (KB / "coverage.json", "application/json"),
    "geomancy://reading_contract": (ROOT / "library" / "schema" / "grounded_reading.json", "application/json"),
}


def call(name: str, args: dict) -> dict:
    fn = {"cast_from_mothers": t_cast, "grounded_reading": t_reading, "score_answer": t_score,
          "voices_for": t_voices, "coverage": t_coverage, "grounding_pack": t_pack}[name]
    return fn(args or {})


def handle(msg: dict) -> dict | None:
    """One JSON-RPC message in, one response out (None for notifications)."""
    mid = msg.get("id")
    method = msg.get("method")
    if msg.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": _ERR_PARSE, "message": "expected a JSON-RPC 2.0 request object"}}
    if method.startswith("notifications/"):
        return None
    params = msg.get("params") or {}
    try:
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": PROTOCOL, "serverInfo": SERVER,
                "capabilities": {"tools": {"listChanged": False}, "resources": {"subscribe": False,
                                                                                 "listChanged": False}},
                "instructions": ("Geomancy chart computation plus a source-attributed reading layer. Cited or "
                                 "silent, never invented. Curated text is CC BY-NC 4.0 - see geomancy://licensing.")}}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": mid, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "tools": [{"name": n, "description": t["description"], "inputSchema": t["inputSchema"],
                           "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True,
                                           "openWorldHint": False}} for n, t in sorted(TOOLS.items())]}}
        if method == "tools/call":
            name = params.get("name")
            if name not in TOOLS:
                return {"jsonrpc": "2.0", "id": mid,
                        "error": {"code": _ERR_PARAMS, "message": f"unknown tool {name!r}",
                                  "data": {"tools": sorted(TOOLS)}}}
            try:
                res = call(name, params.get("arguments") or {})
            except (ValueError, KeyError, TypeError) as e:
                # a tool that raises is a protocol error with a readable reason, not a crash: a client that
                # loses the connection learns nothing, and a client told "unknown figure Viaa" can fix itself
                return {"jsonrpc": "2.0", "id": mid, "result": {
                    "isError": True, "content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}]}}
            blob = json.dumps(res, indent=1, sort_keys=True, ensure_ascii=False, default=str)
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "isError": False, "content": [{"type": "text", "text": blob}], "structuredContent": res}}
        if method == "resources/list":
            return {"jsonrpc": "2.0", "id": mid, "result": {"resources": [
                {"uri": uri, "name": uri.rsplit("/", 1)[-1], "mimeType": mime,
                 "description": "published so an agent can read the licence and the gaps before it quotes us"}
                for uri, (_, mime) in sorted(RESOURCES.items())]}}
        if method == "resources/read":
            uri = params.get("uri")
            if uri not in RESOURCES:
                return {"jsonrpc": "2.0", "id": mid, "error": {"code": _ERR_PARAMS,
                                                                "message": f"unknown resource {uri!r}"}}
            path, mime = RESOURCES[uri]
            if not path.exists():
                return {"jsonrpc": "2.0", "id": mid, "result": {
                    "isError": True, "contents": [{"uri": uri, "text": f"missing in this checkout: {path.name}"}]}}
            return {"jsonrpc": "2.0", "id": mid, "result": {"contents": [
                {"uri": uri, "mimeType": mime, "text": path.read_text()}]}}
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": _ERR_METHOD, "message": f"method {method!r} is not implemented by this server",
                          "data": {"methods": ["initialize", "ping", "tools/list", "tools/call",
                                               "resources/list", "resources/read"]}}}
    except Exception as e:  # never die on a client's bad day, but never pretend either
        log(f"internal error on {method}: {e!r}")
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": _ERR_INTERNAL, "message": f"{type(e).__name__}: {e}"}}


def serve() -> int:
    log(f"{SERVER['name']} {SERVER['version']} on stdio, {len(TOOLS)} tools, {len(RESOURCES)} resources")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            out = {"jsonrpc": "2.0", "id": None,
                   "error": {"code": _ERR_PARSE, "message": f"invalid JSON: {e}"}}
            print(json.dumps(out), flush=True)
            continue
        resp = handle(msg) if isinstance(msg, dict) else None
        if resp is not None:
            print(json.dumps(resp, ensure_ascii=False), flush=True)
    return 0


def self_test() -> int:
    """A scripted session through the same code path a client uses - not a re-implementation of it."""
    moms = ["Via", "Populus", "Acquisitio", "Amissio"]
    reqs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "cast_from_mothers", "arguments": {"mothers": moms}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "grounded_reading", "arguments": {"mothers": moms, "topic": "marriage"}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "coverage", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
             "params": {"name": "voices_for", "arguments": {"figure": "Amissio", "limit": 5}}},
            {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
             "params": {"name": "score_answer", "arguments": {"answer": "The Judge shows loss. [cattan1608:VI]",
                                                               "mothers": moms}}},
            {"jsonrpc": "2.0", "id": 8, "method": "resources/read",
             "params": {"uri": "geomancy://licensing"}},
            {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
             "params": {"name": "cast_from_mothers", "arguments": {"mothers": ["Viaa", "x", "y", "z"]}}},
            {"jsonrpc": "2.0", "id": 10, "method": "completion/complete", "params": {}},
            {"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "grounding_pack",
                                                                            "arguments": {"mothers": moms,
                                                                                          "topic": "voyage"}}}]
    out = [handle(m) for m in reqs if (m.get("id") or True) and not m["method"].startswith("notifications/")]
    out = [o for o in out if o]
    checks = []

    def ck(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    by_id = {o["id"]: o for o in out}
    init = by_id[1]["result"]
    ck("initialize announces tools + resources", "tools" in init["capabilities"] and "resources" in init["capabilities"])
    ck("server is not claiming sampling/prompts", not ({"sampling", "prompts"} & set(init["capabilities"])))
    tools = [t["name"] for t in by_id[2]["result"]["tools"]]
    ck("all six tools listed", len(tools) == 6 and "grounded_reading" in tools, ",".join(tools))
    ck("every tool has an inputSchema", all("inputSchema" in t for t in by_id[2]["result"]["tools"]))
    chart = json.loads(by_id[3]["result"]["content"][0]["text"])
    ck("chart has exactly the 12 houses, no court masquerading as houses",
       sorted(int(k) for k in chart["houses"]) == list(range(1, 13)), str(sorted(chart["houses"])))
    ck("court is a fourth-of-shield object, judge + reconciler present",
       set(chart["court"]) == {"witness_left", "witness_right", "judge", "sentence"}
       and chart["reconciler"] == chart["court"]["sentence"])
    ck("shield order: mothers, then daughters V-VIII, then nieces IX-XII",
       chart["shield"][:4] == chart["mothers"] and list(chart["daughters"].values()) == chart["shield"][4:8]
       and list(chart["nieces"].values()) == chart["shield"][8:12] and chart["daughters"]["V"] == chart["houses"]["5"])
    ck("Judge is even-pointed, as the parity law requires over all 65,536 casts",
       chart["judge"] in ("Acquisitio", "Amissio", "Carcer", "Conjunctio", "Fortuna Major", "Fortuna Minor",
                          "Populus", "Via"), str(chart["judge"]))
    rd = json.loads(by_id[4]["result"]["content"][0]["text"])
    ck("reading audited clean", rd["audit"]["ok"], json.dumps(rd["audit"].get("problems", []))[:120])
    ck("every claim cites a voice", all((c.get("cites") or {}).get("voice_ids") or c["type"] == "no_source_ruling"
                                        for c in rd["claims"]), f"{len(rd['claims'])} claims")
    cov = json.loads(by_id[5]["result"]["content"][0]["text"])
    ck("coverage reports a score and denominators", 0 < cov["score_of_100"] <= 100
       and all("target" in c and "count" in c for c in cov["components"].values()))
    vs = json.loads(by_id[6]["result"]["content"][0]["text"])
    ck("voices_for returns locatable rows", vs["voices"] and all(v.get("locator") and v.get("work")
                                                                  for v in vs["voices"]))
    sc = json.loads(by_id[7]["result"]["content"][0]["text"])
    ck("score_answer grades prose", "grounding_rate" in sc and sc["sentences"] >= 1, f"rate={sc['grounding_rate']}")
    lic = by_id[8]["result"]["contents"][0]["text"]
    ck("licence resource readable", "CC BY-NC" in lic and "core_facts" in lic)
    ck("bad figure is a readable tool error, not a crash", by_id[9]["result"]["isError"]
       and "unknown:" in by_id[9]["result"]["content"][0]["text"], by_id[9]["result"]["content"][0]["text"][:90])
    ck("unimplemented method gets -32601", by_id[10]["error"]["code"] == _ERR_METHOD)
    pk = json.loads(by_id[11]["result"]["content"][0]["text"])
    ck("grounding_pack carries instructions + voices + schema", "cite" in pk["instructions"].lower()
       and pk["n_voices"] > 0 and pk["output_schema"].get("type") == "object")

    bad = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail and not ok else ""))
    print(f"\nself-test: {len(checks) - len(bad)}/{len(checks)} passed" if not bad else
          f"\nself-test: {len(bad)} of {len(checks)} checks FAILED")
    return 1 if bad else 0


def transport_test() -> int:
    """Drive the real process over real pipes: the framing bugs a client finds are never the ones you test."""
    import subprocess
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": PROTOCOL,
                                                                        "capabilities": {},
                                                                        "clientInfo": {"name": "pipes", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "voices_for",
                                                                       "arguments": {"family": "look_rule",
                                                                                     "limit": 3}}},
        "@@@ this line is deliberately not JSON @@@",
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "grounded_reading", "arguments": {"mothers": ["Via", "Via", "Via", "Via"],
                                                              "topic": "voyage"}}},
        {"jsonrpc": "2.0", "id": 5, "method": "resources/list", "params": {}},
    ]
    # each entry is either a dict (serialised) or a raw string (punched on the wire as-is), because the
    # malformed-message path can only be tested by sending a malformed message
    stdin = "\n".join(m if isinstance(m, str) else json.dumps(m) for m in msgs) + "\n"
    r = subprocess.run([sys.executable, str(pathlib.Path(__file__)), "--quiet"], input=stdin,
                       capture_output=True, text=True, cwd=ROOT, timeout=60)
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    ok = True

    def ck(cond, detail):
        nonlocal ok
        print(f"  [{'ok' if cond else 'FAIL'}] {detail}")
        ok = ok and bool(cond)

    ck(r.returncode == 0, f"process exited 0 (got {r.returncode}; stderr: {r.stderr.strip()[:120]})")
    # 6 messages in, 5 replies expected: initialize, voices_for, grounded_reading and resources/list are
    # requests; the notification gets nothing; the garbage line gets a parse error and no death
    ck(len(lines) == 5, f"5 replies for 6 messages (one notification, silence expected), got {len(lines)}")
    parsed = []
    for l in lines:
        try:
            parsed.append(json.loads(l))
        except Exception as e:
            ck(False, f"every stdout line is one JSON object: {e} on {l[:60]!r}")
    ck(len(parsed) == len(lines), "no stray prints on stdout")
    by = {p.get("id"): p for p in parsed}
    ck(by.get(1, {}).get("result", {}).get("serverInfo", {}).get("name") == "geomancy-library", "initialize result")
    ck("voices" in by.get(2, {}).get("result", {}).get("structuredContent", {}), "tools/call structuredContent")
    parse_err = [q for q in parsed if q.get("id") is None and q.get("error")]
    ck(len(parse_err) == 1 and parse_err[0]["error"]["code"] == _ERR_PARSE,
       f"garbage line -> -32700 parse error and the process stays alive (got {parse_err})")
    rd = by.get(4, {}).get("result", {}).get("structuredContent") or {}
    ck(rd.get("audit", {}).get("ok") is True, f"populated cast reads clean over the wire ({rd.get('audit')})")
    ck(all(v.get("locator") for v in rd.get("voices", []) if isinstance(v, dict)) or "voices" not in rd,
       "any voice row that travels the wire keeps its locator")
    ck(len(by.get(5, {}).get("result", {}).get("resources", [])) == len(RESOURCES), "resources/list count")
    print("\ntransport test: PASS" if ok else "\ntransport test: FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="MCP server for the geomancy library (stdio, JSON-RPC 2.0)")
    ap.add_argument("--self-test", action="store_true", help="run a scripted session and exit")
    ap.add_argument("--transport-test", action="store_true", help="drive this server as a subprocess over pipes")
    ap.add_argument("--quiet", action="store_true", help="suppress the stderr banner")
    args = ap.parse_args()
    if args.quiet:
        globals()["log"] = lambda *a, **k: None
    if args.self_test:
        state()
        return self_test()
    if args.transport_test:
        return transport_test()
    return serve()


if __name__ == "__main__":
    sys.exit(main())
