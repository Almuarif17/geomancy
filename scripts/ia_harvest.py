#!/usr/bin/env python3
"""Fish Internet Archive for everything geomancy-adjacent, deduplicate, score, and record how to get each one.

Broad on purpose: the material hides under Latin/French/Italian/German titles, under 'judicial
astrology', under Arabic 'ilm al-raml', under African and Indian divination names, and under the
medieval 'Losbuch'/sortes (question -> answer) literature.
"""
import json, re, time, urllib.parse, pathlib, sys
from concurrent.futures import ThreadPoolExecutor
import requests

QUERIES = {
 "core_en":        ['geomancy', 'geomantic figures', '"geomantia"', 'geomanzia', 'geomancie', 'geomantie'],
 "arabic":         ['"ilm al-raml"', '"ilm al-raml"', 'al-raml divination', '"khatt al-raml"',
                    'علم الرمل', 'الرمل', 'فصل في اصول علم الرمل', 'الزنجatian'],
 "judicial_astro": ['judicial astrology', 'astrology divination figures', '"practica" astrology Lilly',
                    'horary astrology questions', 'elections astrology'],
 "casebooks":      ['Losbuch', 'sortes', "sors sanctorum", 'sortes virgilianae', 'book of lots',
                    'oracle of the', 'questions and answers divination', 'demands geomancy'],
 "african_ifa":    ['ifa divination odu', 'Ifa: sixteen cowries', 'Fa divination', 'sikidy Madagascar',
                    'vintana divination', 'hakata divination', 'geomancy Yoruba', 'geomancy Hausa fansa',
                    'tinbuktu manuscripts divination'],
 "south_asian":    ['ramalastra', 'ramalasastra', 'Lal Kitab', 'Prasna Marga', 'prashna astrology',
                    'yogic divination', 'Samudrika', 'Indian divination dice'],
 "east_asian":     ['I Ching Legge', 'Yi King', 'Ching divination', 'fu-ching'],
 "hermetic_pd":    ['Agrippa occulta philosophia', 'Theomagia Heydon', 'Trithemius', 'De occulta philosophia',
                    "Cardano astrology", 'Delrio magickes', 'Bodies of the earth divination'],
 "manuscript_cat": ['catalogue manuscripts astrology', 'alchemical manuscripts catalogue',
                    'oriental manuscripts catalogue divination'],
 "francais":       ['géomancie', 'divination par les points', 'sortiléges', 'arts divinatoires',
                    'Théomagie', 'agripa'],
}

BASE = "https://archive.org/advancedsearch.php"
FIELDS = ["identifier", "title", "year", "downloads", "mediatype", "licenseurl", "collection",
          "creator", "language", "pagecount", "access-restricted-item"]

def search(q, rows=60):
    url = (BASE + "?q=" + urllib.parse.quote(f'({q})') +
           "&fl[]=" + "&fl[]=".join(FIELDS) +
           f"&sort[]=downloads+desc&rows={rows}&page=1&output=json")
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=45)
            if r.status_code == 200:
                return r.json()["response"]["docs"]
        except Exception:
            time.sleep(1.5)
    return []

seen, docs = {}, []
for group, qs in QUERIES.items():
    for q in qs:
        for d in search(q):
            ident = d.get("identifier")
            if not ident or ident in seen:
                continue
            seen[ident] = True
            d["_group"] = group
            d["_query"] = q
            docs.append(d)
        time.sleep(0.15)
print(f"unique items: {len(docs)}")

def has_text(d):
    ident = d["identifier"]
    for suffix in (f"/{ident}_djvu.txt", "/djvu.txt", f"/{ident}_text.pdf", "/meta.xml"):
        try:
            r = requests.head(f"https://archive.org/download{suffix}" if not suffix.startswith("/meta")
                              else f"https://archive.org/metadata/{ident}", timeout=12, allow_redirects=True)
            if r.status_code == 200 and int(r.headers.get("content-length") or 0) > 3000:
                return True
        except Exception:
            pass
    return False

CACHE, CACHE_F = {}, pathlib.Path("corpus/ia/meta_cache.json")
if CACHE_F.exists():
    try: CACHE = json.loads(CACHE_F.read_text())
    except Exception: CACHE = {}

