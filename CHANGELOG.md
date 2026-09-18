# Changelog

## Unreleased — grounded UI, astrology of translation, JS chart on the phone

- **v1 kept, v2 settings pulled in.** `app/mobile.html` is still the phone app. Settings now
  also hold tick sound, show-the-sums, keep-history, and plain vs traditional names (the
  extras prototype v2 had). Buttons and cards are **solid and curved** (22px, a real
  shadow-step) instead of a silk wash.
- **Offline chart math.** `engine.js` + `perfection.js` ship in the page and in the APK.
  If Python is not answering, a cast still builds the shield, court, translation/occupation
  modes and house aspects on the device. Source *passages* remain a named gap until the
  dataset is fetched.
- **Astrology and translation.** The library already knew translation as a third figure.
  It did not know how signs and planets colour that third party. `kb/astrology.yaml` and
  `notes/ASTROLOGY_AND_TRANSLATION.md` add Agrippa 1655 signs (public domain), Cattan
  house aspects, company kinds (demi-simple = same planet), Agrippa's house chart as
  NAMED_NOT_DEFAULT, and Gerard of Cremona as NAMED_ONLY. Disagreements are not averaged.
  FINDINGS §23.


## Unreleased — JS runtime (no Python on the phone)

- **Architecture.** `docs/APP_ARCHITECTURE.md` records the decision: Python stays the research/oracle
  engine; the phone runs `web/engine.js`; knowledge is fetched from GitHub via jsDelivr and cached;
  no Termux, no engine-address dialog once the port is proved, no paid host, no LLM as the judge.
- **`web/engine.js`.** Mothers → Daughters → Nieces → Witnesses → Judge → Reconciler, Via Puncti,
  projection, Part of Fortune, motus. `node web/engine.test.js` walks all 65,536 casts: 0 odd Judges,
  eight even Judges at 8,192 each. This is the offline-engine backlog in `notes/APP.md`, started.
- **`web/cdn.js`.** Pin-tag fetch of `library/dataset/` through jsDelivr with a local cache.
- Not yet: Node↔Python differential in CI, outcome-shard retrieval in the UI, prototype v2 screens
  wired to this engine, APK without a Python server.


## 0.2.6 - 2026-09-17

- **Android shell.** `android/build.sh` wraps the phone app in a WebView and produces a debug-signed, sideloadable
  `android/dist/D-Gem.apk` with Gradle, Android Studio and the Play Console all absent: two free zips from Google
  and a JDK are the entire toolchain, and `android/prepare.py` assembles the APK's assets from `app/` at build
  time, so there is no second copy of the app to drift. The page is loaded from a made-up https origin and its
  `/api/` calls are proxied to whatever engine address the user names, which is what lets an http server on the
  LAN be installed at all - and the shell keeps no rule: no figure, no house, no quotation lives in the Java.
  `python3 android/build.sh --check` gates the sources without a toolchain; a GitHub Action builds the APK on a
  tag and uploads it next to the SQLite file. Two builds of the same tree produce identical bytes (the one entry
  `aapt2` does not normalise gets a fixed mtime), so `D-Gem.apk.sha256` beside it is a check a download can be
  held to, and `DEBUG_KEYSTORE` pins the signing identity so a newer build installs *over* an older one instead of
  being refused. `python3 android/serve_apk.py` hands the file to a phone over the Wi-Fi with that hash on the
  page, for when there is no cable and no `adb`.

### Added
- **The phone app.** `app/mobile.html`, a manifest, a service worker and two generated icons, served by the same
  `app/server.py` at `/m`. Four casting modes - sixteen pierced hills of sand (one dot or two at random each),
  one row per page across sixteen pages, four rows to a page with the untouched rows asleep until a double-tap
  wakes the next, and press-and-hold while the phone taps and buzzes - all of them feeding the engine the raw
  counts rather than the app's own conclusions. Three shield renderings (classical, 4x4, ledger) covering all
  sixteen places including the witnesses, Judge and Reconciler; copy-all-houses as text; share the shield as a
  PNG with the question drawn above it; auto-saved history on the device; three swiped reading panes (houses,
  advanced techniques and citations, interrelating who/where/when) where every paragraph ends in a **Prove**
  button opening the arithmetic and the named sources instead of a footnote merged into the prose.
