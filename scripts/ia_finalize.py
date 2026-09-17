#!/usr/bin/env python3
"""Finish the exhaustive harvest incrementally: bounded per-query, probe with a deadline, save as we go."""
import json, re, time, urllib.parse, pathlib, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

QUERIES = ['geomancy','geomantia','geomancie','geomanzia','geomantie','geomantic',
 'geomancy divination','art of punctuation','judicial astrology','علم الرمل','الرمال','raml',
 'khatt al-raml','Liber geomantiae','Tractatus de Geomantia','Agrippa geomancy','Theomagia',
 'Cattan geomancie','Heydon','Fludd','Book of Fate','Losbuch','sortes','sikidy','vintana',
 'ifa divination','odu','geomancy Yoruba','fansa','ramal shastra','lal kitab','prasna marga',
 'shatpanchashika','science of the sand',"kum hesabı",'geomancia','geomancy arabic','raml islam']
FL=["identifier","title","year","downloads","mediatype","licenseurl","language","pagecount"]
BASE="https://archive.org/advancedsearch.php"
OUT=pathlib.Path("corpus/ia"); PROBE_DEADLINE=time.time()+420

def q(qs, rows=120):
    u=(BASE+"?q="+urllib.parse.quote(f'({qs})')+"&fl[]="+"&fl[]=".join(FL)+
       f"&sort[]=downloads+desc&rows={rows}&page=1&output=json")
    for _ in range(2):
        try:
            j=requests.get(u,timeout=45).json()["response"]; return j["docs"]
        except Exception: time.sleep(0.7)
    return []

docs={}
for qs in QUERIES:
    for d in q(qs):
        i=d.get("identifier")
        if i and i not in docs: d["_q"]=qs; docs[i]=d
print("unique:", len(docs))

CACHE_F=OUT/"meta_cache.json"
CACHE=json.loads(CACHE_F.read_text()) if CACHE_F.exists() else {}
def probe(ident):
    try:
        m=requests.get(f"https://archive.org/metadata/{ident}",timeout=25).json()
        files=[f.get("name","") for f in m.get("files",[]) if isinstance(f,dict)]
        md=m.get("metadata",{})
        return ident,{"_txt":any(f.endswith("_djvu.txt") for f in files),
                      "_pdf":any(f.endswith(".pdf") for f in files),
                      "_scans":sum(1 for f in files if f.endswith((".jp2",".jpg",".tif"))),
                      "_restricted":md.get("access-restricted-item") in ("true",True,"1","True"),
                      "_coll":",".join(md.get("collection",[]) if isinstance(md.get("collection"),list) else [md.get("collection") or ""])[:56]}
    except Exception: return ident,None

todo=[i for i in docs if i not in CACHE]
todo.sort(key=lambda i: -(docs[i].get("downloads") or 0))
done=0
with ThreadPoolExecutor(max_workers=14) as ex:
    futs=[ex.submit(probe,i) for i in todo]
    for fu in as_completed(futs):
        if time.time()>PROBE_DEADLINE:
            print("probe deadline reached; continuing with what we have"); break
        ident,res=fu.result()
        if res: CACHE[ident]=res; done+=1
        if done%150==0 and done:
            CACHE_F.write_text(json.dumps(CACHE)); print(f"  probed {done}/{len(todo)}", flush=True)
CACHE_F.write_text(json.dumps(CACHE))
print("newly probed:",done,"cache size:",len(CACHE))

def flat(v): return " / ".join(map(str,v)) if isinstance(v,list) else str(v or "")
TOK=re.compile(r"geomanc|geomant|geomanz|raml|ramal|theomagi|calatarama|occulta|agrippa|book of fate|"
               r"losbuch|sortes|sikidy|vintana|odu|ifa|divination|judicial|cattan|heydon|fludd|"
               r"science of the sand|kum hes|shatpanchashika|prasna|lal kitab",re.I)
rel=[d for d in docs.values() if TOK.search(flat(d.get("title"))) or TOK.search(flat(CACHE.get(d["identifier"],{}).get("_coll","")))]
for d in rel: d.update(CACHE.get(d["identifier"],{}))
rel.sort(key=lambda d:-(d.get("downloads") or 0))
(OUT/"ia_full.json").write_text(json.dumps(rel,indent=1))
L=["# Internet Archive — complete harvest\n",
   f"{len(docs)} unique items from {len(QUERIES)} queries (each returning the top 120 by downloads, not 60); "
   f"**{len(rel)} relevant** to geomancy / `ilm al-raml` / question-oracles.\n",
   "`txt` = standalone text layer (no OCR needed) · `rstr` = borrow-only, needs a **free archive.org account** "
   "· `scans` = page images, for OCR.\n",
   "| # | identifier | title | year | dl | txt | rstr | scans | licence | found via |",
   "|---:|---|---|---|---:|:-:|:-:|---:|---|---|"]
for n,d in enumerate(rel,1):
    lic=(d.get("licenseurl") or "").replace("https://creativecommons.org/licenses/","").replace("http://","")
    L.append(f"| {n} | `{d['identifier']}` | {flat(d.get('title'))[:86]} | {d.get('year') or ''} | "
             f"{d.get('downloads') or 0} | {'Y' if d.get('_txt') else '-'} | "
             f"{'**borrow**' if d.get('_restricted') else '-'} | {d.get('_scans',0)} | {lic[:18]} | {d.get('_q','')[:20]} |")
(OUT/"IA_CATALOG.md").write_text("\n".join(L)+"\n")
print(f"relevant {len(rel)} | open+txt {sum(1 for d in rel if d.get('_txt') and not d.get('_restricted'))} "
      f"| borrow-only {sum(1 for d in rel if d.get('_restricted'))} | no-layer {sum(1 for d in rel if not d.get('_txt'))}")
