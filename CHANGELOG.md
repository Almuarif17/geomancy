# Changelog

## 0.2.3 - 2026-09-17

### Fixed
- `library/tools/check_calatarama_grid.py` used an f-string with nested identical quotes
  (`f"...{doc["houses"]}..."`), which is PEP 701 syntax: accepted by Python 3.12+, a **SyntaxError** on the
  3.11 interpreter CI pins. The gate therefore died before printing anything, and `validate.py` reported a
  failure with no detail because it only read the child's stdout. Rewritten portably.
- `library/tools/validate.py` now appends the child's stderr tail whenever a subprocess gate fails. A gate
  that cannot say why it failed is worse than no gate; that is why this took a CI run to diagnose.
- The shipped derived files were not what a fresh clone produces: `library/dataset/index/*`,
  `bundles.json` and `tables/calatarama_grid.json` were built from an older passage set, so CI's
  "Generated artefacts must be committed" guard had been failing since 0.2.1. Rebuilt in CI's exact order
  (`build_dataset` -> `retrieve --build` -> `gen_types`) and committed; a clean clone is now reproducible.

### Notes
- Contents: 1,140 passages / 23 rules, 184/192 Calatarama cells, 12 houses, 22 outcomes. Bundles grew as
  the recovered rulings propagated: `verdict` 362K, `search` 840K, `offline_full` 349K.

## Unreleased

### Added
- `.github/workflows/validate.yml` and `library/tools/validate.py` now run
  `library/tools/check_calatarama_grid.py`, so the class of defect that cost 42 Calatarama rulings in
  0.2.0-0.2.2 (a figure vanishing from every house, a cell swallowing the next appendix, a short house
  with no explanatory note) fails CI instead of landing in a release. No data change: the 0.2.2 assets
  remain byte-valid.

## 0.2.2 - 2026-09-17

**Fourty-two cells that were never missing from the manuscript.** The Calatarama grid goes from
142 rulings over 10 houses to **184 over all 12**, and the shortfall that remained turns out to be the
sources own, with a citation attached.

### Fixed
- `scripts/extract_calatarama_grid.py` dropped every `[Carcer]` row: the alias map listed `Carcel` and
  `Carcel`-with-ccedilla but not the canonical spelling, so the traditions figure of detention and death
  seemed judged in no house at all. Names now resolve through `kb/figures.yaml`, and anything the parser
  cannot place is reported in `_meta.coverage.unmatched_labels` instead of being discarded.
