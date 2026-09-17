#!/usr/bin/env python3
"""Advanced OCR pipeline for early-print / scanned geomancy sources.

Handles the three things that break naive OCR on these books:
  1. no text layer (or a garbage one) -> render the page image ourselves
  2. blackletter / Fraktur type        -> tesseract 'frk' model, with eng+lat fallback
  3. long-s (ſ) read as 'f', hyphenated line breaks, column bleed
and emits a clean text layer plus a quality score so we know what to trust.

Usage:  ocr_pipeline.py <pdf> <out_prefix> [pages...]   (pages are 0-based)
"""
import subprocess, sys, re, pathlib
import pymupdf

DPI = 400
LANGS = "frk+lat+eng"

def render(doc, i, dpi=DPI):
    pg = doc[i]
    pix = pg.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    p = pathlib.Path(f"/tmp/pg{i}.png"); pix.save(p)
    return p

def clean(path):
    """Deskew-lite + binarise + despeckle, tuned for 16th-c. letterpress."""
    import cv2, numpy as np
    im = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    im = cv2.fastNlMeansDenoising(im, None, 12, 7, 21)
    im = cv2.resize(im, None, fx=1.0, fy=1.0, interpolation=cv2.INTER_CUBIC)
    im = cv2.adaptiveThreshold(im, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 41, 15)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    im = cv2.morphologyEx(im, cv2.MORPH_OPEN, k)
    out = path.with_name(path.stem + "_clean.png")
    cv2.imwrite(str(out), im)
    return out

def ocr(img, langs=LANGS, psm=6):
    r = subprocess.run(["tesseract", str(img), "stdout", "-l", langs, "--psm", str(psm)],
                       capture_output=True, text=True)
    return r.stdout

POST = [(re.compile(r"[ﬁﬀﬃﬂﬄ]", re.U), lambda m: {"ﬁ":"fi","ﬀ":"ff","ﬃ":"ffi","ﬂ":"fl","ﬄ":"ffl"}[m.group(0)]),
        (re.compile(r"(?<=\b)f(?=[ilmnoprstu][a-z])", re.I), lambda m: "s"),   # long-s repair
        (re.compile(r"(\w)-\s*\n\s*(\w)"), lambda m: m.group(1)+m.group(2)),    # dehyphenate
        (re.compile(r"[ \t]+"), lambda m: " "),
        (re.compile(r"\n{2,}"), lambda m: "\n")]
def postprocess(t):
    for rx, f in POST: t = rx.sub(f, t)
    return t.strip()

def score(txt):
    """crude readability metric: share of alphabetic chars inside 3+ letter words"""
    w = re.findall(r"[A-Za-z]{3,}", txt)
    letters = sum(len(x) for x in w)
    n = max(1, len(re.sub(r"\s", "", txt)))
    return round(100*letters/n, 1)

if __name__ == "__main__":
    pdf, outp = sys.argv[1], sys.argv[2]
    pages = [int(x) for x in sys.argv[3:]] or [0]
    doc = pymupdf.open(pdf)
    for i in pages:
        raw = ocr(render(doc, i))
        img_clean = clean(pathlib.Path(f"/tmp/pg{i}.png"))
        ocrd = postprocess(ocr(img_clean))
        layer = postprocess(doc[i].get_text())
        pathlib.Path(f"{outp}.p{i}.ocr.txt").write_text(ocrd)
        print(f"--- page {i}: embedded-layer score {score(layer):5.1f} | raw OCR {score(raw):5.1f} | cleaned OCR {score(ocrd):5.1f}")
        print("    embedded:", " ".join(layer.split())[:220])
        print("    our OCR :", " ".join(ocrd.split())[:380])

# --- legacy-print normaliser (added after first trials on Cattan 1591) -----------------
# The killer for 16th-century English isn't accuracy, it's that the OCR reads the
# long-s 'ſ' as 'f', so 'fignify'/'gofree'/'paffed' are unreadable and unsearchable.
_LIG = {"æ":"ae","œ":"oe","ĳ":"ij","ø":"o","ð":"d","þ":"th","ɣ":"g","‑":"-","–":"-","—":"-"}
def normalise_legacy(t):
    t = t.lower()
    for k,v in _LIG.items(): t = t.replace(k,v)
    # u/v in old prints: 'vnto'->'unto','vhich'->'which'
    t = re.sub(r"\bv([aeiou])", r"u\1", t)
    t = re.sub(r"([bcdfghjklmnpqrtstwxyz])v(?=[aeiou])", r"\1u", t)
    # ſ already printed as s by tesseract on frk; fix the residual 'f'->'s' inside words
    t = re.sub(r"(?<=[a-z])f(?=[ailo][a-z])", "s", t)
    t = re.sub(r"\bf(?=t\b|l\b)", "s", t)
    t = t.replace("ſ","s").replace("ﬁ","fi").replace("fl","fl")
    t = re.sub(r"(\w)-\s+(\w)", r"\1\2", t)   # de-hyphenate across line breaks
    t = re.sub(r"\b(?:t[ht]?|yt|yt)\b(?=\s)", "it", t) if False else t
    t = re.sub(r"[^a-z0-9\s.,;:'()\-\n]", " ", t)
    t = re.sub(r"[ \t]+", " ", t); t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()
