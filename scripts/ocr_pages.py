#!/usr/bin/env python3
"""Parallel page OCR for a specific page list — bounded, resumable, cached."""
import sys, pathlib, subprocess, re, pymupdf
from concurrent.futures import ThreadPoolExecutor
pdf, pagespec, out, langs, dpi = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]), sys.argv[4], int(sys.argv[5])
pages=[]
for p in pagespec.split(","):
    if "-" in p: a,b=p.split("-"); pages+=list(range(int(a),int(b)+1))
    else: pages.append(int(p))
d=pymupdf.open(pdf); (out if out.suffix=="" else out.parent).mkdir(parents=True,exist_ok=True)
def one(i):
    f=out/f"p{i:04d}.txt"
    if f.exists() and f.stat().st_size>200: return i,"cached"
    p=pathlib.Path(f"/tmp/ocr_{i}.png")
    d[i].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY).save(p)
    r=subprocess.run(["tesseract",str(p),"stdout","-l",langs,"--psm","6"],capture_output=True,text=True)
    f.write_text(r.stdout); p.unlink(missing_ok=True); return i,len(r.stdout)
with ThreadPoolExecutor(max_workers=6) as ex:
    res=list(ex.map(one,pages))
print("done:",len(res),"chars total:",sum(v for _,v in res if isinstance(v,int)))