- Houses VIII and X were skipped whole because those two tables are headed irregularly ("Meaning of the
  geomantic **house** in the VIII House"; "Meaning of geomantic figures in the X House", without "the").
- Section slices are now bounded at `Appendix 2:` and choose the richest occurrence per house, so headings
  quoted in the thesis commentary cannot cut a table in half (house XIIs `Via` cell held 600 characters of
  transcription conventions before this).
- A transcriber insertion bracket (`the hear[are] not equal`) was being read as a figure label; a bracket
  only opens a row when whitespace precedes it.
- **Wrong data shipped in v0.2.0**: house Xs `Laetitia` ruling had been filed under house IX.
- `library/tools/sync_corpus.py` wrote PDF bytes into `.txt` files; PDFs are stored as binaries and flagged
  for text extraction instead of producing a corrupt corpus file.

### Added
- `kb/calatarama_grid.json` `_meta.coverage` recomputed (184/192, per-house shortfalls),
  `_meta.editorial_notes` (the two deliberate absences) and `_meta.text_conflicts` (7 cells where the
  corrected parse differs from the published one, each with both texts so the change is auditable).
- `library/tools/check_calatarama_grid.py`: fails the build when a figure is absent from every house - the
  shape of a broken extractor dressed up as a source gap - or when a house with a shortfall carries no note.
- FINDINGS 21 rewritten. It had asserted the absences were "scattered across figures ... not a systematic
  exclusion of one figure", a claim the same runs output disproved; the corrected section names each defect.

## 0.2.1 - 2026-09-17

* `library/tools/verify_release.py`: downloads a release's `SHA256SUMS.txt` and every asset, checks
  the digests, and confirms the tarball's `manifest.json` matches a local `make build` - so
  "content-addressed" is provable from the network, not a claim. Run against v0.2.0: 5/5 assets ok,
  21/21 manifest digests match.
* Gap accounting made machine-visible: `index/by_house.jsonl` carries `missing_figure_rulings` and
  `by_figure.jsonl` carries `missing_house_rulings`; `retrieve.coverage()` reports them. Measured state
  of the Calatarama grid: **142/192 cells, houses VIII and X absent from our extraction** - recorded in
  `kb/calatarama_grid.json` `_meta.coverage` with the re-extraction target, and FINDINGS s.21.
* Docs: release assets are the recommended consumption path for apps; `SETUP.md` covers a fresh clone.

## 0.2.0 - 2026-09-17

* Added `registry/works.jsonl` (23 works: identifier, licence bucket, disposition, host-trust
  reason, retrieval recipe) + `library/tools/sync_corpus.py` (fetch/verify/lock, `--check`,
  `--dry-run`) + `library/tools/triage.py` (inbox -> proposed bucket, never auto-admitted).
* Added outcome-first retrieval: `engine/retrieve.py`, `library/dataset/index/{by_figure,by_house,
  by_outcome,by_work}.jsonl`, `bundles.json` (per-screen files + bytes + sha256), and
  `library/dataset/tables/` so the dataset is self-contained on a device.
* Added `verdict` to the reading contract (schema-required), `trace.via_puncti.endpoints` +
  `branch_count`, and a warning flag for topics with no sub-question bank; aliased the app-facing
  topic names (theft, lost_item, treasure, missing_person, lawsuit, litigation, court_case).
* Added `engine/oracle.py` + `engine/evaluate.py`: independent re-implementation, differentially
  verified over all 65,536 casts; `library/dataset/evaluation.json` published with the build.
* Added `kb/rule_tests.yaml` (29 executable cases, 20 proofs / 9 pins) + `run_rule_tests.py`;
  `validate.py` now gates registry legality, licence disposition, source citations, rule cases,
  oracle agreement and generated artefacts.
* Added `library/tools/gen_types.py` -> `types/geomancy.d.ts` + `library/dataset/openapi.yaml`.
* Fixed: `via_puncti` dropped all but the last branch (now follows every head, per the bicéphale
  rule); published artefacts moved out of the gitignored/snapshot-excluded `library/build/`;
  schemas relocated to `library/schema/`; example reading regenerated.
* Docs: `docs/SOURCES.md`, `docs/APP-INTEGRATION.md`, `docs/EVALUATION.md`. CI: dataset paths,
  new gates, and a weekly `sources-health.yml` that fails on link rot.

## v0.1.0 — first public release
- Dataset: 1,098 source-cited rulings (150 figure×house rulings from the Calatarama and Jean de la Taille,
  42 Latin quaestiones from the *Fasciculus geomanticus*, 859 answer cells from Hartmann's 2,048-cell table,
  47 motion/particulars rows from Cattan) + 23 computable interpretation rules (19 rated HIGH).
- Knowledge base: 16 figures with cross-tradition names (Latin, Arabic *ʿilm al-raml*, flagged Ifá
  correspondence), humours, timing units, attribute tables; 12 houses with the medieval routing table;
  two source conflicts recorded rather than harmonised (Puer/Puella pattern; planetary attributions).
- Engine: shield with the classical nephew rule (V+VI, VII+VIII), validity gates, motus, parentage,
  perfection with exact base rates, Via Puncti with branching, projection of the points, Part of Fortune,
  humours + remedy, who/where/when, planetary-day/hour gate on temporal hours, casebook sub-questions
  including the turned chart from the Judge and the *figura extracta*.
- Statistics: exact finite population over all 65,536 casts — attainable figures per house, surprisal,
  perfection-mode priors, and the oracle's own optimism bias measured.
- Contract: `reading.json` schema 1.0 with a mandatory `gaps[]` field; JSON Schema in `library/dataset/schema/`.
- Gates: licence/provenance/coverage validation in CI, 23 engine checks, 12 dataset/schema assertions.
- Known gaps (see `library/dataset/manifest.json` and each `gaps[]`): the Calatarama attribute table covers
  6 of 16 figures; la Taille's grid survives for 3 houses; the *hidden figure* and *suffrage* techniques are
  named in the literature without a stated procedure and are therefore not implemented.
