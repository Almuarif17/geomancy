# Changelog

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
