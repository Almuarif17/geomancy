# geomancy/ — a deep-reading stack, built to be extended

Four things live here: a **source corpus**, a **knowledge base** extracted from it with provenance,
an **engine** that computes the rare techniques, and **validators** that keep both honest.

## Layout

```
corpus/raw/      primary texts (typed translations preferred; OCR where unavoidable)
corpus/ocr/      per-page OCR output + INDEX.md triage, for scanned books
corpus/MANIFEST.md       what each file is, its size, and how much technique-signal it holds
corpus/ia/IA_CATALOG.md  the complete IA harvest: 259 relevant of 1,604 unique, with text-layer,
                         borrow-status and scan counts (the shopping list), with text-layer,
                         licence and borrow status - the shopping list for what to fetch next
corpus/raw/ia/           open text layers from that sweep (Agrippa 1655/1783, Fasciculus 1704,
                         German Geomantia 1704-47, Hartmann 1889, SurkhAb raml 1528, Lal Kitab, ...)
corpus/raw/ia3/          open items from the complete IA sweep, incl. la Taille's Geomancie and the two Ifa-studies
                         (see _REMOVED_because_in_copyright.txt for in-copyright items I deleted)
corpus/raw/ia2/          the horary question literature (Prasna Marga, Shatpanchashika, ...)
corpus/raw/ia/fasciculus_ocr/  my own tesseract pass over the Quaestiones leaves (lat+eng)
docs/RESEARCH_LEDGER.md  libraries to go to, what each asks for, communities and their citations
data/fixtures/README.md   the gem-count readings from your two app screenshots
kb/figures.yaml  16 figures: patterns, Arabic + Ifá names, qualities, humours, timing unit,
                 extracted medieval attribute rows, and the two conflicts in the sources
kb/houses.yaml   the 12 houses + court, the Calatarama house table, question -> house routing
kb/techniques.yaml     23 techniques as algorithms, each with source, page/folio and a confidence
kb/lataille_grid.json          8 rulings + 3 rules from Jean de la Taille's French treatise
kb/calatarama_grid.json  142 figure x house rulings (typed translation, folio-tagged)
kb/cattan_motus_bank.json    24 motion rulings (English Renaissance, OCR'd)
kb/cattan1591_dangers.json   23 page-pointers to Cattan's per-figure/per-house event rulings (weapon, poison, prison, sickness), raw OCR by design
kb/priors.json   exact P(figure | house) + surprisal over all 65,536 casts
kb/perfection_priors.json  exact base rates of occupation/conjunction/mutation/translation per house
kb/calibration.json  the oracle's own bias, measured
engine/deep_read.py    the reader: chart -> validity -> relations -> trace -> specifics -> cross-read
engine/questions.py    the sub-question engine: 35 casebook rules incl. la Taille's tie-break, every one leaf-cited
engine/elections.py    day/hour lords, temporal hours, legality gate, re-cast advice
engine/audit_chart.py  verify any chart (app or book) against the generation rules
engine/build_priors.py, engine/build_perfection_priors.py   regenerate the statistics
engine/test_deep_read.py 24 checks, incl. exhaustive over the whole cast space
scripts/             acquisition, OCR, and extraction tooling (each source has its extractor)
readings/            generated reports
```

## Use it

```bash
cd geomancy
python3 engine/deep_read.py --mothers "Carcer,Amissio,Caput Draconis,Populus" \
        --topic travel_journey --day Tuesday --hour 3 --out readings/x.md
python3 engine/test_deep_read.py                     # must end with FAILURES: 0
python3 engine/audit_chart.py data/fixtures/chart2.json # which convention a chart obeys
python3 engine/build_priors.py && python3 engine/build_perfection_priors.py   # refresh stats
```

Topics understood: `marriage love_partner wealth_money job_livelihood career_rank children pregnancy
health illness death property_land inheritance travel_journey studies servants_workers lawsuit
enemies_obstruction imprisonment_absent lost_things news_message friends animals`.
`--day` is the weekday of the cast and `--hour` the **planetary** hour (1-24 from sunrise);
omit `--hour` to skip the hour test. Use `elections.planetary_hour(sunrise_min, sunset_min, now_min)`
to get a real hour number — clock hours are wrong outside the equinoxes.

## Reading a generated report

1. **Validity first.** If a gate fails, stop; the advice given is what the sources advise (wait an
   hour, re-cast, distrust the querent).
2. **Judge and Sentence** are the headline and the after-effect. `*` on Puer/Puella means the label
   is contested between traditions, not that the cast is uncertain.
3. **The trace** (Via Puncti, projection, Part of Fortune) tells you where to look *outside* the
   obvious house. A "clean single line" and "no branch" are different statements; "cannot form" is
   itself an answer.
4. **The news-value line** matters more than the mode name: a mode that occurs in 50% of all casts
   is not a sign.
5. **Every specific** (`who`, `where`, `when`) is printed with its source or with an explicit gap
   message. Gaps are not omissions to fill by imagination; they are marked TODOs against a folio.

## Page scans are NOT stored here
The PDFs and EPUBs (multi-hundred MB) are re-downloadable, so they live outside the workspace.
`python3 scripts/refetch.py fasciculus_geomanticus_1704` restores one; `--all` restores everything.
`corpus/raw/ia/_fetch_report.json` holds the exact URL for each item, plus its licence/borrow flags.

## Adding a source

```bash
python3 scripts/find_sources.py            # adapt a query, list candidates
python3 scripts/acquire.py                 # fetch IA text layers + quality-score them
python3 scripts/ocr_ingest.py <id> --pages 140-180 --out corpus/ocr/<name> \
        --keywords judge,house,figure,...               # triage a scan
# then write scripts/extract_<name>.py that emits JSON into kb/, and register the
# technique in kb/techniques.yaml with source + confidence (NAMED_ONLY if no procedure).
# Finally: extend engine/test_deep_read.py so the new rules are checked, not trusted.
```

The rule that keeps this honest: **a technique is only computed if a source states how to compute
it; a source that merely names it is recorded as `NAMED_ONLY`.** Nothing in `kb/` was invented to
fill a gap, and where the tradition disagrees with itself, both readings are kept and the
disagreement is printed.