- `POST /api/cast_from_rows` (sixteen tap counts or sixteen row values in, chart plus `mothers_arithmetic` out),
  `GET /api/chart16` (all sixteen positions with their derivation chain plus the technique layer),
  `GET /api/prove` (per-claim arithmetic, quotable and cite-only voices, the 65,536-cast differential, the audit)
  and `GET /api/copy` (the plain-text block). `GET /api/reading` now accepts `?prefs=` like the POST path does.
- `merge_prefs()` with a nine-key presentation whitelist: a phone may reorder, relabel and shorten, and the
  server answers with the keys it ignored, which the settings screen then prints.
- `app/make_icons.py` draws the app icons from the first four mothers, deterministically, and
  `--check` fails if the committed PNGs are stale - a binary a person made once in a graphics program is not an
  artefact this repo can reproduce.
- **`app/check_render.py`: 50 render checks in headless Chromium at 412x915**, driving all four cast modes, the
  proof sheet, the clipboard, history, theming and an offline engine, and failing on a clipped figure name, a
  `[object Object]`, a console error, or app arithmetic that has drifted from `deep_read.add`. It self-skips
  where Playwright is absent; CI installs the browser and runs it.

### Changed
- `app/test_app.py` grew from 26 to 55 checks, adding the tap-counting differential against the engine, the
  install files, the whitelist, the row arithmetic, and the copy block's sixteen numbered places.
- `copy_text()` now numbers the four court figures XIII-XVI as well as the twelve houses, so a pasted block still
  shows where every figure sits.
- `library/tools/validate.py --build` gates on the render check, so a release cannot ship an app that paints badly.

## 0.2.5 - 2026-09-18

### Added
- **The licence is now three layers, enforced by a build gate.** `LICENSING.md` carries a machine-readable
  `scope` block; `LICENSE_DATA.md` holds the precise terms; `LICENSE` opens with a notice that MIT covers the
  code layer only. L1 code MIT, L2 `library/dataset/core_facts.json` **CC0** (figure bits, house numbering,
  and what the arithmetic over all 65,536 casts implies - free forever, including commercially), L3 the
  curated layer **CC BY-NC 4.0 plus a commercial licence on request**. The README had been saying "Dataset and
  notes: CC BY 4.0", which licensed the paid thing away; that is what this closes.
- `app/test_app.py`: 26 checks over a real socket - routes answer, every claim keeps its locator, an unknown
  route is JSON 404 rather than a stack trace, no `fetch()` to an absolute origin (the page must survive a
  sandboxed preview and an offline copy), and the server logs no traceback while all of it runs.
- `library/tools/check_licence_scope.py` - fails the build when a tracked path is claimed by no layer (it
  would silently inherit MIT) or by two, and pins the CC0 layer to exactly one file of definitions and
  arithmetic. 232 tracked files, 3 layers.
- `library/tools/build_core_facts.py` -> `library/dataset/core_facts.json`, rebuilt as the first step of
  `finalize_dataset.py` so the manifest hashes it; deterministic, no timestamps.
- `kb/coverage.json` + `library/tools/score_coverage.py`: completeness against our own targets, every ratio
  printed with its numerator and denominator, and the next moves ranked worst-component-first. Disagreement
  counts are reported but never scored, because a library could only improve that number by hiding them.
  Every command the scoreboard prints is verified real (script exists, flags exist) - a scoreboard that tells
  you to run a command that does not exist teaches people to ignore scoreboards.
- `server/mcp_geomancy.py`: the library as an MCP server, standard library only, six tools
  (`cast_from_mothers`, `grounded_reading`, `voices_for`, `score_answer`, `grounding_pack`, `coverage`) plus
  three resources that hand the agent the licence text. Tested two ways in CI: a 17-check protocol surface and
  a real subprocess session over pipes (framing, notifications, garbage input, clean exit).
