# PLAN — recovering the buried layer of geomancy

Usman — this is the method I designed and then ran, not a proposal. Sections 1-3 are the plan,
4-6 are what it produced, 7 is what it cannot yet do.

## 0. The thesis I am working to

Everything you want — *why*, *who*, *where*, *how to check the alternative*, *how to calculate the
movement* — is already inside the cast. The art is not adding mysticism; it is that **a cast is a
small finite structure (16²⁴ = 65,536 states) and every question you can ask of it has an exact,
enumerable answer.** Modern books give you a dictionary (figure × house). The older and Arabic
sources give you **machinery**: gates, traces, sums, remainders, parents, motion, and elections.
The plan is to recover the machinery, save it, and make it computable — so that "this cast has
hidden meaning X" is always traceable to a named rule in a named folio, and its rarity is known.

## 1. Where the rare knowledge actually sits (source map)

Tiered by expected yield per hour of work. Ticks = already acquired into `corpus/`.

| Tier | Body of material | Specific targets | How obtained | Yield |
|---|---|---|---|---|
| A ✓ | **Arabic-derived Castilian manual**, with a scholarly translation of its tables | *Libro de los juysios de calatarama* (= kitāb al-raml), in A.J.C. Finan, *The Book of the Judgements of Calatarama* (Univ. Toronto, 2023, open thesis PDF, 400pp) | direct PDF fetch; typed text layer, **no OCR needed** | the whole interpretation *procedure*: 10 steps, validity gate, timing, day/hour figures, triplicity routing, figure×house ruling tables |
| A ✓ | **Classical Arabic `ilm al-raml** | W. van Binsbergen, *The astrological origin of Islamic geomancy* (1996, 63pp PDF) incl. his translation of al-Zanātī, *Kitāb al-faṣl fī uṣūl ʿilm al-raml* | quest-journal PDF | the derivation algebra in the Arabic form; the "only 8 figures can be Judge" theorem; 16th figure = houses **I + XV** |
| B ✓ | **English Renaissance practice** | Cattan, *The Geomancie* (1591 and 1608, archive.org) ; Heydon, *Theomagia* (1663) | IA `_djvu.txt` + own OCR | figure-by-figure **motion through the houses** (book III), stopping figures, "re-cast an hour later" |
| B | **Latin compendia** | *Opus geomantiae completum* (1638); Petrus de Abano, *Modo iudicandi quaestiones*; Gerard of Cremona, *Si quis per artem*; *Estimaverunt Indi*; Agrippa, *De occulta philosophia* II.48-51 | IA (some acquired); Tannery, *Mémoires scientifiques* II (cited edition of the Latin texts) | the "aspects/arrows/suffrages" family; the *De fortuna et infortunio figurarum* gradings |
| C | **Maghrebi/Sudanese and Indian Ocean manuals** | al-Būnī lineage; *Shams al-maʿārif* geomancy chapters; Hausa *fansa*/*kaya*; Malagasy *sikidy*; Sri Lankan *ramalama* / *meka* | need **Arabic-script OCR** (`tesseract -l ara`, installed) + Wikitext/manuscript repositories (Qatar Digital Library, ISAC al-Furqan, BnF Gallica, Süleymaniye) | per-figure "answering" verses; the *ṭarsīs*/magic-square pairing method (figure+figure → a *new* figure to answer a sub-question) |
| C | **Ifá** (the binary cousin) | 16 *ojú dù* and the *ewe* (taboo)/*ebo* (prescription)/*osanyin* (herb) lists per odu | Bascom, *Sixteen Cowries*; Abímọ̀lá, *Ifà: An Exposition*; Odu Ifá corpus sites | the "personal detail" register — warnings, taboos, visitors, specific dangers, which geomancy alone never states |
| D | **Modern synthesis** (for cross-checking, not for discovery) | Skinner, *The Oracle of Geomancy*; Pennick; Greer's *Intermediate Techniques*; KitchenToad's evil-eye/crossed-conditions essay; Digital Ambler (Conant) series | web | names techniques we must then find in a primary source before trusting |

**Rule I keep to:** a technique enters `kb/techniques.yaml` with (a) the rule as an algorithm,
(b) the source that states it, (c) a confidence. If a source only *names* a technique, it is stored
as `NAMED_ONLY` and the engine refuses to compute it. That single rule is what makes this stack
different from the usual geomancy material.

## 2. Extraction procedure (why OCR, and what it is really for)

Measured, not assumed:

- IA's own `_djvu.txt` on Cattan 1591 recovers **4 of 11** words I could check on a page I read by
  eye; my tesseract pass (Fraktur+English) recovers **8 of 11**. So IA's layer is *not* trustworthy
  for blackletter, and neither is one OCR pass.
- Binaries, upscaling and denoising were all *worse* than raw 400 dpi greyscale — the page is a dense
  two-ink layout, and enhancement invents letters.
- Word-level confidence filtering (`tsv`, conf ≥70) removes half the words and keeps recall roughly
  unchanged: it converts noise into fewer, safer hits.
- Therefore the OCR stage is a **locator, not an edition**: `scripts/ocr_ingest.py` renders each page,
  runs OCR, scores it against a keyword set, keeps the better of (embedded layer, OCR) per page, and
  writes an `INDEX.md` that ranks pages. You then read the page image for anything you intend to quote.
- Anything already typed (the Toronto thesis, van Binsbergen's PDF) is preferred over any OCR:
  the 142 figure×house rulings in `kb/calatarama_grid.json` came from typed translation, zero OCR loss.

**Normalisation that matters for early print:** long-s (`ſ`→s), `u/v` interchange, de-hyphenation
across line-breaks, and the abbreviation marks. In `corpus/raw` the un-normalised files are kept
untouched; normalisation lives in the parsers so the raw evidence is never mutated.

## 3. Validation protocol (the part that catches me being wrong)

Three independent checks, all automated (`engine/test_deep_read.py`):

1. **Reproduce a real cast.** I count the gems out of your two app screenshots myself and require
   the engine to regenerate houses V-XVI from the four Mothers — 16/16 and 15/15. This is what killed
   my own invented "crossed nephew" rule: the app was right, I was wrong, and the app's two charts
   disagreed in exactly one place, which is what made it decidable.
2. **Enumerate the whole space.** All 65,536 casts: Judge is even-in-points always; a cast can never
   hold 16 distinct figures; Via Puncti reaches a root figure in 32,768/32,768 cases where the
   Judge's head is single; `f + f = Populus` always (which is *why* "Judge + left witness" is a
   degenerate 16th figure and the sources' `I + XV` is the real one).
3. **Cross-source agreement.** Where two traditions state the same mechanism differently
   (Puer/Puella patterns; which planet rules which figure), the KB records the conflict and the
   engine prints it instead of picking silently.

## 4. What the plan produced (already usable)

`kb/`
- `figures.yaml` — 16 figures: pattern, points, Arabic name+gloss, Ifá odu (flagged as comparison
  only), element/planet, quality, incoming/outgoing, humours, time-unit, plus the extracted
  Calatarama attribute rows (place, direction, colour, metal, number, letters, peoples, sciences,
  age of man, body part, physique) for the 6 figures where the translation preserves them; **two
  named conflicts** (Puer/Puella pattern; planetary attribution table) recorded, not resolved.
- `houses.yaml` — the 12 houses + court, with the Calatarama's own house table (its "significations",
  gender, element, colour, body part) and `question_to_house` for topic routing.
- `techniques.yaml` — 19 rare techniques as algorithms with provenance and confidence, including
  `NAMED_ONLY` entries for the ones I could not source a procedure for.
- `calatarama_grid.json` — **142 figure×house rulings** (ff. 24v-61v), the medieval "what exactly
  does this mean here" text, typed translation, folio-tagged.
- `cattan_motus_bank.json` — 24 motion rulings (figure passing I→Nth house), English Renaissance.
- `priors.json`, `perfection_priors.json`, `calibration.json` — the exact finite population:
  attainable figures per house, surprisal in bits, per-question-house distribution of the perfection
  modes, the oracle's optimism measured.

`engine/`
- `deep_read.py` — builds the cast, then runs validity gates, motus, parentage, perfection,
  triplicities (both systems), Via Puncti, projection of the points, Part of Fortune, humours,
  timing (both methods), who/where/when, the Arabic/Ifá cross-read, and the medieval ruling text.
- `elections.py` — day/hour gate with **unequal (temporal) hours** computed from sunrise/sunset,
  the Calatarama f.5 planetary table, and "which weekday would make this cast legal" ranking.
- `audit_chart.py` — feed it any chart (app or book) and it tells you which rule each house came
  from and whether the drawing obeys it. This is how you check *other* sources, and how I checked
  yours. `test_deep_read.py` — 12 checks incl. the exhaustive ones.

`scripts/`
- `find_sources.py` (archive discovery), `acquire.py` (fetch + quality-score), `ocr_ingest.py`
  (the OCR locator), `extract_cattan_motus.py`, `extract_calatarama_grid.py`, `mine.py`
  (OCR-noise-tolerant passage search — this is what actually found Cattan's recast rule).

## 5. The "genius-level detail" question, answered honestly

You asked for the kind of thing only a genius knows — *a visitor is coming; beware of a knife* —
from a single cast. Two separate things are needed and I have done the first:

1. **A register of concrete particulars per figure.** That exists: the Calatarama's figure table
   (place, direction, metal, colour, peoples, science, age, body part, physique) and its per-house
   rulings; Cattan's motion rulings; Agrippa's stone/herb/planet correspondences. Wired in: the
   engine's `who`/`where`. This is how "who" and "where" are traceable rather than invented.
2. **A danger/prescription register** (knife, poison, water, enemies, what to offer). Geomancy's own
   catalogues give *classes* (Rubeus = violence, Carcer = bonds, Cauda = poison/ending), but the
   "beware of a knife" granularity lives in **Ifá** (each odu's *ewe* taboos and *ebo* prescriptions)
   and in the *ṭarsīs* magic-square techniques of the Arabic manuals. That is Tier C, and I have
   deliberately **not** fabricated a mapping into `engine/`. The `ifa_odu` column is a structural
   correspondence from one modern author who himself warns the two oracles do not share semantics;
   the engine prints that warning rather than pretending.

So: the detail engine is real, and the register it needs is in Tier C. That is the next acquisition.

## 5b. Second pass, completed after the first draft of this plan

Harvest went from capped queries to a full paginated sweep (1,604 unique → 259 relevant, each with
text-layer / borrow / scan status), and the corpus gained: Agrippa's 4th book *and* its geomancy
treatise (1655, 1783), the *Fasciculus geomanticus* (1704) with **Alfagini's Quaestiones** (42 rules
re-OCR'd by me), four German *Geomantia* prints, Hartmann's **2,048-answer** casebook with its
non-shield casting rule, Persian *Kitāb-i Sorkhāb* and McGill's *Nuskhah-i raml*, the Lal Kitab
originals, the horary question literature (Prasna Marga, Shatpanchashika) for **question shape only**,
the Amazulu bones corpus for the **named-particulars format**, and Jean de la Taille's French
treatise for its **tie-break rule**. The engine grew `questions.py` (35 leaf-cited sub-questions,
turned-chart test, figura extracta, passage test, la Taille tie-break) and the checks grew to 24.
Two things were deliberately *not* used: four in-copyright uploads (deleted, named) and the Hindi
"Ramal" books, which are the Book-of-Fate lookup genre, not figure geomancy.

## 6. Roadmap (in order of payoff)

1. **Complete the figure table.** The thesis prints 6 of 16 attribute columns. Get the manuscript
   facsimile / a fuller edition (Charmasson, *Recherches sur une technique divinatoire*, the primary
   modern edition of this text family) and fill the other 10 → every `who/where` cell stops being empty.
2. **Arabic OCR pass.** Run `ocr_ingest.py --lang ara` on Shams al-maʿārif-type geomancy sections and
   the *sikidy*/*fansa* literature; mine for (a) the **hidden figure** procedure (named, unresolved),
   (b) the **ṭarsīs** pairing-for-sub-questions method, (c) the **suffrages/arrows**.
3. **Ifá register.** Build `kb/ifa_ewe.json`: odu → taboos, dangers, prescriptions, orisha, place,
   herb. Then, and only then, a documented rule for when a geomancer may consult it.
4. **Statistical layer.** Extend `build_priors.py` to per-house, per-mode conditional tables
   (e.g. P(XIII = Rubeus | Judge = Populus)), and a "which questions is this cast actually about"
   score — the cast's information-theoretic profile. Rarely done for geomancy by anyone.
5. **Timing precision.** Calatarama gives two timing methods and one ambiguity (which unit).
   Test both on the dated charts we can reconstruct, and record failure rates like a scientist.

## 7. What I refuse to claim

- That these techniques are "true". They are a precise, inherited *reading procedure*; the engine
  makes that procedure auditable, nothing more.
- That a figure's meaning is fixed. The Calatarama's own principle is the opposite: "*it is possible
  to count the good figures for bad and the bad figures for good*" (f.11) — meaning is
  question-relative, so the engine always prints the question house it used.
- That the numbers in `priors.json` are magic. They are the finite population's arithmetic, and
  they are useful exactly in one way: they tell you when a chart feature is **news** and when it is
  something that occurs in 50-70% of all casts and therefore means almost nothing by itself.

## Status of this plan (2026-09-17, v0.2.0)

*Done*: rule verification incl. the 16th figure; corpus acquisition and OCR; 1,098 provenanced
passages + 23 computable rules + exact priors; engine built and audited; licence discipline in code;
repo hygiene; **source registry + automated sync + weekly health check** (the "which hosts are
trusted, and can a program fetch it" question); **triage flow for uploads**;
**outcome-indexed retrieval** + bundles + generated TS/OpenAPI contract; **differential accuracy
audit** (independent oracle, all 65,536 casts) and executable rule cases.

*Next, in order*: (1) OCR-diff the 32 measured Calatarama leaves cell-by-cell against
`kb/calatarama_grid.json`; (2) cross-check the 859 Hartmann answer cells using Hartmann's own
casting rule; (3) Persian/Arabic manuscripts (`nuskhah_raml_mcgill`, `surkhab_raml_leiden`) -
`make sync` then `make ocr`, expect new figures/rulings, nothing before the text is legible;
(4) a second oracle for `questions.py` sub-question routing (currently pinned, not proved);
(5) tag `v0.2.0` and publish `library/dataset/` as a release asset so apps can pin a version;
(6) app-facing topic coverage: 22 outcomes shipped, the classical corpus supports ~40 - the gap is
routing rows in `kb/houses.yaml`, not new text.
