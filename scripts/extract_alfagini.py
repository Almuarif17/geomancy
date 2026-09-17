#!/usr/bin/env python3
"""'Alfagini Quaestiones Geomantici' (Fasciculus geomanticus, 1704) -> kb/alfagini_quaestiones.json

Uses the archive text layer (legible for these rules; a full re-OCR of 240 pages costs ~40 min for no
gain here) and captures each quaestio as: topic heading + the decision rule. Leaf numbers point at the
scan so anything doubtful can be checked.
"""
import pymupdf, re, json, pathlib

PDF = pathlib.Path("corpus/raw/ia/fasciculus_geomanticus_1704.pdf.pdf")
OUT = pathlib.Path("kb/alfagini_quaestiones.json")
d = pymupdf.open(str(PDF))
LO, HI = 440, 690

ROMAN = r"(?:PRIMA|SECUNDA|TERTIA|QUARTA|QUINTA|SEXTA|SEPTIMA|OCTAVA|NONA|DECIMA|V[Nn]DECIMA|DECIMA\s*[ET]?[Qq]?V[Nn]T[A-Z]*|VLTIMA|DECIM[A-Z]*|[IVXLCDM]{1,7})"
TOPIC = re.compile(r"((?:De|An|Utrum|Quomodo|Qualiter|Quantitas)\s+[A-Za-zà-ÿæœ'’\-\s,]{5,88}?)[.?!]?\s*$", re.I)

items = []
for i in range(LO, min(HI, d.page_count)):
    t = d[i].get_text()
    if "QUAESTIO" not in t.upper():
        continue
    lines = [l.strip() for l in t.split("\n")]
    joined = re.sub(r"\s+", " ", t).replace("QUASTIO", "QUAESTIO").replace("QVÆSTIO", "QUAESTIO")
    for m in re.finditer(r"QUAESTIO\W{0,3}" + ROMAN + r"\W{0,3}", joined):
        pre = joined[max(0, m.start() - 160):m.start()]
        tm = None
        for cand in reversed(re.findall(r"((?:De|An|Utrum|Quomodo|Qualiter|Quantitas)[^.]{5,90})", pre, re.I)):
            tm = cand.strip(" -—.,;:0123456789"); break
        body = joined[m.end():m.end() + 780]
        nxt = re.search(r"(?:QUAESTIO\W{0,3}" + ROMAN + r")|(?:De\s+[A-ZÀ-Ý][a-zà-ÿ]{3,}\s*$)", body, re.I)
        if nxt: body = body[:nxt.start()]
        body = body.strip(" -—.,;:")
        if len(body) < 60:
            continue
        items.append({"leaf_pdf": i + 1, "topic_latin": (tm or "").strip(),
                      "text_latin": re.sub(r"\s+", " ", body)[:780]})

# dedupe repeated extractions of the same rule (pages overlap in the layer)
best = {}
for it in items:
    k = re.sub(r"[^a-z]", "", it["topic_latin"].lower())[:26] or it["text_latin"][:40].lower()
    if k not in best or len(it["text_latin"]) > len(best[k]["text_latin"]):
        best[k] = it
items = sorted(best.values(), key=lambda x: x["leaf_pdf"])

def method(body):
    H = {p: n for p, n in [("I",1),("II",2),("III",3),("IV",4),("V",5),("VI",6),("VII",7),
                           ("VIII",8),("IX",9),("X",10),("XI",11),("XII",12),("XV",15),("XIII",13),("XIV",14)]}
    houses = set()
    for name, num in [("prima",1),("primam",1),("fecunda",2),("secunda",2),("fequente",3),("tertia",3),
                      ("quarta",4),("quartam",4),("quinta",5),("fexta",6),("sexta",6),("feptima",7),
                      ("feptimam",7),("septima",7),("octaua",8),("octava",8),("nona",9),("decima",10),
                      ("vndecima",11),("vndecima",11),("decima tertia",13),("decima quarta",14),
                      ("decima quinta",15),("quartadecima",14),("quintadecima",15)]:
        if re.search(r"\b" + name + r"\b", body, re.I):
            houses.add(num)
    return {
      "houses": sorted(houses),
      "good_terms": len(re.findall(r"\b(bona|bonus|bonum|bene|fortunata|fortior|fortis|lucrum|gain|laetitiam|gaudi)\b", body, re.I)),
      "bad_terms": len(re.findall(r"\b(mala|malum|male|infortunata|debilis|tristitiam|damnum|mors|mortem|infirmitas|carcer|furta|penuriam| detriment)\b", body, re.I)),
      "intrans": len(re.findall(r"\bintrans\b", body, re.I)),
      "exiens": len(re.findall(r"\b(exiens|reiens|tranfiens|transiens|exit)\b", body, re.I)),
      "fixa": len(re.findall(r"\b(fixa|firmissima|firma|fixam)\b", body, re.I)),
      "mobilis": len(re.findall(r"\b(mobilis|volubilis|irregularis)\b", body, re.I)),
      "angles": len(re.findall(r"angul", body, re.I)),
      "extracta": len(re.findall(r"(extracta|educas|ducas\s+figura|trahere|figura ex\s+\w+\s*&)", body, re.I)),
      "life_stage": len(re.findall(r"(iuuentute|iuventute|fenectute|senectute|pueritia|adolefcentia|infantia|aetate)", body, re.I)),
      "witness_or_judge": len(re.findall(r"(teftis|witness|index|judex|iudex)", body, re.I)),
    }
for it in items:
    it["method"] = method(it["text_latin"])

OUT.write_text(json.dumps({
 "_meta": {"source": "Fasciculus geomanticus (1704), 'Alfagini Quaestiones Geomantici', liber secundus/tertius",
   "identifier": "b3299753x", "scan": "corpus/raw/ia/fasciculus_geomanticus_1704.pdf.pdf",
   "leaves_scanned": f"PDF pages {LO}-{HI}",
   "confidence": "MED-HIGH: structure reliable; letter-level Latin may carry OCR slips - check leaf_pdf before quoting",
   "why_it_matters": ("This is a per-question decision engine: it names the houses to consult, the qualities "
      "that decide (bona/mala, intrans/exiens, fixa/mobilis), whether the four angles must consent, and when to "
      "draw a figura extracta from two houses to answer something the shield was not asked."),
   "method_key": {"houses": "houses the rule directs you to",
    "intrans/exiens": "entering vs leaving (same axis as the Calatarama's entrantes/sallentes, and stable/mobile)",
    "fixa/mobilis": "whether the matter stays or changes",
    "angles": "consent of I, IV, VII, X raises the strength of the answer",
    "extracta": "figura extracta - add the two houses named, read the new figure for the hidden cause",
    "life_stage": "which period of life the outcome falls in",
    "witness_or_judge": "the rule appeals to witness/judge figures"}},
 "count": len(items), "items": items}, indent=1))
print("quaestiones captured:", len(items))
for it in items[:6]:
    print(f"  leaf {it['leaf_pdf']}  {it['topic_latin'][:52]!r}  houses={it['method']['houses']} "
          f"in/ex={it['method']['intrans']}/{it['method']['exiens']} ang={it['method']['angles']} ext={it['method']['extracta']}")