- `index/by_outcome.jsonl` rows now carry the voice layer with them - `n_voices`, `n_works`, `works`,
  `disagreeing_keys`, `quote_available`, `coverage_note` - so an app can show "32 voices, 1 work, 0 measured
  disagreements" without shipping 1,408 rows. The row shape is itself published as
  `library/schema/outcome_row.json`, generated by the build that writes the data and checked against the data
  in both directions; `types/geomancy.d.ts` is now 38 interfaces.
- Docs numbers extended: `coverage_score`, `licence_layers`, `mcp_tools` are markers, so the README's claims
  are build outputs.
- `manifest.json` - the file an app actually reads - now carries `licence_summary.outbound_licence` with the
  three layers and their paths, and `library/schema/manifest.json` **requires** it, so a build that publishes
  data without stating its terms fails the schema gate. `LICENSE_POLICY.md`'s advice to licence derived
  output "CC BY 4.0", `UPSTREAM.md`'s archive.org guidance and `docs/IP_STRATEGY.md`'s "if you say go"
  paragraph were all corrected to match what shipped; three stale licence sentences in three files is exactly
  how a split like this becomes folklore again.

- `app/server.py` + `app/index.html`: the reader. One command, standard library only, no third-party asset.
  Cast four mothers, pick a question, see the shield as dot patterns, then what the sources say, who said it,
  where in the folio, how many voices stand behind each claim, and what the corpus cannot answer. It is also
  the answer to "how do I understand this library": `how it works` in the header renders the eight stages from
  the live build, with the counts and the gate protecting each stage, so the explanation is generated and
  cannot disagree with the data.
- `app/preferences.json` is the owner's control surface, read on every request: which works are quoted first,
  whether verbatim quotations show, how loudly silences are named, which topics you actually get asked,
  the claim count a single reading may reach. It governs presentation only - `engine/ground.py` keeps sole
  authority over content - which is the line that has to stay where it is.

### Fixed
- **A chart bug in our own reader.** `engine/ground.py`'s CLI and `library/tools/check_grounding.py` passed all
  sixteen shield figures in as "houses", so `houses` held the two witnesses, the Judge and the Sentence as
  houses XIII-XVI, and `assemble()` would happily emit a claim about "Amissio in house XV" - a ruling no
  source contains, since every table in the corpus stops at XII. `_chart_from` now clamps to 1..12 and routes
  13-16 into the court, at the one choke point every caller passes through; a fixture reading lost 8 such
  claims (47 -> 39) and still audits clean.
- The court block of `assemble()` joined up to 11 contradictory Hartmann appendix answers into a single
  `sourced_ruling`, which presented a candidate set as a verdict and tripped the certainty auditor on
  verbatim source text ("He will go to see his sweetheart"). Divergent answers are now `sources_disagree`
  with `leans` and `candidate_answers` visible, counted in `gaps.contested`; `voyage` reports 4 contested
  positions where the old code reported a consensus.
- Every claim now states `mode` (`quote` or `gloss`). Court and correspondence claims carried no mode, so the
  auditor's rule "certainty language inside a quotation is the source talking, not us" could not apply to them
  and honest verbatim text failed the audit.
- `build_core_facts.py` first printed the 16 *house* labels as "attainable Judges", because `calibration.json`
  keys that table by house. It now reads `priors.json.possible_judges` and refuses to emit a Judge set whose
  members are not figure names - 8 even-pointed figures, verified.
- `gen_types.py` named interfaces from each schema's `title`, and titles are sentences: the shipped
  `types/geomancy.d.ts` contained `export interface A passage in the library: text is never allowed without
  provenance`, which no TypeScript compiler can read. Names come from the file stem now, titles became doc
  comments, and `check_schema.py` lints the emitted file (valid identifiers, balanced braces, no duplicate or
  dangling declarations) so this cannot come back unnoticed.

### Notes
- The stale `## Unreleased` section described a CI change that shipped inside `v0.2.3` (confirmed by
  `git merge-base --is-ancestor 69a1b7f v0.2.3`); its note is folded into 0.2.3 and the section is gone, with
  the file ordered newest-first again.