def check(d):
    ident = d["identifier"]
    if ident in CACHE:
        d.update(CACHE[ident]); return d
    try:
        m = requests.get(f"https://archive.org/metadata/{ident}", timeout=25).json()
        files = m.get("files", [])
        names = [f.get("name", "") for f in files]
        txt = [n for n in names if n.endswith("_djvu.txt") or n.endswith("_text.pdf")]
        pdf = [n for n in names if n.endswith(".pdf")]
        d["_files"] = {"text_layers": len(txt), "pdf": len(pdf),
                       "scans": sum(1 for n in names if n.endswith((".jp2", ".jpg", ".tif")))}
        d["_has_txt"] = bool(txt)
        d["_has_pdf"] = bool(pdf)
        colls = m.get("metadata", {}).get("collection", [])
        d["_collections"] = colls if isinstance(colls, list) else [colls]
        d["_access"] = m.get("metadata", {}).get("access-restricted-item", "")
        d["_locator"] = (m.get("server"), m.get("dir"))
        CACHE[str(ident)] = {"_files": d["_files"], "_has_txt": d["_has_txt"], "_has_pdf": d["_has_pdf"],
                             "_collections": d["_collections"], "_access": d["_access"]}
    except Exception as e:
        d["_files"] = {"error": str(e)[:60]}
        d["_has_txt"] = d["_has_pdf"] = False
    return d

with ThreadPoolExecutor(max_workers=12) as ex:
    docs = list(ex.map(check, docs))
CACHE_F.parent.mkdir(parents=True, exist_ok=True)
CACHE_F.write_text(json.dumps(CACHE, indent=0))

def flat(v):
    if isinstance(v, list):
        return " / ".join(str(x) for x in v)
    return str(v or "")

def score(d):
    t = flat(d.get("title")).lower()
    s = 0
    for k, w in [("geomanc", 30), ("geomant", 30), ("raml", 26), ("divination", 14), ("astrolog", 10),
                 ("judicial", 10), ("sortes", 10), ("losbuch", 10), ("ifa", 14), ("odu", 12),
                 ("theomagi", 22), ("agrippa", 14), ("occulta", 12), ("figures", 6), ("lots", 5),
                 ("sikidy", 14), ("vintana", 12), ("lal kitab", 12), ("marga", 10), ("ching", 8)]:
        if k in t: s += w
    if d.get("_has_txt"): s += 8
    if d.get("licenseurl"): s += 3
    if d.get("_files", {}).get("scans", 0) > 40: s += 2
    return s

for d in docs:
    d["_score"] = score(d)
docs.sort(key=lambda d: -d["_score"])
pathlib.Path("corpus/ia/ia_catalog.json").write_text(json.dumps(docs, indent=1))

TOK = re.compile(r"geomanc|geomant|raml|theomagi|occulta philosoph|agrippa|sikidy|vintana|odu|ifa |"
                 r"lal kitab|marga|losbuch|sortes|book of lots|divination|judicial", re.I)
keep = [d for d in docs if d["_score"] >= 14 or TOK.search(flat(d.get("title")))]
lines = ["# Internet Archive harvest\n",
         f"Queried {sum(len(v) for v in QUERIES.values())} search strings across {len(QUERIES)} groups; "
         f"{len(docs)} unique items, **{len(keep)} relevant** (score >= 14 or title matches).\n",
         "`txt` = a standalone text layer is present (no OCR needed). `lic` = license/usage field on the item.\n",
         "| score | identifier | title | year | dl | txt | pdf | scans | license | group |",
         "|---:|---|---|---|---:|:-:|:-:|---:|---|---|"]
for d in keep[:160]:
    lic = (d.get("licenseurl") or "").replace("http://", "").replace("https://", "")
    lines.append(f"| {d['_score']} | `{d['identifier']}` | {flat(d.get('title'))[:92]} | "
                 f"{d.get('year') or ''} | {d.get('downloads') or 0} | {'Y' if d.get('_has_txt') else '-'} | "
                 f"{'Y' if d.get('_has_pdf') else '-'} | {d['_files'].get('scans', 0)} | {lic[:34]} | {d['_group']} |")
pathlib.Path("corpus/ia/IA_CATALOG.md").write_text("\n".join(lines) + "\n")
print(f"relevant: {len(keep)}  (top: {[d['identifier'] for d in keep[:14]]})")
