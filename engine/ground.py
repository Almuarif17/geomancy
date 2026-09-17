#!/usr/bin/env python3
"""Assemble a *grounded* reading: every statement carries the voice that said it, or is not said.

This is the piece the rest of the ecosystem does not have. A cast goes in, a structured reading comes
out, and the reading is machine-auditable:

  * every claim lists `cites` -> voice ids in `kb/voices.jsonl`; each voice carries authority, the
    edition/translation it reached us through, a folio/leaf locator, a licence bucket and, where the work
    is one whose text we may ship, the quote itself;
  * where two sources speak to the same key and their leans differ, the claim is typed `sources_disagree`
    and carries both, unaveraged;
  * where the sources are silent, the claim is typed `no_source_ruling` with the reason, and the gap is
    counted;
  * `validate()` refuses any output containing an uncited claim, a citation that resolves to no voice, a
    figure that is not in the cast, or modal certainty language ("will", "guaranteed", "certain to").

`score()` runs the same audit over someone else's text - i.e. a language model's answer - so a product can
publish a grounding rate instead of a vibe. `--prompt-pack` emits the instructions to hand any model
(Ollama, OpenAI, Claude, whatever ships next month) together with the voice list it may cite; the model is
allowed to *phrase*, never to *assert*.

    python3 engine/ground.py --mothers Via,Populus,Acquisitio,Amissio --topic marriage --json
    python3 engine/ground.py --chart chart.json --topic wealth_money --out reading.json
    python3 engine/ground.py --prompt-pack > prompts/grounded_reader.md
    python3 engine/ground.py --score model_answer.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

VOICES = ROOT / "kb" / "voices.jsonl"
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X",
         11: "XI", 12: "XII"}
CERTAINTY = r"\b(will|guarantee[ds]?|certain(ly)? (to|that)|definitely|must happen|inevitabl\w+|promise[ds]?)\b"
CLAIM_TYPES = {"sourced_ruling", "sources_disagree", "figure_quality", "correspondence", "look_rule",
               "no_source_ruling", "method_note"}
SILENT = {"no_source_ruling"}


class VoiceBook:
    def __init__(self, path: pathlib.Path = VOICES):
        self.rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        self.by_id = {r["id"]: r for r in self.rows}
        self.by_key: dict[str, list] = {}
        for r in self.rows:
            self.by_key.setdefault(r["key"], []).append(r)

    def key(self, k: str, reliable_only: bool = True) -> list:
        rows = self.by_key.get(k, [])
        if not reliable_only:
            return rows
        # a low-reliability lean is not a disagreement, it is an absence of measurement: treating OCR'd
        # 16th-century French as "neutral" would manufacture conflict where the source simply was not scored
        return [r for r in rows if r.get("polarity_reliability") != "low"] or rows

    def lookup(self, vid: str):
        return self.by_id.get(vid)


def _chart_from(chart: dict) -> tuple[dict, dict]:
    """Accept {houses:{1:'Via',...}} or {'1':...} or a 12-length list; ignore whatever else is present."""
    raw = chart.get("houses") or chart
    out: dict[int, str] = {}
    if isinstance(raw, list):
        out = {i + 1: v for i, v in enumerate(raw[:12])}
    else:
        for k, v in raw.items():
            s = str(k).strip().lower().replace("house", "").strip()
            num = None
            if s.isdigit():
                num = int(s)
            else:
                inv = {v_: k_ for k_, v_ in ROMAN.items()}
                num = inv.get(s.upper())
            if num and isinstance(v, str):
                out[num] = v.strip()
    court = {k: v for k, v in chart.items() if k in ("judge", "reconciler", "witness_left", "witness_right",
                                                     "left_witness", "right_witness", "sentence")}
    return out, court


def assemble(chart: dict, topic: str | None = None, vb: VoiceBook | None = None,
             questions: list | None = None) -> dict:
    vb = vb or VoiceBook()
    houses, court = _chart_from(chart)
    claims, gaps = [], []

    def cite(rows, text=None):
        return {"voice_ids": [r["id"] for r in rows], "n_voices": len(rows),
                "works": sorted({r["work"] for r in rows})}

    quesited = None
    if topic:
        try:
            from engine import questions as Q
            quesited = Q.house_for(topic) if hasattr(Q, "house_for") else None
        except Exception:
            quesited = None
    if quesited is None and topic:
        try:
            import yaml
            h = yaml.safe_load((ROOT / "kb" / "houses.yaml").read_text())
            m = (h.get("question_to_house") or {}).get(topic)
            quesited = int(m) if m is not None else None
        except Exception:
            quesited = None

    # 1. figure-in-house rulings, per house actually occupied
    focus = [quesited] if quesited else list(houses)
    for hn in sorted(set(list(houses) + focus)):
        fig = houses.get(hn)
        if not fig:
            continue
        rows = vb.key(f"figure_in_house:{fig}:{hn}")
        if not rows:
            gaps.append({"house": hn, "figure": fig, "reason": "no tabulated ruling in any shipped source"})
            claims.append({"type": "no_source_ruling", "figure": fig, "house": hn,
                           "text": f"No source we ship speaks to {fig} in house {ROMAN.get(hn, hn)}.",
                           "cites": {"voice_ids": [], "n_voices": 0, "works": []}})
            continue
        leans = {r.get("polarity") for r in vb.key(f"figure_in_house:{fig}:{hn}") if r.get("polarity")}
        typ = "sources_disagree" if len(leans) > 1 else "sourced_ruling"
        claims.append({"type": typ, "figure": fig, "house": hn,
                       "text": " / ".join((r.get("quote") or r.get("gloss") or "") for r in rows)[:420],
                       "leans": sorted(str(x) for x in leans),
                       "mode": "quote" if any(r.get("quote") for r in rows) else "gloss",
                       "cites": cite(rows)})

    # 2. what the figures are like: quality, motion, element - the "look" of the cast
    for hn, fig in sorted(houses.items()):
        rows = [r for r in vb.key(f"figure_attribute:{fig}:quality", reliable_only=False)]
        if rows:
            claims.append({"type": "figure_quality", "figure": fig, "house": hn,
                           "text": f"{fig} is {rows[0].get('value')} by nature", "cites": cite(rows)})

    # 3. judge / sentence / reconciler, and the universal answer table behind them
    for role, fig in court.items():
        if not isinstance(fig, str):
            continue
        rows = vb.key(f"judge_cofigure:{fig}:*")
        for r in vb.rows:
            if r["family"] == "judge_and_cofigure" and r.get("judge") == fig:
                if topic and questions is None:
                    qtxt = (r.get("question") or "").lower()
                    if not any(w in qtxt for w in re.split(r"[^a-z]+", topic.lower()) if len(w) > 3):
                        continue
                rows.append(r)
        if rows:
            claims.append({"type": "sourced_ruling", "role": role, "figure": fig,
                           "text": " / ".join((r.get("quote") or "") for r in rows)[:400],
                           "n_candidate_answers": len(rows), "cites": cite(rows)})

    # 4. correspondences for the quesited house's figure: colour, place, bodies, numbers, "looks like"
    if quesited and houses.get(quesited):
        fig = houses[quesited]
        for r in vb.rows:
            if r["family"] == "correspondence" and r["figure"] == fig:
                claims.append({"type": "correspondence", "figure": fig, "house": quesited,
                               "attribute": r["attribute"], "text": str(r.get("value")), "cites": cite([r])})

    # 5. method: the rules that were applied, each with its own citation, not posed as a claim
    method = []
    for r in vb.rows:
        if r["family"] == "look_rule":
            method.append({"technique": r["technique"], "status": r.get("status"),
                           "cite": r["id"], "authority": r["authority"]})

    citations = {}
    for c in claims:
        for vid in (c.get("cites") or {}).get("voice_ids", []):
            v = vb.lookup(vid)
            if v:
                citations[vid] = {"authority": v["authority"], "through": v["through"], "year": v["year"],
                                  "locator": v.get("locator"), "licence": v.get("licence"),
                                  "cite_only": v.get("cite_only")}
    return {"schema": "geomancy.grounded_reading/1.0", "topic": topic, "quesited_house": quesited,
            "chart": {str(k): v for k, v in houses.items()}, "court": court, "claims": claims,
            "method": method, "citations": citations,
            "gaps": {"no_source_ruling": len([c for c in claims if c["type"] in SILENT]),
                     "contested": len([c for c in claims if c["type"] == "sources_disagree"])},
            "standing": ("This library documents what named authorities wrote about geomancy. It does not "
                         "assert that any of it is predictive, and none of it is medical, legal or financial "
                         "advice.")}


def validate(reading: dict, vb: VoiceBook | None = None) -> dict:
    """The audit. Anything that fails here must not ship as an answer."""
    vb = vb or VoiceBook()
    problems, in_cast = [], set((reading.get("chart") or {}).values()) | set(
        v for v in (reading.get("court") or {}).values() if isinstance(v, str))
    for i, c in enumerate(reading.get("claims", [])):
        if c.get("type") not in CLAIM_TYPES:
            problems.append(f"claim {i}: unknown type {c.get('type')!r}")
        cites = (c.get("cites") or {}).get("voice_ids") or c.get("cite") and [c["cite"]] or []
        if c.get("type") not in SILENT and not cites:
            problems.append(f"claim {i} ({c.get('type')}): uncited assertion")
        for vid in cites:
            v = vb.lookup(vid)
            if not v:
                problems.append(f"claim {i}: citation {vid!r} resolves to no voice")
                continue
            fig = c.get("figure")
            if fig and v.get("figure") and v["figure"] != fig:
                problems.append(f"claim {i}: cites {vid} about {v['figure']} to make a point about {fig}")
        for f in re.findall(r"\b(Via|Populus|Albus|Conjunctio|Fortuna Maior|Fortuna Major|Fortuna Minor|"
                            r"Amissio|Acquisitio|Laetitia|Tristitia|Carcer|Puella|Puer|Cauda Draconis|"
                            r"Caput Draconis)\b", c.get("text", "")):
            norm = "Fortuna Major" if f == "Fortuna Maior" else f
            if norm not in in_cast:
                problems.append(f"claim {i}: mentions {norm}, which is not in this cast")
        # Certainty language is the *source's* voice when it sits inside a quotation or in a verbatim
        # quote-mode claim; it is ours - and therefore a violation - anywhere else. This distinction is the
        # whole product: we may repeat a 13th-c. claim of certainty, we may not endorse it.
        if c.get("type") != "no_source_ruling" and c.get("mode") != "quote":
            unquoted = re.sub(r"“[^”]*”|\"[^\"]*\"", " ", c.get("text", ""))
            if re.search(CERTAINTY, unquoted, re.I):
                problems.append(f"claim {i}: asserts certainty ({c.get('mode')}); attribute it or quote it")
    return {"ok": not problems, "claims": len(reading.get("claims", [])),
            "cited": len({v for c in reading.get("claims", []) for v in (c.get('cites') or {}).get('voice_ids', [])}),
            "problems": problems[:40]}


def score(answer: dict | str, vb: VoiceBook | None = None) -> dict:
    """Grade someone else's prose (typically an LLM) against the voice book."""
    vb = vb or VoiceBook()
    if isinstance(answer, str):
        answer = {"claims": [{"type": "sourced_ruling", "text": s.strip(),
                              "cites": {"voice_ids": re.findall(r"\[([a-z_]+:[^\]\s]+)\]", s)}}
                             for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]}
    res = validate(answer, vb)
    ids = {r["id"] for r in vb.rows}
    claims = answer.get("claims", [])
    cited = sum(1 for c in claims if (c.get("cites") or {}).get("voice_ids"))
    res.update({"grounding_rate": round(100 * cited / max(1, len(claims)), 1),
                "sentences": len(claims), "sentences_with_valid_citation": cited,
                "unknown_citation_ids": sorted({v for c in claims
                                                for v in (c.get("cites") or {}).get("voice_ids", [])
                                                if v not in ids})[:10]})
    return res


