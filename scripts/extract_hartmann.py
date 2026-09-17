#!/usr/bin/env python3
"""Franz Hartmann, 'The Principles of Astrological Geomancy' (1889) -> kb/hartmann_casebook.json

Two assets: (1) the figure table incl. his number/element/sign and the parentage+witness rules;
(2) the appendix of 2,048 answers = 8 attainable Judges x 16 co-significators x 16 questions.
The text is 19th-century typeset, so the layer is legible; OCR still garbles glyphs and some
figure names, which we repair with a fuzzy matcher and record verbatim alongside.
"""
import json, re, pathlib, difflib, collections

SRC = pathlib.Path("corpus/raw/ia/principles_astrological_geomancy_1889.txt.txt")
OUT = pathlib.Path("kb/hartmann_casebook.json")
raw = SRC.read_text(errors="replace")
txt = re.sub(r"-\n", "", raw)
txt = re.sub(r"\s+", " ", txt)

JUDGES = ["Acquisitio", "Amissio", "Fortuna major", "Fortuna minor", "Populus", "Via",
          "Conjunctio", "Carcer"]
FIGS = ["Acquisitio", "Amissio", "Fortuna major", "Fortuna minor", "Populus", "Via", "Conjunctio",
        "Carcer", "Laetitia", "Tristitia", "Puella", "Puer", "Albus", "Rubeus", "Caput Draconis",
        "Cauda Draconis"]
QUESTIONS = {
 1: "Will the person inquired about have a long life?",
 2: "Will he become rich?",
 3: "Will the proposed undertaking succeed?",
 4: "How will the undertaking end?",
 5: "Is the expected child a boy or a girl?",
 6: "Are the servants honest?",
 7: "Will the patient recover?",
 8: "Will the lover succeed?",
 9: "Will the inheritance be obtained?",
 10: "Will the lawsuit be gained?",
 11: "Will the desired position be had?",
 12: "What will be the kind of death?",
 13: "Will the expected letters arrive?",
 14: "Will the voyage be fortunate?",
 15: "Will good news arrive?",
 16: "Will the adversary be conquered?",
}
def near(s):
    s = re.sub(r"[^A-Za-z ]", "", s).strip().lower()
    best, score = None, 0.0
    for f in FIGS:
        r = difflib.SequenceMatcher(None, s, f.lower()).ratio()
        if r > score: best, score = f, r
    for pat, name in [(r"pney|boy", "Puer"), (r"alhiis|white head", "Albus"),
                      (r"ruheus|redhead", "Rubeus"), (r"laetit|lzetit", "Laetitia")]:
        if re.search(pat, s): best, score = name, max(score, 0.9)
    return best, round(score, 2)

# --- part 1: figure table
figs = {}
for f in FIGS:
    m = re.search(re.escape(f) + r"[\.,].{0,460}?(?:its number (\d{1,2})|number (\d{1,2}))", txt, re.I)
    if m:
        blk = m.group(0)
        figs[f] = {
            "number": int(m.group(1) or m.group(2)),
            "element": (re.search(r"element is (\w+)", blk) or [None, None])[1] if re.search(r"element is (\w+)", blk) else None,
            "gloss": re.sub(r"\s+", " ", blk[:200]).strip(),
        }
rules = [x.strip() for x in re.findall(
    r"(?:A (?:good|bad) figure made of[^.]*\.|If the (?:first |two )?(?:witness|judge)[^.]*\.)", txt)]

# --- part 2: the answer appendix
start = txt.find("There have been")
ap = txt.find("QUESTIONS. 1. Will the person")
cell = re.compile(r"(?:\bor\b|\.|\s)\s*(" + "|".join(re.escape(j) for j in JUDGES) + r")\b", re.I)
blocks = []
for m in re.finditer(r"(?i)\b(" + "|".join(JUDGES) + r")\b\.?(\s*[^.]{0,20})?", txt[ap:ap+120000]):
    pass
# Walk the appendix; a "judge" section starts at the INDEX page-name, and inside it
# each co-significator block is introduced by that figure's name, then 16 numbered answers.
tail = txt[ap:]
cur_j, cur_f, answers = None, None, {}
rows = []
tokens = re.finditer(
    r"(?P<sec>\b(?:" + "|".join(JUDGES) + r")\.(?![a-z]))"
    r"|(?P<fig>\b(?:Acquisitio|Amissio|Fortuna major|Fortuna minor|Populus|Via|Conjunctio|Carcer|Laetitia|Tristitia|Puella|Puer|Alhiis|Albus|Ruheus|Rubeus|Caput Draconis|Cauda Draconis)\b)"
    r"|(?P<ans>(?:^|\s)(?P<n>\d{1,2})\.\s(?P<t>[^.!?]{4,150}?[.!?]))", tail)
for m in tokens:
    if m.group("sec"):
        nxt = tail[m.end():m.end()+260]
        fj, sc = near(nxt.split(".")[0] if nxt else "")
        cur_j = re.sub(r"[^A-Za-z ]", "", m.group("sec")).strip().title()
        if cur_j.lower().startswith("fortuna"): cur_j = cur_j.title()
    elif m.group("fig"):
        nm = m.group("fig").strip()
        nm = {"Alhiis": "Albus", "Ruheus": "Rubeus"}.get(nm, nm)
        if nm.lower().startswith("fortuna"): nm = nm[:8] + nm[8:].title()
        cur_f = nm
    elif m.group("ans"):
        n = int(m.group("n"))
        if n in QUESTIONS and cur_j and 1 <= len(rows) + 1:
            rows.append({"judge": cur_j, "cofigure": cur_f, "q": n,
                         "question": QUESTIONS[n], "answer": m.group("t").strip()})
seen, uniq = set(), []
for r in rows:
    k = (r["judge"], r["cofigure"], r["q"])
    if k in seen or not r["judge"]: continue
    seen.add(k); uniq.append(r)
OUT.write_text(json.dumps({
 "_meta": {"source": "Franz Hartmann, The Principles of Astrological Geomancy (London, 1889), "
                     "appendix '2,048 Answers to Questions'",
           "identifier": "b24884145",
           "method_note": ("Hartmann's own casting rule is NOT the classical shield: he takes the total "
                           "points of the punctuation, divides by 12, and the remainder is the house of the "
                           "Judge ('there have been 152 points ... there will still remain 8; 8 is therefore "
                           "in this case the Judge'). Read his answers as an appendix oracle keyed to figures, "
                           "not as the medieval judgment."),
           "cells_recovered": len(uniq), "of_2048": "partial - the OCR breaks some section boundaries",
           "questions": QUESTIONS},
 "figure_table": figs, "composition_rules": rules, "answers": uniq}, indent=1))
print("figures with numbers:", len(figs), "| composition rules:", len(rules), "| answer cells:", len(uniq))
print("by judge:", collections.Counter(r["judge"] for r in uniq).most_common())
for r in uniq[:6]: print("   ", r["judge"], "/", r["cofigure"], "Q", r["q"], "→", r["answer"][:70])
