#!/usr/bin/env python3
"""Build kb/question_inventory.json: every answerable sub-question the old casebooks name,
with (a) the houses to consult, (b) which attribute of the figure answers it, (c) the source.

Sources combined:
  - Alfagini, Quaestiones Geomantici (Fasciculus geomanticus 1704) - Latin, per-question rules
  - Libro de los juysios de calatarama, 'universal chapter' (via Finan's thesis) - per-house question lists
  - Cattan, The Geomancie (1608) - per-figure motion rulings
  - Shatpanchashika / Prasna Marga (horary) - used ONLY for the shape of the question list, not for method
"""
import json, re, pathlib, pymupdf, collections

ROOT = pathlib.Path(".")
inv = collections.OrderedDict()

# ---------- 1. Latin quaestiones: harvest every "De ... / An ..." heading near a QUAESTIO token
d = pymupdf.open(str(ROOT / "corpus/raw/ia/fasciculus_geomanticus_1704.pdf.pdf"))
TOP = re.compile(r"^\s*((?:De|An|Utrum|Quomodo|Qualiter|Quantitas|Cur)\s+[A-Za-zà-ÿæœ'’\-\s,]{5,80}?)[.?!]?\s*$")
lat = []
for i in range(438, 690):
    if i >= d.page_count: break
    for line in d[i].get_text().split("\n"):
        m = TOP.match(line.strip())
        if m:
            t = re.sub(r"\s+", " ", m.group(1)).strip(" .,:;-")
            t = t.replace("De ", "De ").strip()
            if len(t) > 12 and not re.search(r"(geomantia|quaestio|caput|liber|finis)", t, re.I):
                lat.append({"topic_latin": t, "leaf_pdf": i + 1})
seen = set(); latu = []
for x in lat:
    k = x["topic_latin"].lower()[:40]
    if k in seen: continue
    seen.add(k); latu.append(x)
print("Latin question headings:", len(latu))

# ---------- 2. Calatarama: numbered question lists per house, from the thesis
th = (ROOT / "corpus/raw/calatarama_example_questions_175_225.txt").read_text(errors="replace")
th = re.sub(r"<<<PAGE \d+>>>", " ", th)
th = re.sub(r"\s+", " ", th)
cal = []
for m in re.finditer(r"(?i)(questions? (?:of|concerning|assigned to) the (first|second|third|fourth|fifth|sixth|"
                     r"seventh|eighth|ninth|tenth|eleventh|twelfth) house)(.{0,2200})", th):
    house = m.group(2).lower()
    body = m.group(3)
    items = re.findall(r"\((\d{1,3})\)\s*([A-Za-z][^;.]{14,150})", body)
    nums = re.findall(r"(?:question|asks? whether|asks? if)\s+([a-z][^;.?]{14,150})", body, re.I)
    for n, q in items: cal.append({"house": house, "no": int(n), "question": q.strip()})
    for q in nums[:12]: cal.append({"house": house, "no": None, "question": q.strip()})
print("Castilian question lines:", len(cal))

# ---------- 3. Cattan: which figure-in-house answers what
cat = json.loads((ROOT / "kb/cattan_motus_bank.json").read_text())["records"]
print("Cattan motion rulings:", len(cat))

# ---------- 4. the Prasna taxonomy (question SHAPE only)
pr = (ROOT / "corpus/raw/ia2/indian_horary_shatpanchashika.txt").read_text(errors="replace")
pr = re.sub(r"\s+", " ", pr)
chaps = []
for m in re.finditer(r"(?i)(Chapter \d+)\s+([A-Z\-]{4,22})\s*(?:Verses\s+\d+\s*)?(.{0,900}?)(?=Chapter \d+|\Z)", pr):
    subs = re.findall(r"(\d{1,2})\s*[.,]?\s*([A-Z][a-z][^.]{14,150}?)[.;]", m.group(3))
    chaps.append({"chapter": m.group(1), "name": m.group(2),
                  "questions": [{"no": int(n), "q": t.strip()} for n, t in subs][:14]})
print("Prasna chapters:", len(chaps))

# ---------- 5. the geomantic answer-slot table: which attribute answers which kind of sub-question
SLOTS = {
 "identity_of_person":  {"read": "figure in the house of the quesited -> Table 4 'Demonstration and Disposition of Men' + 'Figures of Bodies of Men and Women'",
                         "source": "Calatarama Table 4 (thesis pp.103-104)"},
 "age_stage":           {"read": "same table, 'Ages of Men'", "source": "Calatarama Table 4"},
 "direction_to_look":   {"read": "'Direction' of the quesited figure (North/Mideast/Midwest/West)", "source": "Calatarama Table 4"},
 "place_type":          {"read": "'Place' of the quesited figure (rivers, locked places, towers, dark place/desert, streets)", "source": "Calatarama Table 4"},
 "distance_quantity":   {"read": "'Numbers' of the quesited figure; for travel also the points of the figure", "source": "Calatarama Table 4 + f.12"},
 "matter_substance":    {"read": "'Metals', 'Stones', 'Colour', 'Flavour', 'Scent'", "source": "Calatarama Table 4"},
 "occupation_class":    {"read": "'Sciences' + 'Meaning in the events and dispositions of men' + 'Peoples'", "source": "Calatarama Table 4"},
 "body_part_health":    {"read": "'Parts of the Body' of the figure in I or VI", "source": "Calatarama Table 4"},
 "recovery_or_loss":    {"read": "motion: intrans/entering keeps and recovers; exiens/leaving loses", "source": "Calatarama f.10v; Alfagini 'De re amortisa'"},
 "hidden_cause":        {"read": "figura extracta: add the two houses the rule names (often IV & V, or the house & its neighbour)",
                         "source": "Alfagini Quaestiones (leaf 465-466); Calatarama f.39v"},
 "strength_of_answer":  {"read": "consent of the four angles (I, IV, VII, X) + the 15th", "source": "Alfagini 'quatuor anguli sint fortuna' (leaf 464)"},
 "when":                {"read": "unit from the figure in the quesited house, count from points", "source": "Calatarama ch.6 f.12"},
 "who_else_involved":   {"read": "company pairs (1-2,3-4,5-6,7-8,9-10,11-12); odd=present, even=future", "source": "Serena Powers / medieval practice"},
 "legal_or_moral_note": {"read": "context can invert the figure's native quality", "source": "Calatarama f.11"},
}
out = {
 "_meta": {"built": "scripts/build_question_inventory.py",
   "purpose": ("An inventory of what a cast can actually be asked, with the answer-slot each source uses. "
               "The engine (engine/questions.py) reads this to tell you what to look at for a given sub-question."),
   "slot_table": SLOTS,
   "caveat": ("The Prasna/horary chapter lists are used only for the SHAPE of the question inventory. "
              "Their answers are computed from lunar mansions and planetary combinations, not from figures; "
              "do not paste a horary combination into a geomantic chart.")},
 "latin_quaestiones": latu,
 "castilian_questions_by_house": cal[:400],
 "cattan_motion_rulings": cat,
 "prasna_question_taxonomy": chaps,
}
pathlib.Path("kb/question_inventory.json").write_text(json.dumps(out, indent=1))
print("\nwrote kb/question_inventory.json")
print("sample Latin:", [x["topic_latin"] for x in latu[:12]])
print("sample Castilian:", [(c["house"], c["question"][:60]) for c in cal[:5]])
for ch in chaps[:3]:
    print(f"  Prasna {ch['chapter']} [{ch['name']}]:", [q["q"][:52] for q in ch["questions"][:4]])