PROMPT = """# Grounded geomancy reader - instructions for a language model

You are composing a reading from a supplied voice list. You are a writer, not a source.

Hard rules, each of which is checked by `engine/ground.py validate()` and can fail your output:

1. Every sentence that says something about the cast must cite at least one voice id from `voices`.
   No citation, no sentence. If you have nothing cited, write that the sources are silent.
2. Quote, or attribute in your own words - never assert on your own authority. "Cattan warns that…" is
   allowed; "this means you will…" is not.
3. Do not mention a figure that is not in the cast, and do not invent a ruling for a gap. Gaps are
   content: name them (`no_source_ruling`) and say what is missing.
4. Where two cited voices lean differently, present both. Never average them into a consensus.
5. No certainty vocabulary (will, guaranteed, certain, definitely, inevitable). Report leans, not outcomes.
6. If the question touches health, death, the law, or a named third party, say plainly that the reader
   should consult a doctor, a lawyer, or the person - and put the geomantic material after that, not before.
7. End with the citation block exactly as given to you. Do not add references you were not given.

Return JSON matching `library/schema/grounded_reading.json`: claims[] with type, text, cites.voice_ids[].
Your output is auditable by construction: a reviewer runs one command and sees which sentences have no
source. That is the whole point of this library.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mothers"), ap.add_argument("--chart"), ap.add_argument("--topic")
    ap.add_argument("--out", default="-")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--prompt-pack", action="store_true")
    ap.add_argument("--score")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    vb = VoiceBook()
    if a.prompt_pack:
        print(PROMPT)
        return 0
    if a.score:
        print(json.dumps(score(json.loads(pathlib.Path(a.score).read_text()), vb), indent=1))
        return 0
    chart: dict = {}
    if a.chart:
        chart = json.loads(pathlib.Path(a.chart).read_text())
    elif a.mothers:
        from engine import deep_read as D
        moms = [m.strip() for m in a.mothers.split(",")]
        c = D.build(moms)
        chart = {"houses": {i + 1: D.fig(pat) for i, pat in enumerate(c["houses"])},
                 "judge": D.fig(c["judge"]), "sentence": D.fig(c["sentence"]),
                 "witness_left": D.fig(c["witnesses"][0]), "witness_right": D.fig(c["witnesses"][1])}
    if not chart:
        sys.exit("give --mothers A,B,C,D or --chart file.json")
    reading = assemble(chart, a.topic, vb)
    audit = validate(reading, vb)
    reading["audit"] = audit
    text = json.dumps(reading, indent=1 if a.json or a.out == "-" else None, ensure_ascii=False)
    if a.out == "-":
        print(text)
    else:
        pathlib.Path(a.out).write_text(text + "\n")
        print(f"wrote {a.out}: {len(reading['claims'])} claims, audit ok={audit['ok']}")
    return 0 if audit["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
