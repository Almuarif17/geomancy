#!/usr/bin/env python3
"""Finish the job for the relevant set only: probe every one, then download every open text layer
that is not yet in the corpus. Resumable via corpus/ia/meta_cache.json."""
import json, re, pathlib, requests, time
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT=pathlib.Path("corpus/ia"); RAW=pathlib.Path("corpus/raw/ia3"); RAW.mkdir(parents=True,exist_ok=True)
CACHE_F=OUT/"meta_cache.json"; CACHE=json.loads(CACHE_F.read_text()) if CACHE_F.exists() else {}
rel=json.loads((OUT/"ia_full.json").read_text())
def flat(v): return " / ".join(map(str,v)) if isinstance(v,list) else str(v or "")
TOK=re.compile(r"geomanc|geomant|geomanz|raml|ramal|theomagi|calatarama|occulta|agrippa|book of fate|"
               r"losbuch|sortes|sikidy|vintana|odu|ifa|divination|judicial|cattan|heydon|fludd|"
               r"science of the sand|kum hes|shatpanchashika|prasna|lal kitab",re.I)
rel=[d for d in rel if TOK.search(flat(d.get("title"))) or TOK.search(CACHE.get(d["identifier"],{}).get("_coll",""))]
ids=[d["identifier"] for d in rel]
print("relevant items:",len(ids),"| uncached:",sum(1 for i in ids if i not in CACHE))

def probe(i):
    try:
        m=requests.get(f"https://archive.org/metadata/{i}",timeout=28).json()
        files=[f.get("name","") for f in m.get("files",[]) if isinstance(f,dict)]
        md=m.get("metadata",{})
        return i,{"_txt":any(f.endswith("_djvu.txt") for f in files),
                  "_pdf":any(f.endswith(".pdf") for f in files),
                  "_scans":sum(1 for f in files if f.endswith((".jp2",".jpg",".tif"))),
                  "_restricted":md.get("access-restricted-item") in ("true",True,"1","True"),
                  "_coll":",".join(md.get("collection",[]) if isinstance(md.get("collection"),list) else [md.get("collection") or ""])[:56],
                  "_files":files}
    except Exception: return i,None
todo=[i for i in ids if i not in CACHE]
with ThreadPoolExecutor(max_workers=14) as ex:
    for n,(i,r) in enumerate(ex.map(probe,todo),1):
        if r: CACHE[i]=r
        if n%100==0: print(f"  probed {n}/{len(todo)}",flush=True)
CACHE_F.write_text(json.dumps(CACHE))
for d in rel: d.update(CACHE.get(d["identifier"],{}))
(OUT/"ia_full.json").write_text(json.dumps(rel,indent=1))

open_txt=[d for d in rel if d.get("_txt") and not d.get("_restricted")]
have={p.stem for p in RAW.glob("*.txt")} | {p.stem for p in pathlib.Path("corpus/raw/ia").glob("*.txt")}
new=[d for d in open_txt if re.sub(r"[^A-Za-z0-9]","_",flat(d.get("title"))[:44]).strip("_") not in have]
print(f"open with text layer: {len(open_txt)} | to fetch now: {len(new)}")
def fetch(d):
    i=d["identifier"]; p=RAW/f"{i}.txt"
    if p.exists() and p.stat().st_size>4000: return i,"cached"
    try:
        r=requests.get(f"https://archive.org/download/{i}/{i}_djvu.txt",timeout=200)
        if r.ok and len(r.text)>4000:
            p.write_text(r.text); return i,len(r.text)
        return i,"no-layer"
    except Exception as e: return i,str(e)[:40]
KEY={"geomancy":r"geomanc|geomant|raml|ramal","figure":r"figure|figura","judge":r"judge|judex|iudex|richt",
 "witness":r"witness|testis|zeugen","mother":r"mother|matris|mutter|madres|أمهات","daughter":r"daughter|filia|dochter",
 "question":r"question|quaest|demand|frage|prashna|प्रश्न","thief":r"thief|fur|raub|चोर|latron","house":r"house|domus|haus|bhava"}
sig=[]
with ThreadPoolExecutor(max_workers=6) as ex:
    for i,res in ex.map(fetch,new[:40]):
        sig.append((i,res))
        if isinstance(res,int) and (RAW/f"{i}.txt").exists():
            t=(RAW/f"{i}.txt").read_text(errors="replace")
            hits={k:len(re.findall(v,t,re.I)) for k,v in KEY.items()}
            hits={k:v for k,v in hits.items() if v>10}
            print(f"  {i[:40]:40s} {res:8d}ch  {hits}")
print("fetched:",sum(1 for _,r in sig if isinstance(r,int)),"of",min(40,len(new)))
# regenerate the catalogue with complete flags
L=["# Internet Archive — complete harvest\n",
   f"{len(rel)} relevant items (title or collection matches the geomancy / raml / question-oracle family), "
   "from 1,604 unique items found across 38 queries.\n",
   "`txt`=standalone text layer · `rstr`=borrow-only → **free archive.org account + loan** · "
   "`scans`=page images for OCR · `in corpus`=already fetched here\n",
   "| # | identifier | title | year | dl | txt | rstr | scans | in corpus |","|---:|---|---|---|---:|:-:|:-:|---:|:-:|"]
for n,d in enumerate(sorted(rel,key=lambda x:-(x.get("downloads") or 0)),1):
    inb = "✓" if (RAW/f"{d['identifier']}.txt").exists() or any((pathlib.Path('corpus/raw/ia')).glob(f"*{d['identifier'][:12]}*")) else ""
    L.append(f"| {n} | `{d['identifier']}` | {flat(d.get('title'))[:80]} | {d.get('year') or ''} | "
             f"{d.get('downloads') or 0} | {'Y' if d.get('_txt') else '-'} | "
             f"{'**borrow**' if d.get('_restricted') else '-'} | {d.get('_scans',0)} | {inb} |")
(OUT/"IA_CATALOG.md").write_text("\n".join(L)+"\n")
print("\ncatalogue rows:",len(rel))
