#!/usr/bin/env python3
"""Jean de la Taille, 'La Geomancie' (16th c., in bub_gb_6ajNTSLF0IgC) -> kb/lataille_grid.json

A second figure x house ruling grid, in French vernacular, with rules the Latin and Castilian
sources do not give: mobile or 'common' figures hand the judgement over to the QUALITY OF THE HOUSE,
and the 4th together with the 15th gives the end of any matter.
"""
import json, re, pathlib, difflib
SRC = pathlib.Path("corpus/raw/ia3/lataille_la_geomancie.txt")
OUT = pathlib.Path("kb/lataille_grid.json")
t = re.sub(r"\s+", " ", SRC.read_text(errors="replace"))
i0 = t.lower().find("geomanc")
body = t[max(0, i0 - 200):]

FR = {"voie": "Via", "peuple": "Populus", "blanche": "Albus", "conjonction": "Conjunctio",
      "pucele": "Puella", "pucelle": "Puella", "garson": "Puer", "garcon": "Puer",
      "rouge": "Rubeus", "perte": "Amissio", "tristesse": "Tristitia", "joie": "Laetitia",
      "fortune majeure": "Fortuna Major", "fortune mineure": "Fortuna Minor",
      "prison": "Carcer", "teste du dragon": "Caput Draconis", "queue au dragon": "Cauda Draconis",
      "queue du dragon": "Cauda Draconis", "acquet": "Acquisitio", "acquisition": "Acquisitio"}
ORD = {"premiere": 1, "feconde": 2, "seconde": 2, "troifme": 3, "troisiefme": 3, "troisieme": 3,
       "quatriefme": 4, "quatrieme": 4, "cinquiefme": 5, "cinquieme": 5, "fixiefme": 6, "sixiefme": 6,
       "fixieme": 6, "feptiefme": 7, "septieme": 7, "huictiefme": 8, "huitieme": 8, "nefiefme": 9,
       "neuvieme": 9, "difme": 10, "dixieme": 10, "onziefme": 11, "onzieme": 11, "douziefme": 12,
       "douzieme": 12, "treziefme": 13, "quatorziefme": 14, "quinziefme": 15}
def figname(s):
    s = re.sub(r"[^a-zêîûàé ]", " ", s.lower()).strip()
    if s in FR: return FR[s]
    best, sc = None, 0.62
    for k, v in FR.items():
        r = difflib.SequenceMatcher(None, s, k).ratio()
        if r > sc: best, sc = v, r
    return best

HEAD = re.compile(r"(?i)(?:DE\s+LA|DV\s+LA|EN\s+LA)\s+([a-zſêîûàé]{4,14})\s*(?:MAISON|MAIFON|MA[îi]SON)")
def norm_ordinal(w):
    w = w.lower().replace("ſ", "s").replace("v", "u").replace("i", "i")
    w = (w.replace("u", "i") if False else w)
    w = w.replace("ſ", "s")
    for a, b in [("ê","e"),("é","e"),("è","e"),("à","a"),("î","i"),("ô","o"),("û","u")]:
        w = w.replace(a, b)
    # the print renders -me/-me variously; fold common variants
    for suf in ["me","me.","mefme","mieme","me"]:
        if w.endswith(suf): w = w[: -len(suf)]; break
    KEY = {"premier":1,"prem":1,"fecond":2,"fecond":2,"fecod":2,"fec":2,"fe":2,"trois":3,"tro":3,
           "trof":3,"quatr":4,"quart":4,"quatri":4,"cinqu":5,"cin":5,"fix":6,"fex":6,"f":6,
           "fept":7,"fe":7,"fep":7,"huict":8,"huit":8,"neuf":9,"nef":9,"di":10,"dif":10,"dix":10,
           "onze":11,"onz":11,"douze":12,"douz":12,"treize":13,"trez":13,"quatorze":14,"quatorz":14,
           "quinze":15,"quinz":15}
    for k, v in KEY.items():
        if w.startswith(k): return v
    return None
heads = [(m.start(), norm_ordinal(m.group(1))) for m in HEAD.finditer(body)]
heads = [(p, n) for p, n in heads if n]
items = []
for k, (pos, house) in enumerate(heads):
    end = heads[k + 1][0] if k + 1 < len(heads) else len(body)
    seg = body[pos:end]
    for m in re.finditer(r"(?i)\b(?:Si|Lorsque|Quand)\s+([A-Za-zà-ÿ' ]{3,24}?)[,;:]\s*(.{50,700}?)(?=\b(?:Si|Lorsque|Quand)\s+[A-Za-zà-ÿ' ]{3,24}?[,;:]|\bNotez\b|$)", seg):
        f = figname(m.group(1))
        txt = re.sub(r"\s+", " ", m.group(2)).strip(" .,;:")
        if f and len(txt) >= 40:
            items.append({"house": house, "figure": f, "ruling_fr": txt[:600]})
best = {}
for it in items:
    key = (it["house"], it["figure"])
    if key not in best or len(it["ruling_fr"]) > len(best[key]["ruling_fr"]):
        best[key] = it
grid = sorted(best.values(), key=lambda x: (x["house"], x["figure"]))
OUT.write_text(json.dumps({
 "_meta": {"source": "Jean de la Taille (seigneur de Bondaroy), La Geomancie - French, via IA item LaGeomanceAbregeeDeIeanDeLaTailleDeBondaroy",
   "grid": f"{len(grid)} figure-house rulings across {len(set(g['house'] for g in grid))} houses",
   "extra_rules": [
     "'files figures eftoient mobiles ou communes, preferez le jugement felon les qualitez des maisons' - "
     "a mobile or common figure hands the verdict over to the house's own quality (the tie-break rule)",
     "'la quatriefme avec la quinziefme la fin' - read the 4th together with the 15th for the END of any matter",
     "'le Thresor cache eft en la garde du Diable' - Populus in the 4th: the hidden treasure is under the Devil's keeping",
     "the figure attributions run their own course here (Perte=Amissio is 'of Venus retrograde, in Scorpio, of the element of Fire')"],
   "confidence": "MED: 16th-c. French print with long-s; OCR repairs names, so check before quoting",
   "language": "fr"},
 "grid": grid}, indent=1))
print("rulings:", len(grid), "| houses covered:", sorted(set(g["house"] for g in grid)))
for g in grid[:5]: print(f"  house {g['house']:2d} {g['figure']:16s} {g['ruling_fr'][:105]}")
