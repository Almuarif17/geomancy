#!/usr/bin/env python3
"""Parse Appendix 1 of the Calatarama thesis -> kb/calatarama_grid.json

Appendix 1 is the medieval manual's own table of "the meaning of the geomantic figures in the
Nth house" for houses II-XII (ff. 26v-... of the manuscript). This is the highest-value asset in
the whole corpus for mining specifics: a figure x house grid, in a scholarly translation, with
folio references - and it is typed text, so nothing here depends on OCR quality.
"""
import json, re, pathlib, unicodedata as _ud


def _norm(x: str) -> str:
    x = _ud.normalize("NFKD", x).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", x.lower()).strip()
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
hdr = re.compile(r"Meaning of (?:the )?[Gg]eomantic (?:[Ff]igures|house) in the ([IVX]+)\s*House(\s*\(f\.\s*([0-9a-zA-Z.\-]+)\))?")  # VIII and X are headed irregularly; a strict pattern silently skipped both tables
starts = [(m.group(1), m.group(3) or "", m.start()) for m in hdr.finditer(t)]
print("sections found:", [(h, f) for h, f, _ in starts])
ent = re.compile(r"(?<=\s)\[([A-Za-z\u00c0-\u017f ]{2,26})\]\s*(.+?)(?=\s\[|$)")   # transcriber insertions like "hear[are] not equal" sit mid-sentence; whitespace before the
# canonical names resolve to themselves; the manuscript's Romance spellings alias in.
# The original map listed only variants, so "[Carcer]" - how 11 of the 12 tables label the figure -
# matched nothing and the row vanished. Now every unresolved label is reported instead of dropped.
CANON = ["Via", "Populus", "Conjunctio", "Caput Draconis", "Cauda Draconis", "Tristitia",
         "Laetitia", "Carcer", "Amissio", "Acquisitio", "Fortuna Major", "Fortuna Minor",
         "Albus", "Rubeus", "Puella", "Puer"]
_BY_NORM = {ALIAS and _norm(k): v for k, v in ALIAS.items()} if False else {_norm(k): v for k, v in ALIAS.items()}
_BY_NORM.update({_norm(c): c for c in CANON})
unmatched: dict = {}

# The thesis quotes the universal tables in its commentary as well as printing them in Appendix 1, so
# a house can appear as a section more than once and the slices cut each other (that is what truncated
# house XII and dropped house I on 2026-09-17). Parse every occurrence and keep the richest one.
best = {}
for i, (house, folio, a) in enumerate(starts):
    b = starts[i + 1][2] if i + 1 < len(starts) else len(t)
    body = t[a:b]
    # Appendix 2 (the raw transcription, full of editorial square brackets) follows the tables; without
    # this bound the last figure of house XII swallows its opening paragraphs.
    cut = body.find("Appendix 2:")
    if cut > 0:
        body = body[:cut]
    rows = {}
    last = None
    for m in ent.finditer(body):
        nm = m.group(1).strip()
        fig = ALIAS.get(nm) or _BY_NORM.get(_norm(nm))
        txt = re.sub(r"\s*\d{2,4}\s*$", "", m.group(2).strip(" .;"))
        txt = re.sub(r"\.\s*(?:\.\s*){2,}", ".", txt).strip(" .;")
        if fig is None:
            # Not a figure label. In this translation square brackets also mark the transcriber's
            # insertions ("the hear[are] not equal"), so the fragment belongs to the row above; keep
            # the text AND count the label, so a genuinely unknown figure name still surfaces.
            unmatched[nm] = unmatched.get(nm, 0) + 1
            if last and last in rows and len(nm) < 14:
                rows[last][-1] = rows[last][-1].rstrip(". ") + " [" + nm + "] " + txt
            continue
        if not txt or len(txt) < 12:
            continue
        rows.setdefault(fig, []).append(txt)
        last = fig
    rows = {k: " ".join(v)[:600] for k, v in rows.items()}
    if len(rows) > len(best.get(house, (None, {}))[1]):
        best[house] = (folio, rows)
grid = {h: {"folio": f, "entries": r} for h, (f, r) in best.items() if r}

for h, v in sorted(grid.items(), key=lambda x: ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"].index(x[0])):
    print(f"  house {h:4s} ({len(v['entries'])} figures) f.{v['folio']}")
OUT.write_text(json.dumps({"_meta": {"unmatched_labels": dict(sorted(unmatched.items(), key=lambda x: -x[1])),
               "unmatched_note": "bracketed labels the parser could not resolve to a figure; empty means every row in the appendix tables was claimed",
         "source": "Libro de los juysios de calatarama, universal chapter tables, "
    "as translated in Appendix 1 of A.J.C. Finan, 'The Book of the Judgements of Calatarama' (Univ. of Toronto, 2023)",
    "why": "a figure x house ruling grid from the 13th-15th c. Arabic-derived tradition; typed translation, no OCR loss",
    "usage": "quote with the folio; it is a translation of one manuscript, not a universal rule"},
    "grid": grid}, indent=1))
print("wrote", OUT)
