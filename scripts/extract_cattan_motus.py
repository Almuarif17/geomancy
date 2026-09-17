#!/usr/bin/env python3
"""Cattan, The Geomancie (1608) book III -> a figure x house "motion" specifics bank.

Book III walks each of the 16 figures through the houses ("if this figure X be in the first house,
and pass into the second, it signifieth ..."), which is the single most detail-dense table in the
early English corpus. Blackletter OCR is imperfect, so every record keeps its raw ocr_text: the
bank is evidence for a reader to verify, not quotable text.
"""
import re, json, pathlib, collections

SRC = pathlib.Path("corpus/raw/cattan_geomancie_1608.txt")
OUT = pathlib.Path("kb/cattan_motus_bank.json")
seg = re.sub(r"\s+", " ", SRC.read_text(errors="replace")[282000:])

VARIANTS = {
 "Acquisitio": ["acquifito", "acquisito", "aquiſitio", "acquiſitio", "acquilitio"],
 "Amissio": ["amiſſio", "amiliſio", "amilfio", "amiffio", "amiflio", "emiſſio"],
 "Populus": ["populus", "popvlus", "populns"],
 "Via": [" via ", "via,"],
 "Albus": ["albus", "albas"],
 "Rubeus": ["rubeus", "rabeus"],
 "Laetitia": ["leticia", "lleticia", "lzeticia", "lzetitia"],
 "Tristitia": ["tiſtitia", "triſtitia", "triſticia", "tiſticia"],
 "Conjunctio": ["coniunctio", "conjunbtio", "conjunftio"],
 "Carcer": ["carcer", "carci?r", "earcer"],
 "Puella": ["puella", "puclla", "pucll3"],
 "Puer": ["puer,", "puer ", "pusr"],
 "Fortuna Major": ["fortuna maiot", "fortuna mator", "forruna mayor", "fortuna major"],
 "Fortuna Minor": ["fortuna minor", "forruna minor", "fortuna mtnor"],
 "Caput Draconis": ["caput dracenis", "caput draconis", "caput drone"],
 "Cauda Draconis": ["cauda draconis", "cauda dracenis", "cold dragonis", "cauda dragonis"],
}
FIND = [(v, k) for k, vs in VARIANTS.items() for v in vs]
FIND.sort(key=lambda t: -len(t[0]))
FIRSTISH = re.compile(r"\bfir[a-zſ?]{1,5}\b|\bfit\b|\bfirſt\b", re.I)
ORD = {
 # OCR gives either a literal long-s (ſ, normalised to s) or mis-reads it as 'f' - accept both.
 "first":1,"firft":1,"firſt":1,"fit":1,"firt":1,"firde":1,
 "second":2,"fecond":2,"ſecond":2,"ſecone":2,"ſeconde":2,"ſeconbe":2,
 "third":3,"the third":3,
 "fourth":4,"fowerth":4,"foureth":4,
 "fifth":5,"fift":5,"fiftt":5,"菲":5,
 "sixth":6,"fixth":6,"firth":6,"fixt":6,
 "seventh":7,"feventh":7,"ſeventh":7,"ſeuenth":7,"euenth":7,"ſeuenth":7,
 "eighth":8,"eight":8,"cighth":8,
 "ninth":9,"minth":9,"nuieth":9,
 "tenth":10,"xenth":10,"xernth":10,
 "eleventh":11,"eleuenth":11,"eieeenth":11,"ẽuenth":11,
 "twelfth":12,"twellth":12,"twelth":12,"weelfth":12,"tweline":12,
}
CLAUSE = re.compile(r"(?:to|into|in to)\s+the\s+([a-zſ]{3,9})\b\s*(?:heufe|houſe|houfe|houfe)?\s*[:,-]?\s*"
                    r"([^!!.?]{20,240})", re.I)

# candidate block starts = figure-variant occurrences sitting near a "first house" phrase
starts = []
for var, fig in FIND:
    for m in re.finditer(re.escape(var), seg, re.I):
        ctx = seg[m.end():m.end() + 55]
        if FIRSTISH.search(ctx):
            starts.append((m.start(), fig))
starts.sort()
# drop starts that fall inside the previous block's tail (same figure repeated as clause subject)
keep, last = [], -1
for pos, fig in starts:
    if pos - last < 220:
        continue
    keep.append((pos, fig)); last = pos

recs, seen = [], set()
for i, (pos, fig) in enumerate(keep):
    end = keep[i + 1][0] if i + 1 < len(keep) else min(len(seg), pos + 5200)
    blk = seg[pos:end][:5200]
    for c in CLAUSE.finditer(blk):
        w = c.group(1).lower().replace("ſ", "s").replace(":", "")
        h = ORD.get(w) or next((v for k, v in ORD.items() if w.startswith(k)), None)
        if not h:
            continue
        txt = c.group(2).strip(" ,:;")
        if len(txt) < 25 or (fig, h) in seen:
            continue
        seen.add((fig, h))
        recs.append({"figure": fig, "from_house": 1, "to_house": h, "ocr_text": txt[:240]})

cov = collections.Counter(r["figure"] for r in recs)
OUT.write_text(json.dumps({
 "_meta": {"source": "Christopher Cattan, The Geomancie (1608), book III ('A brief deduction of the "
                     "original and signification of the sixteen figures')",
   "identifier": "bim_early-english-books-1475-1640_the-geomancie-of-maister_cattan-christophe-de_1608",
   "method": "figure-name-anchored block split, then 'to the Nth' clause split; raw OCR retained",
   "confidence": "MED - use as leads to verify against a collated edition, not as quotation",
   "coverage": f"{len(cov)} figures / {len(recs)} of a possible 192 transitions"},
 "records": recs}, indent=1))
print(f"{len(keep)} blocks -> {len(recs)} transitions, {len(cov)}/16 figures")
for f in sorted(cov, key=lambda x: -cov[x]): print(f"   {f:18s}{cov[f]:2d}")
print("\nsamples:")
for r in recs[:10]:
    print(f"   {r['figure']:16s} I->{r['to_house']:2d} | {r['ocr_text'][:95]}")
