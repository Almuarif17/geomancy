# `server/mcp_geomancy.py` — the library as an agent tool

One file, no dependencies, standard library only. It speaks MCP over stdio, which is what Claude Desktop,
Cursor, Codex-style CLIs and OpenAI agent SDKs connect to without an adapter.

```bash
python3 server/mcp_geomancy.py --self-test       # protocol surface: 17 assertions
python3 server/mcp_geomancy.py --transport-test  # a real subprocess session over real pipes
python3 server/mcp_geomancy.py                   # now a server; JSON-RPC lines on stdin
```

Client config (`mcpServers`, same shape for Claude Desktop / Cursor / Continue):

```json
{ "mcpServers": { "geomancy": { "command": "python3", "args": ["server/mcp_geomancy.py"] } } }
```

A session, with the responses abbreviated to what matters:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"cast_from_mothers","inputSchema":…}, …6 tools…]}}

{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"grounded_reading",
  "arguments":{"mothers":["Via","Populus","Acquisitio","Amissio"],"topic":"marriage"}}}
{"jsonrpc":"2.0","id":2,"result":{"isError":false,"structuredContent":{
  "claims":[{"type":"sourced_ruling","text":"…","mode":"quote",
             "cites":{"voice_ids":["figure_in_house:Acquisitio:7:calatarama"],"works":["calatarama"]}}],
  "gaps":{"no_source_ruling":1,"contested":0},
  "audit":{"ok":true,"claims":39,"cited":33,"problems":[]},
  "citations":{"figure_in_house:Acquisitio:7:calatarama":
      {"authority":"…","locator":"24v-25 (thesis Table 8)","licence":"…"}}}}
```

## The six tools

| tool | what an app does with it |
|---|---|
| `cast_from_mothers` | compute the chart: 12 houses, daughters, nieces, witnesses, Judge, Sentence — arithmetic, not a lookup |
| `grounded_reading` | a reading where every claim names the work and folio it came from, and the audit says which claims could not be sourced |
| `voices_for` | the raw witnesses on one claim: quote or gloss, authority, edition, polarity, licence, `cite_only` |
| `score_answer` | grade *another* model's prose: grounding rate, uncited assertions, invented citation ids, off-cast figures, certainty language |
| `grounding_pack` | everything one LLM call needs at once: instructions, chart, relevant voices, the output schema |
| `coverage` | how much of the corpus exists, with denominators — so "comprehensive" is checkable |

Three resources publish the licence terms, the CC0 facts and the coverage file to the agent itself, because a
model that quotes the corpus should also know it is CC BY-NC.

## Deliberate limits

Read-only: no cast is stored, nothing is written, no network. `notifications/*` are accepted and ignored, and
unimplemented methods return `-32601` instead of pretending — a server that answers nothing for a capability
it never declared is the kind of integration that wastes a week of someone's evaluation. Sampling and
`prompts` are not implemented because a model that asks this server to think for it would defeat the point of
a library whose product is *attributed* text.
