#!/usr/bin/env python3
"""Parse Appendix 1 of the Calatarama thesis -> kb/calatarama_grid.json

Appendix 1 is the medieval manual's own table of "the meaning of the geomantic figures in the
Nth house" for houses II-XII (ff. 26v-... of the manuscript). This is the highest-value asset in
the whole corpus for mining specifics: a figure x house grid, in a scholarly translation, with
folio references - and it is typed text, so nothing here depends on OCR quality.
"""
import json, re, pathlib
SRC = pathlib.Path("corpus/raw/cal_appendices_translation.txt")
OUT = pathlib.Path("kb/calatarama_grid.json")
t = SRC.read_text(errors="replace")
t = re.sub(r"<<<PAGE \d+>>>", " ", t)
t = re.sub(r"\s+", " ", t)

ALIAS = {"Itisiçio": "Acquisitio", "Itisicio": "Acquisitio", "Emysio": "Amissio", "Emijio": "Amissio",
         "Populo": "Populus", "Liticia": "Laetitia", "Leticia": "Laetitia", "Tristicia": "Tristitia",
         "Carçel": "Carcer", "Carcel": "Carcer", "Rubea": "Rubeus", "Puela": "Puella", "Puer": "Puer",
         "Alua": "Albus", "Albus": "Albus", "Congregacion": "Conjunctio", "Congregacio": "Conjunctio",
         "Conjunctio": "Conjunctio", "Forfuna Mayor": "Fortuna Major", "Fortuna Mayor": "Fortuna Major",
         "Forfuna Menor": "Fortuna Minor", "Fortuna Menor": "Fortuna Minor", "Via": "Via",
         "Cabeça del Dragon": "Caput Draconis", "Cabeca del Dragon": "Caput Draconis",
         "Cola del Dragon": "Cauda Draconis"}

# a section header: "Meaning of the Geomantic Figures in the II House (f. 26v)"
hdr = re.compile(r"Meaning of the [Gg]eomantic [Ff]igures in the ([IVX]+)\s*House\s*(\(f\.\s*([\dvxrxiv]+)\))?")
starts = [(m.group(1), m.group(3) or "", m.start()) for m in hdr.finditer(t)]
print("sections found:", [(h, f) for h, f, _ in starts])
ent = re.compile(r"\[([A-Za-zçÇáéíóúñ ]+?)\]\s*(.+?)(?=\s\[|$)")
grid = {}
for i, (house, folio, a) in enumerate(starts):
    b = starts[i + 1][2] if i + 1 < len(starts) else len(t)
    body = t[a:b]
    # cut off trailing thesis prose (footnotes/next appendix)
    stop = re.search(r"(?i)(See |footnote|Appendix \d|chapter \d)", body)
    if stop: body = body[:stop.start()]
    rows = {}
    for m in ent.finditer(body):
        nm = m.group(1).strip()
        fig = ALIAS.get(nm)
        txt = m.group(2).strip(" .;")
        if not fig or len(txt) < 12:
            continue
        rows.setdefault(fig, []).append(txt)
    if rows:
        grid[house] = {"folio": folio, "entries": {k: " ".join(v)[:600] for k, v in rows.items()}}
for h, v in grid.items():
    print(f"  house {h:4s} ({len(v['entries'])} figures) f.{v['folio']}")
OUT.write_text(json.dumps({"_meta": {"source": "Libro de los juysios de calatarama, universal chapter tables, "
    "as translated in Appendix 1 of A.J.C. Finan, 'The Book of the Judgements of Calatarama' (Univ. of Toronto, 2023)",
    "why": "a figure x house ruling grid from the 13th-15th c. Arabic-derived tradition; typed translation, no OCR loss",
    "usage": "quote with the folio; it is a translation of one manuscript, not a universal rule"},
    "grid": grid}, indent=1))
print("wrote", OUT)
