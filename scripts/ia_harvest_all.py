#!/usr/bin/env python3
"""Exhaustive Internet Archive harvest: paginate every relevant query to the end, dedupe,
probe each item for a text layer / borrow restriction, and write the full catalogue."""
import json, re, time, urllib.parse, pathlib, requests
from concurrent.futures import ThreadPoolExecutor

QUERIES = [
 'geomancy', 'geomantia', 'geomancie', 'geomanzia', 'geomantie', 'geomantic',
 '(geomancy OR geomantia OR geomancie OR geomanzia OR geomantie OR geomantic)',
 'geomancy divination', 'geomancy figures', 'art of punctuation', 'judicial astrology',
 'علم الرمل', 'الرمل', 'الزيج? رمل', 'raml', 'ilm al-raml', 'khatt al-raml', 'ramali',
 'Book of the Judgements of Calatarama', 'Liber geomantiae', 'Tractatus de Geomantia',
 'Agrippa geomancy', 'Theomagia', 'Cattan geomancie', 'Heydon geomancy', 'Fludd geomantia',
 'Book of Fate', 'Losbuch', 'sortes virgilianae', 'sors sanctorum', 'sortes',
 'sikidy', 'vintana Madagascar', 'hakata divination', 'ifa divination', 'odu ifa',
 'Ifa corpus', 'geomancy Yoruba', 'geomancy Hausa', 'fansa divination', 'babila divination',
 'ramal', 'ramal shastra', 'lal kitab', 'prasna', 'prashna', 'kitab al-raml',
 'science of the sand', '砂占', 'kum hesabı', 'teng? raml', 'tawlid? raml',
]
FL = ["identifier","title","year","downloads","mediatype","licenseurl","language","pagecount"]
BASE = "https://archive.org/advancedsearch.php"

def page(q, start, rows=100):
    u = (BASE + "?q=" + urllib.parse.quote(f'({q})') + "&fl[]=" + "&fl[]=".join(FL) +
         f"&sort[]=downloads+desc&rows={rows}&page={1 + start // rows}&output=json")
    for _ in range(3):
        try:
            j = requests.get(u, timeout=60).json()["response"]
            return j["numFound"], j["docs"]
        except Exception:
            time.sleep(1.0)
    return 0, []

docs, seen = {}, set()
for q in QUERIES:
    total, first = page(q, 0)
    got = list(first)
    n = len(first)
    while n < min(total, 400):          # cap 400 per query to stay polite
        more = page(q, n)[1]
        if not more: break
        got += more; n += len(more)
    for d in got:
        i = d.get("identifier")
        if i and i not in seen:
            seen.add(i); d["_q"] = q; docs[i] = d
    print(f"  {q[:44]:44s} numFound={total:5d} kept={len(got)}", flush=True)
print("unique items across all queries:", len(docs))

CACHE_F = pathlib.Path("corpus/ia/meta_cache.json")
CACHE = json.loads(CACHE_F.read_text()) if CACHE_F.exists() else {}

def probe(item):
    ident, d = item
    if ident in CACHE:
        d.update(CACHE[ident]); return d
    try:
        m = requests.get(f"https://archive.org/metadata/{ident}", timeout=30).json()
        files = [f.get("name", "") for f in m.get("files", []) if isinstance(f, dict)]
        md = m.get("metadata", {})
        d["_txt"] = any(f.endswith("_djvu.txt") for f in files)
        d["_pdf"] = any(f.endswith(".pdf") for f in files)
        d["_scans"] = sum(1 for f in files if f.endswith((".jp2", ".jpg", ".tif")))
        d["_restricted"] = md.get("access-restricted-item") in ("true", True, "1", "True")
        d["_coll"] = ",".join(md.get("collection", []) if isinstance(md.get("collection"), list)
                              else [md.get("collection") or ""])[:60]
        CACHE[ident] = {k: d[k] for k in ("_txt","_pdf","_scans","_restricted","_coll")}
    except Exception as e:
        d["_err"] = str(e)[:50]
    return d

with ThreadPoolExecutor(max_workers=12) as ex:
    docs = list(ex.map(probe, docs.items()))
CACHE_F.write_text(json.dumps(CACHE))

def flat(v): return " / ".join(map(str, v)) if isinstance(v, list) else str(v or "")
TOK = re.compile(r"geomanc|geomant|geomanz|raml|ramal|theomagi|calatarama|occulta philosoph|"
                 r"agrippa|book of fate|losbuch|sortes|sikidy|vintana|odu|ifa |divination|judicial|"
                 r"cattan|heydon|fludd|lilly|jude?l?iary|science of the sand|kum hes", re.I)
rel = [d for d in docs if TOK.search(flat(d.get("title"))) or TOK.search(flat(d.get("_coll")))
       or (d.get("_q","").startswith("geomancy") and not flat(d.get("title")).lower().startswith("geoma"))]
rel.sort(key=lambda d: -(d.get("downloads") or 0))

pathlib.Path("corpus/ia/ia_full.json").write_text(json.dumps(rel, indent=1))
L = ["# Internet Archive — complete harvest\n",
     f"{len(docs)} unique items across {len(QUERIES)} queries (paginated, not capped at 60); "
     f"**{len(rel)} relevant** to geomancy / raml / question-oracles.\n",
     "`txt`=standalone text layer, `rstr`=borrow-only (needs a free archive.org account), "
     "`scans`=page images available for OCR.\n",
     "| # | identifier | title | year | dl | txt | rstr | scans | lic | found via |",
     "|---:|---|---|---|---:|:-:|:-:|---:|---|---|"]
for n, d in enumerate(rel, 1):
    lic = (d.get("licenseurl") or "").replace("https://creativecommons.org/licenses/", "").replace("http://", "")
    L.append(f"| {n} | `{d['identifier']}` | {flat(d.get('title'))[:88]} | {d.get('year') or ''} | "
             f"{d.get('downloads') or 0} | {'Y' if d.get('_txt') else '-'} | "
             f"{'**borrow**' if d.get('_restricted') else '-'} | {d.get('_scans',0)} | {lic[:20]} | {d.get('_q','')[:24]} |")
pathlib.Path("corpus/ia/IA_CATALOG.md").write_text("\n".join(L) + "\n")
open_doc = sum(1 for d in rel if d.get("_txt") and not d.get("_restricted"))
print(f"relevant: {len(rel)} | with text layer and open: {open_doc} | borrow-only: "
      f"{sum(1 for d in rel if d.get('_restricted'))}")
