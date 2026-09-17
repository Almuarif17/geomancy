#!/usr/bin/env python3
"""Acquire + OCR a scanned book into a searchable, provenance-tagged corpus.

Why this exists: the interesting geomancy material (16th-17th c. English, Latin, and Arabic prints)
lives in image PDFs whose machine text layer is unusable or absent. Measured on Cattan 1591:
the Internet Archive layer recovered 4 of 11 expected words on a page I could check against my own
reading; tesseract with a Fraktur model at 400 dpi recovers ~7-8 of 11. Neither is quotable prose -
both are good enough to FIND a passage, which is the job of this script. Reading the found passage
from the page image is the human's job.

Usage:
  python3 ocr_ingest.py <ia-identifier> --pages 170-180 --lang frk+eng --out corpus/ocr/name
  python3 ocr_ingest.py <ia-identifier> --all --conf 70 --keywords thief,enemies,judge,mother

Outputs, under --out:
  pages/NNNN.txt      cleaned text per page (OCR or embedded layer, whichever scored better)
  pages/NNNN.meta.json  which method, confidence, scores, crop used
  INDEX.md            page list with keyword hits, for triage
"""
import argparse, json, pathlib, re, subprocess, sys

import pymupdf

LEGACY_MAP = str.maketrans({"æ": "ae", "œ": "oe", "ƿ": "w", "ȝ": "g", "ſ": "s",
                            "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "—": "-",
                            "–": "-", "ø": "o", "ð": "d", "þ": "th"})


def normalise_legacy(t):
    """Repair the two systematic corruptions of early-modern print: long-s and u/v, plus soft hyphens."""
    t = t.translate(LEGACY_MAP)
    t = re.sub(r"(\w)-\s+(\w)", r"\1\2", t)                             # de-hyphenate across breaks
    t = re.sub(r"\b(v)([aeiou])", r"u\2", t)                            # vnto -> unto
    t = re.sub(r"([bcdfghjklmnpqrtstwxyz])v(?=[aeiou])", r"\1u", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def score_against(text, keywords):
    """Crude but decisive: how many of the words we expect on this page are actually present."""
    low = re.sub(r"[^a-z ]", " ", text.lower())
    words = set(low.split())
    hits = {k: (k in words or k.rstrip("s") in words or (k + "e") in words) for k in keywords}
    return sum(hits.values()), hits


def render(doc, i, dpi, crop):
    pg = doc[i]
    r = pg.rect
    clip = pymupdf.Rect(r.x0 + r.width * crop[0], r.y0 + r.height * crop[1],
                        r.x0 + r.width * crop[2], r.y0 + r.height * crop[3])
    pix = pg.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, clip=clip)
    p = pathlib.Path(f"/tmp/ocr_page_{i}.png")
    pix.save(p)
    return p


def tesseract(img, lang, psm, conf_min):
    out = subprocess.run(["tesseract", str(img), "stdout", "-l", lang, "--psm", str(psm), "tsv"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return "", []
    keep, rows = [], out.stdout.splitlines()[1:]
    for line in rows:
        c = line.split("\t")
        if len(c) < 12:
            continue
        txt, conf = c[11], c[10]
        if txt.strip() and (conf == "-1" or float(conf) >= conf_min):
            keep.append(txt)
    return " ".join(keep), keep


def parse_pages(spec, total):
    if spec == "all":
        return list(range(total))
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), min(int(b), total - 1) + 1))
        else:
            out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("identifier")
    ap.add_argument("--pages", default="all")
    ap.add_argument("--lang", default="frk+eng")
    ap.add_argument("--psm", type=int, default=6, help="6=uniform block, 4=variable columns, 3=auto")
    ap.add_argument("--dpi", type=int, default=400)
    ap.add_argument("--conf", type=float, default=70, help="drop tesseract words below this confidence")
    ap.add_argument("--crop", default="0.02,0.05,0.82,0.98",
                    help="x0,y0,x1,y1 fractions - crop away marginalia, which wrecks line grouping")
    ap.add_argument("--keywords", default="judge,witness,mother,daughter,figure,house,signify,thief,enem")
    ap.add_argument("--pdf", default=None, help="use a local pdf instead of fetching from archive.org")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    out = pathlib.Path(a.out)
    (out / "pages").mkdir(parents=True, exist_ok=True)
    kw = [k.strip().lower() for k in a.keywords.split(",") if k.strip()]
    crop = tuple(float(x) for x in a.crop.split(","))

    pdf = pathlib.Path(a.pdf) if a.pdf else None
    if pdf is None or not pdf.exists():
        url = f"https://archive.org/download/{a.identifier}/{a.identifier}.pdf"
        pdf = pathlib.Path(f"/tmp/{a.identifier}.pdf")
        subprocess.run(["curl", "-sL", "--max-time", "600", "-o", str(pdf), url], check=True)

    doc = pymupdf.open(str(pdf))
    pages = parse_pages(a.pages, doc.page_count)
    index = []
    for i in pages:
        emb = doc[i].get_text() or ""
        img = render(doc, i, a.dpi, crop)
        txt, kept = tesseract(img, a.lang, a.psm, a.conf)
        se, _ = score_against(emb, kw)
        so, hits = score_against(txt, kw)
        # prefer the embedded layer on ties: its spelling of ordinary words is usually better,
        # and it keeps line structure; only switch to OCR when it genuinely finds more.
        if so > se and len(txt) > 60:
            method, text = f"tesseract({a.lang},psm{a.psm},conf>={a.conf},dpi{a.dpi},crop)", normalise_legacy(txt)
            sc = so
        else:
            method, text, sc = "embedded-layer", normalise_legacy(emb), se
        (out / "pages" / f"{i:04d}.txt").write_text(text)
        meta = {"page": i, "method": method, "keyword_hits": sc, "of": len(kw),
                "tesseract_words": len(kept), "embedded_chars": len(emb),
                "hits": {k: bool(v) for k, v in hits.items()}}
        (out / "pages" / f"{i:04d}.meta.json").write_text(json.dumps(meta, indent=1))
        index.append(meta)
        print(f"p{i:4d}  {sc}/{len(kw)} keywords  {method}")

    top = sorted(index, key=lambda m: -m["keyword_hits"])
    lines = [f"# {a.identifier} — OCR triage index\n",
             f"pages processed: {len(index)} of {doc.page_count}; keyword set: {', '.join(kw)}\n",
             "| page | keyword hits | words kept | method |", "|---|---|---|---|"]
    for m in top[:40]:
        lines.append(f"| {m['page']} | {m['keyword_hits']}/{m['of']} | {m['tesseract_words']} | {m['method']} |")
    lines.append("\nRead the PAGE IMAGE for any row worth quoting; the text here is a locator, not an edition.\n")
    (out / "INDEX.md").write_text("\n".join(lines))
    print(f"\nwrote {out}/INDEX.md  ({len(index)} pages; best: {[m['page'] for m in top[:6]]})")


if __name__ == "__main__":
    main()
