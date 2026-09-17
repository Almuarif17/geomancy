#!/usr/bin/env python3
"""Build kb/voices.jsonl: every attested statement in the corpus as an *attributed voice*.

The unit is not "the meaning of Carcer". It is:

    Christophe Cattan, 1608, book III, f.41: "…"  -- and --
    the Libro de los juysios de calatarama, f.50, tr. Finan 2023: "…"

which is the only shape of geomancy knowledge an app or a language model can be held accountable to.
A `key` is the claim being made about (a figure in a house, a judge with a cofigure, a look a cast has);
several works speak to the same key, and they do not always agree, so rows carry `polarity` and the
assembler in engine/ground.py surfaces disagreement instead of averaging it away.

Licence rule, enforced here and checked by library/tools/check_grounding.py: quote text ships only for a
work whose registry disposition is `full` (a public-domain text we hold). Everything else carries a
locator and cite_only=true, with the text left out of the repo entirely. Cite-only is a decision, not a gap.

Polarity is OUR lexical heuristic, never the author's word, and is labelled as such in every row. The
word lists below are deliberately coarse: a false lean is visible and arguable, a hidden judgement is not.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
KB, REG = ROOT / "kb", ROOT / "registry"

# Display attribution. `authority` is who wrote it, `through` is whose edition/translation/OCR we used.
AUTHORITY = {
    "calatarama_thesis": {"authority": "Libro de los juysios de calatarama (Castilian, 13th-c. redaction)",
                          "through": "C. Finan, The Book of the Judgements of Calatarama, 2023, App. 1",
                          "year": 1300, "work": "calatarama"},
    "lataille_geomancie": {"authority": "Jean de la Taille, La Géomancie (1577)",
                           "through": "public-domain scan; my transcription of the French",
                           "year": 1577, "work": "lataille"},
    "cattan_1591": {"authority": "Christophe de Cattan, The Geomancie (1591)",
                    "through": "Internet Archive b30337860, EEBO-style transcription",
                    "year": 1591, "work": "cattan1591"},
    "cattan_1608": {"authority": "Christophe de Cattan, The Geomancie and Opuscule (1608)",
                    "through": "Internet Archive; my own OCR pass",
                    "year": 1608, "work": "cattan1608"},
    "fasciculus_1704": {"authority": "Alfagini, Quaestiones Geomanticae (in Fasciculus geomanticus, 1704)",
                        "through": "Internet Archive b3299753x; my tesseract pass (lat+eng)",
                        "year": 1704, "work": "fasciculus"},
    "hartmann_1889": {"authority": "Hartmann of Solingen, Geomantia, table of answers (1633 print, 1889 ed.)",
                      "through": "Internet Archive b24884145; my OCR of the appendix columns",
                      "year": 1633, "work": "hartmann"},
    "agrippa_ii_1655": {"authority": "Cornelius Agrippa, De occulta philosophia II.31-32 (1553, tr. 1655)",
                        "through": "Internet Archive b20458563", "year": 1553, "work": "agrippa"},
}

POSITIVE = ("profit", "gaine", "gain", "joy", "health", "good", "obtain", "succeed", "success", "riches",
            "honour", "peace", "friend", "comfort", "escape", "acquiring", "acquire", "recover", "live",
            "long life", "happy", "increase", "speedy", "won", "win", "fulfilled", "fulfil", "marri")
NEGATIVE = ("loss", "lose", "death", "die", "dead", "fear", "pain", "sick", "prison", "barren", "poverty",
            "theft", "robbery", "anxiety", "enmit", "enemy", "quarrel", "break", "corrupt", "foolish",
            "separat", "removal", "boredom", "no ", "not ", "without", "nought", "hindrance", "delay",
            "sorrow", "shame", "wound", "betray", "despair", "difficulty",
            # French (la Taille) and Latin (Alfagini, Hartmann's table) are not English text; a lexicon
            # that only knows English silently reports "neutral" and looks like agreement between sources.
            "perte", "mort", "maladie", "peur", "douleur", "prison", "sterile", "vol", "triste", "nuisible",
            "mauvais", "retard", "empesch", "sans effect", "perteuse",
            "mortis", "dolor", "eamus", "non", "negatur", "impedit", "furta", "carcer", "egritudine",
            "malum", "tristia", "damnum", "amittit")


def polarity_of(text: str) -> dict:
    low = " " + (text or "").lower() + " "
    pos = sum(low.count(w) for w in POSITIVE)
    neg = sum(low.count(w) for w in NEGATIVE)
    lean = "positive" if pos > neg else "negative" if neg > pos else "mixed" if pos or neg else "neutral"
    return {"polarity": lean,
            "polarity_basis": "lexical heuristic over en/fr/la markers, by this library, NOT the author's word",
            "polarity_hits": {"pos": pos, "neg": neg}}


ROMAN = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7,"VIII":8,"IX":9,"X":10,"XI":11,"XII":12}


def house_of(value) -> int | None:
    """Houses arrive as Roman numerals (Calatarama, Hartmann prose) and as Arabic (la Taille, Cattan).
    A key that does not normalise them makes the same claim look like two unrelated claims, which is
    how a disagreement between two sources becomes invisible to the assembler."""
    if value is None:
        return None
    v = str(value).strip().upper()
    if v.isdigit():
        return int(v)
    return ROMAN.get(v)


def load(p: pathlib.Path):
    return json.loads(p.read_text())


def registry() -> dict:
    out = {}
    for line in (REG / "works.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        out[r["id"]] = r
    return out


def main() -> int:
    reg = registry()
    rows: list[dict] = []
    skipped_no_registration = set()

    def add(**kw):
        work = kw.pop("work_id")
        meta = AUTHORITY.get(work)
        if meta is None:
            skipped_no_registration.add(work)
            return
        regrow = reg.get(work, {})
        shippable = regrow.get("disposition") == "full"
        quote = kw.pop("quote", None)
        row = {
            "id": None,
            "authority": meta["authority"],
            "through": meta["through"],
            "year": meta["year"],
            "work": meta["work"],
            "work_id": work,
            "licence": regrow.get("licence_bucket"),
            "disposition": regrow.get("disposition"),
            "cite_only": not shippable,
            "quote": quote if shippable else None,
            "quote_withheld_reason": None if shippable else "disposition is not `full`; text stays out of git",
            "locator": kw.pop("locator", None),
            "confidence": kw.pop("confidence", "MED"),
            **kw,
        }
        src = row.get("quote") or row.get("gloss") or ""
        if src:
            row.update(polarity_of(src))
            # 16th-c. French with long-s, and OCR'd Latin, will under-hit an English lexicon. An
            # unscored row is absence of measurement, not neutrality, and must not become "agreement".
            row["polarity_reliability"] = ("low" if row["work_id"] in
                                          ("lataille_geomancie", "fasciculus_1704", "hartmann_1889") else "medium")
        rows.append(row)

    # 1. figure in a house, from the universal tables (the strongest layer we have)
    grid = load(KB / "calatarama_grid.json")["grid"]
    for house, block in grid.items():
        for figure, text in block["entries"].items():
            add(family="figure_in_house", key=f"figure_in_house:{figure}:{house_of(house)}", figure=figure,
                house=house_of(house), house_src=house, quote=text, work_id="calatarama_thesis",
                locator=f"f.{block.get('folio','?')} (house {house})", confidence="MED-HIGH")

    lt = load(KB / "lataille_grid.json")["grid"]
    for r in lt:
        add(family="figure_in_house", key=f"figure_in_house:{r['figure']}:{house_of(r['house'])}",
            figure=r["figure"], house=house_of(r["house"]), house_src=r["house"], quote=r["ruling_fr"],
            work_id="lataille_geomancie",
            locator=f"maison {r['house']}", confidence="MED")

    for fn, wid, loc in (("cattan1591_dangers.json", "cattan_1591", "page {page}"),
                         ):
        d = load(KB / fn)
        for r in d["records"]:
            add(family="figure_in_house", key=f"figure_in_house:{r.get('figure')}:{house_of(r.get('house'))}",
                figure=r.get("figure"), house=house_of(r.get("house")), house_src=r.get("house"),
                topic=r.get("topic"),
                quote=r.get("raw"), work_id=wid, locator=loc.format(**r), confidence=r.get("confidence", "MED"))

    # 2. motion between houses - Cattan's "the figure goes from I to VII", i.e. what moves and where
    for r in load(KB / "cattan_motus_bank.json")["records"]:
        add(family="motion_between_houses",
            key=f"motion:{r['figure']}:{house_of(r['from_house'])}->{house_of(r['to_house'])}",
            figure=r["figure"], from_house=house_of(r["from_house"]), to_house=house_of(r["to_house"]), quote=r.get("ocr_text"),
            work_id="cattan_1608", locator=f"motus bank, {r['figure']} {r['from_house']}->{r['to_house']}",
            confidence="MED (OCR)")

    # 3. judge + cofigure -> the answer, Hartmann's universal table (the closest thing to a lookup oracle)
    hc = load(KB / "hartmann_casebook.json")
    for r in hc.get("answers", []):
        add(family="judge_and_cofigure",
            key=f"judge_cofigure:{r['judge']}+{r['cofigure']}:q{r['q']}", figure=r["judge"],
            cofigure=r["cofigure"], judge=r["judge"], question_no=r["q"], question=r["question"],
            quote=r.get("answer"), work_id="hartmann_1889",
            locator=f"appendix table: judge {r['judge']}, cofigure {r['cofigure']}, q{r['q']}",
            confidence="MED (OCR of 1889 edition, column breaks unverified)")

    # 4. the qualities a cast 'looks' like: attributes and correspondences, per figure
    figs = load(KB / "figures.yaml") if False else None
    import yaml
    fy = yaml.safe_load((KB / "figures.yaml").read_text())
    for name, d in fy["figures"].items():
        for field in ("element", "planet", "quality", "motion", "gender", "nature", "engendering",
                      "time_unit", "points"):
            val = d.get(field)
            if val is None:
                continue
            add(family="figure_attribute", key=f"figure_attribute:{name}:{field}", figure=name,
                attribute=field, value=val,
                gloss=f"{name}: {field} = {val}", work_id="calatarama_thesis",
                locator=f"figures.yaml[{name}].{field} (table {6 if field=='planet' else 2}-6 of the thesis)",
                confidence="MED-HIGH" if field != "planet" else "LOW (contested, see attribution conflicts)")
        for field, val in (d.get("cal_details") or {}).items():
            if val:
                add(family="correspondence", key=f"correspondence:{name}:{field}", figure=name,
                    attribute=field, value=val, quote=val, work_id="calatarama_thesis",
                    locator=f"Calatarama details for {name}", confidence="MED-HIGH")
    # explicit, structured disagreement - published as conflict, never averaged
    # explicit, structured disagreement - published as a conflict, never averaged into a "consensus"
    for cid, block in (fy.get("planet_attribution_conflict") or {}).items():
        if not isinstance(block, dict):
            continue
        note = block.get("note", "")
        for k, v in block.items():
            if k == "note":
                continue
            # two orientations appear in the file: figure -> planet, and planet -> [figures]
            pairs = [(f, k) for f in v] if isinstance(v, list) else [(k, v)]
            for figure, planet in pairs:
                add(family="attribution_conflict", key=f"planet_attribution:{figure}", figure=figure,
                    attribute="planet", value=planet, tradition=cid,
                    gloss=f"{figure} = {planet} according to {cid}" + (f" ({note})" if note else ""),
                    conflict_with=[c2 for c2 in (fy.get("planet_attribution_conflict") or {}) if c2 != cid],
                    work_id="agrippa_ii_1655" if "agrippa" in cid else "calatarama_thesis",
                    locator=f"kb/figures.yaml:planet_attribution_conflict.{cid}",
                    confidence="LOW (documented conflict, not a fact)")
    nc = fy.get("naming_conflict") or {}
    if nc.get("pair"):
        for figure in nc["pair"]:
            add(family="naming_conflict", key=f"naming:{figure}", figure=figure,
                gloss=nc.get("note", ""), work_id="calatarama_thesis", locator="naming_conflict",
                confidence="LOW")

    # 5. question rules (Alfagini's quaestiones) - "if the figure of the first house is X, say Y"
    for it in load(KB / "alfagini_quaestiones.json")["items"]:
        body = (it.get("rule_latin") or "").replace("|", " ").strip()
        topic = (it.get("topic_latin") or "").strip()
        add(family="question_rule",
            key=f"quaestio:{(topic or body)[:36].lower().replace(' ', '_')}", topic=topic or None,
            gloss=None, quote=body[:600], work_id="fasciculus_1704",
            locator=f"leaf {it.get('leaf_pdf')}", confidence="MED (early Latin print, OCR)")

    # 6. look-rules: the executable techniques, each with its own citation
    tech = yaml.safe_load((KB / "techniques.yaml").read_text())["techniques"]
    for name, d in tech.items():
        src = d.get("source") or ""
        add(family="look_rule", key=f"technique:{name}", technique=name, answers=d.get("answers"),
            status=d.get("conf") or d.get("status"), gloss=src[:300],
            work_id="calatarama_thesis", locator=f"kb/techniques.yaml:{name}",
            confidence=d.get("conf", "MED"))

    # stable ids: family + key + work, so a citation survives a rebuild
    seen: dict[str, int] = {}
    for r in rows:
        base = f"{r['key']}:{r['work']}"   # the key already carries the family; ids are citations, keep them readable
        seen[base] = seen.get(base, 0) + 1
        r["id"] = base if seen[base] == 1 else f"{base}#{seen[base]}"
    rows.sort(key=lambda r: (r["family"], r["key"], r["work"]))

    out = KB / "voices.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")

    from collections import Counter
    fam = Counter(r["family"] for r in rows)
    multi = Counter(r["key"] for r in rows)
    print(f"wrote {out.name}: {len(rows)} voices")
    for k, v in fam.most_common():
        print(f"    {k:24s} {v:>4}")
    print(f"  keys spoken to by >1 work: {sum(1 for k, n in multi.items() if n > 1)}")
    print(f"  rows carrying quote text:  {sum(1 for r in rows if r.get('quote'))}")
    print(f"  rows cite-only (no text):  {sum(1 for r in rows if r.get('cite_only'))}")
    if skipped_no_registration:
        print(f"  WORKS NOT IN AUTHORITY MAP, ROWS DROPPED: {sorted(skipped_no_registration)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
