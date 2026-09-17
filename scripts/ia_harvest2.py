#!/usr/bin/env python3
"""Second harvest: other languages + the people/community trail (Dee, Ashmole, Golden Dawn, theosophy)."""
import json, re, time, urllib.parse, pathlib, requests
from concurrent.futures import ThreadPoolExecutor

QUERIES = [
 # Turkish / Ottoman: "kum hesabı" = sand reckoning, the Ottoman name of raml
 '"kum hesabı"', '"ilmi raml"', 'ramalname', 'tûğrâ? raml', 'falname', 'istihare divination',
 # Malay / Indonesian
 '"ilmu ramal"', 'ramal melayu', 'divinasi ramal', 'khasiat? ramal',
 # Persian / Urdu / Hindi
 'رمل', 'نسخه رمل', 'رماله', 'علم الرمل فارسی', 'prashna raml', 'ramal hindi', 'تست رمل',
 # Arabic, more
 '"كتاب الرمل"', 'احكام الرمل', 'علم التurtور? الرمل', 'الرماني رمل', 'زيج? رمل',
 # the English occult lineage that carried it
 '"five books of mystery" Dee', 'Ashmole geomancy', '"true and faithful relation" Dee',
 'Golden Dawn geomancy', "Regardie geomancy", 'Theosophist ramalasastra',
 '"book of the sacred miracles" Leuret', '"key of Solomon" divination',
 # question-and-answer literature
 'Losbuch', '"book of fate"', '"questions of the", astrologer', 'demandes astrologiques',
 '"demandes" geomancie', '"quaestiones" geomantia', 'interrogation astrologique réponse',
 # Italy / Iberia / E. Europe
 'geomanzia domande', "geomancia 'quaestio'", 'geomancie perguntas', 'wróżby geomancja',
 'гаомантия', 'геомантия вопросы',
 # Africa beyond Ifa
 'Fa divination Ghana', 'Afa Babila', 'sikidy ombiasy', 'raml Moroc', 'shrafa sorcery Morocco',
 'kine? geomancy Senegal', 'tiidje wolof',
]
BASE = "https://archive.org/advancedsearch.php"
FL = ["identifier","title","year","downloads","mediatype","licenseurl","language","pagecount"]
seen, docs = set(), []
for q in QUERIES:
    url = (BASE + "?q=" + urllib.parse.quote(f'({q})') + "&fl[]=" + "&fl[]=".join(FL) +
           "&sort[]=downloads+desc&rows=40&page=1&output=json")
    try:
        r = requests.get(url, timeout=45)
        for d in r.json()["response"]["docs"]:
            if d["identifier"] in seen: continue
            seen.add(d["identifier"]); d["_query"] = q; docs.append(d)
    except Exception: pass
    time.sleep(0.1)
print("unique:", len(docs))
KEEP = re.compile(r"raml|ramal|geomanc|geomanz|geomant|losbuch|book of fate|fal.?n|kum hes|"
                  r"istihar|prashna|siku?dy|sikidy|vintana|dea?l?tion figures|theatrum|five books of mystery|"
                  r"key of solomon|golden dawn|regardie|ramalasastra", re.I)
keep = []
for d in docs:
    t = d.get("title"); t = " / ".join(map(str,t)) if isinstance(t,list) else str(t or "")
    if KEEP.search(t):
        d["_title"] = t; keep.append(d)
keep.sort(key=lambda d: -(d.get("downloads") or 0))
pathlib.Path("corpus/ia/ia_catalog2.json").write_text(json.dumps(keep, indent=1))
for d in keep[:40]:
    print(f"{d.get('downloads',0):7d} {d['identifier'][:44]:44s} {d.get('year','')} {str(d.get('language'))[:8]:8s} {d['_title'][:76]}")
print("kept:", len(keep))
