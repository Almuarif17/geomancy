#!/usr/bin/env python3
"""Mine the concrete-danger / specific-fate sentences out of Cattan 1591's (poor) blackletter layer.

These are the "beware of a knife"-grade particulars people expect from a cast. They ARE in the old
printed English, per figure per house. The OCR is bad, so every record keeps page number + raw
string, and the confidence is LOW-MED: use it as a pointer to read the page image, never as a quote.
"""
import re, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mine import canon

PAGES = pathlib.Path("corpus/ocr/cattan1591_book3/pages")
TOPIC = {
 "killed_by_weapon": r"flai\w+\s+with\s+a\s+\w{3,12}",
 "weapon_words": r"(?:fweord|fword|fftaffe|ftaffe|knife|kni|ftafile)",
 "poison": r"poyson|poreon|pzoifon|venom",
 "prison_bonds": r"prifon|prifoner|carcer|impri",
 "sick_death": r"(?:ficke|fick|fapient|fie\w*)\s+\w{0,10}\s*(?:die|danger|amend|mende)",
 "drowning_water": r"drown|drowning|water|feea",
 "betrayal_friend": r"(?:friend|frend|betrap|treafon|traifon)",
 "woman_marriage": r"(?:marriage|woman|wyfe|hufband|wench)",
 "money_loss": r"(?:coyne|money|garne|p2ofit|loffe|gain)",
 "travel_delay": r"(?:voyage|travell|journey|long\b)",
}
FIG = {"Puer":r"p»er|puer|pbet","Rubeus":r"%ubew|rubeu","Populus":r"po?oul|popu|p0p",
 "Carcer":r"carcer|ctfccr|etfccr","Albus":r"albu|albui","Via":r"\bvis\b|\bvia\b",
 "Laetitia":r"laetitia|lzetitia","Tristitia":r"tristitia|tiistitia","Puella":r"puella|puclla",
 "Acquisitio":r"acqui|aquii","Amissio":r"amiff|emi|amii","Conjunctio":r"conj|conij",
 "Fortuna_Major":r"fortuna\W*may","Fortuna_Minor":r"fortuna\W*min","Caput":r"caput|bead",
 "Cauda":r"cauda|taile"}
recs = []
for f in sorted(PAGES.glob("*.txt")):
    page = int(f.stem)
    raw = re.sub(r"\s+", " ", f.read_text())
    for topic, rx in TOPIC.items():
        for m in re.finditer(rx, raw, re.I):
            s = max(0, m.start()-260); ctx = raw[s:m.end()+260]
            fig = next((k for k, v in FIG.items() if re.search(v, ctx, re.I)), None)
            house = None
            hm = list(re.finditer(r"(first|fecond|third|fourth|fift|fixth|feventh|eighth|ninth|tent[ht]|eleventh|twelf\w*)\s+(?:bou|ho)\w?", ctx, re.I))
            if hm:
                ORD = dict(first=1, fecond=2, third=3, fourth=4, fift=5, fixth=6, feventh=7,
                           eighth=8, ninth=9, tenth=10, eleventh=11, twelfth=12)
                house = ORD.get(hm[-1].group(1).lower())
            if not fig:
                continue
            recs.append({"page": page, "figure": fig.replace("_", " "), "house": house,
                         "topic": topic, "raw": ctx.strip()[:320],
                         "confidence": "LOW-MED (blackletter OCR; verify on the page image)"})
seen, out = set(), []
for r in recs:
    k = (r["figure"], r["topic"], r["page"])
    if k in seen: continue
    seen.add(k); out.append(r)
pathlib.Path("kb/cattan1591_dangers.json").write_text(json.dumps({
 "_meta": {"source": "Cattan 1591 (b30337860), book III, pages 140-180, my OCR pass",
  "purpose": "pointer index to the concrete-fate particulars (weapons, poison, prison, sickness, money, travel) per figure per house",
  "warning": "OCR quality on 16th-c blackletter is ~65% recall; these strings are leads to the PAGE IMAGE, not quotations. For a quotable text you need HTR (Transkribus/Kraken) or a collated edition."},
 "records": out}, indent=1))
print(f"{len(out)} records over pages {sorted({r['page'] for r in out})[:12]}")
for r in out[:6]:
    print(f"\n  p{r['page']} {r['figure']} house={r['house']} [{r['topic']}]\n     {r['raw'][:200]}")