## 0.2.4 - 2026-09-17

### Added
- **Voices.** `kb/voices.jsonl`: 1,408 attributed statements across 9 families (figure-in-house 215,
  judge+cofigure answers 859, figure attributes 131, correspondences 87, quaestiones 42, look-rules 23,
  motion-between-houses 24, and the 27 rows that record documented conflicts rather than resolving them).
  Each row carries who wrote it, whose edition or translation reached us, a folio/leaf locator, the licence
  bucket, the quote where we may ship it, and `cite_only` where we may not. Built by
  `scripts/build_voices.py`; served as `index/by_voice.jsonl` (1,379 claim-keys).
- **Grounded reading.** `engine/ground.py` assembles a reading for a cast and a topic where every claim
  names its voices; `validate()` rejects uncited claims, citations that resolve to no voice, figures not in
  the cast, and asserted certainty; `score()` runs the same audit over someone else's text, so an app can
  publish a grounding rate instead of a vibe; `--prompt-pack` emits the instructions any language model is
  held to. Contract: `library/schema/grounded_reading.json`.
- Quote vs assertion is a first-class distinction: certainty language inside a cited quotation is the
  author's voice and allowed; the same words in our own gloss are a validation error.
- Polarity leans carry `polarity_reliability`. Early French/Latin OCR is `low`, and a `low` lean is treated
  as *unmeasured*, not neutral - otherwise two sources look like they agree because one of them was not
  scored. That rule alone changed "13 contested keys" into 4 genuine, measurable cross-source
  disagreements, which is the honest number.
- `library/tools/check_grounding.py`, wired into `validate.py` and CI: enforces that no quote text ships for
  a non-`full` work, that every voice is locatable and uniquely identified, and - the part that makes the
  auditor mean something - that it **fails** on four deliberately bad readings.
- `docs/COST.md` (what this costs: nothing, with the exact triggers that would change that) and
  `docs/IP_STRATEGY.md` (how a public repo stays uncopiable: three licence layers, and selling the machine,
  the freshness, the audit and the access instead of the data).
- `docs/VISION.md`: capability audit, market read with dated prices, six claims a buyer can verify with one
  command, three build tiers, the research agenda with expected yield, and the anti-goals.

### Fixed
- `FINDINGS.md` carried the superseded grid section (142 of 192, with the claim that absences were
  "scattered across figures ... not a systematic exclusion of one figure") as an orphan next to the corrected
  one, and two sections were numbered 13. Removed and renumbered 1-22.
- `library/dataset/evaluation.json` reported 1,098 passages against a manifest of 1,140 - only a Makefile
  target wrote it, so CI's freshness guard never saw it. CI now regenerates it and the guard covers
  `manifest.json` and `evaluation.json`.
- `library/README.md` advertised 1,098 passages to app builders; README, SOURCES, EVALUATION and
  `retrieve.py` prose likewise. Numbers that describe the build are now generated:
  `library/tools/check_docs_consistency.py` verifies marked numbers (`<!--num:passages-->1,140`) against the
  build and `--fix` rewrites them; it also asserts every shipped passage carries a locator, since that is
  the citation guarantee rather than a slogan.
- `scripts/publish_release.py` no longer embeds a personal identity in a tracked file - the leak gate flagged
  it, and it was right to.

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
- CI and `library/tools/validate.py` run `library/tools/check_calatarama_grid.py`, so the class of defect that
  cost 42 Calatarama rulings in 0.2.0-0.2.2 (a figure vanishing from every house, a cell swallowing the next
  appendix, a short house with no explanatory note) fails CI instead of landing in a release. No data change:
  the 0.2.2 assets remain byte-valid. (This note had been sitting in an `## Unreleased` section since; the
  change is inside `v0.2.3`, confirmed by `git merge-base --is-ancestor`.)
- Contents: 1,140 passages / 23 rules, 184/192 Calatarama cells, 12 houses, 22 outcomes. Bundles grew as
  the recovered rulings propagated: `verdict` 362K, `search` 840K, `offline_full` 349K.

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
