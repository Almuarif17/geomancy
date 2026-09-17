# geomancy-library

A **source-cited dataset and rules engine for traditional geomancy** (the European *geomantia* and
Arabic *ʿilm al-raml* line): <!--num:passages-->1,140 extracted rulings and 23 computable interpretation rules, each
carrying the work and folio/leaf it came from, plus the exact statistics of the whole finite cast space
(65,536 charts). Built to be the knowledge layer under a casting app.

No invented readings, no vibes: if no source states a rule, the registry records it as `NAMED_ONLY` and
the engine refuses to compute it. Where sources disagree (which figure is Puer vs Puella; which planet
rules which figure), both variants ship and the output says so.

## Install and run

```bash
git clone https://github.com/<you>/geomancy-library.git && cd geomancy-library
pip install -r requirements.txt
make build        # -> library/dataset/geomancy.sqlite + shards/*.jsonl + manifest.json
make check        # licence gate + provenance gate + 23 engine checks
```

Cast a chart and get an explainable reading (the Mothers are the four thrown figures):

```bash
python3 engine/deep_read.py --mothers "Carcer,Amissio,Caput Draconis,Populus" \
        --topic travel_journey --day Wednesday --hour 4          # readable report
python3 engine/export_reading.py --mothers "Carcer,Amissio,Caput Draconis,Populus" \
        --topic travel_journey --out reading.json                # app-facing JSON, schema 1.0
```

`reading.json` is the product surface: chart, court, **validity gates**, relations (motus, parentage,
perfection *with its base rate*), the trace (Via Puncti, projection of the points, Part of Fortune),
the casebook sub-questions (turned chart, *figura extracta*, the mobile/communal tie-break),
specifics (who / where / when / constitution), and — deliberately — `gaps[]`, which lists every slot the
attested sources cannot fill. A blank that says "not attested" beats a confident guess.

## Use it from anywhere, at zero cost

The dataset is committed as JSONL, so it is directly servable as a CDN file - no server, no database bill.
Every URL below is checked to exist by `check_docs_consistency.py`, and each was fetched over HTTPS before
this release was tagged, because a documentation link that 404s is worse than no link:

```
https://cdn.jsdelivr.net/gh/Almuarif17/geomancy@v0.2.5/library/dataset/index/by_outcome.jsonl
https://cdn.jsdelivr.net/gh/Almuarif17/geomancy@v0.2.5/library/dataset/shards/passages.jsonl
https://cdn.jsdelivr.net/gh/Almuarif17/geomancy@v0.2.5/library/dataset/core_facts.json
https://cdn.jsdelivr.net/gh/Almuarif17/geomancy@v0.2.5/library/dataset/manifest.json
https://cdn.jsdelivr.net/gh/Almuarif17/geomancy@v0.2.5/types/geomancy.d.ts
```

Swap the tag for `@latest` while you evaluate, pin a tag the moment you ship. Pin the **CC0** layer
(`core_facts.json`) if you only need the figures, the house numbering and the arithmetic - it carries no
licence obligation at all.

Update protocol for a client: fetch `manifest.json`, diff the per-file hashes, download only the changed
shards, rebuild a local SQLite index. Offline-capable after first fetch. The prebuilt SQLite file is a
release asset - `geomancy-v0.2.5.sqlite`, 528 KB - so a client that would rather not run `make db` can
`curl -O` it; `make db` regenerates it locally, and it is not committed because the build derives it.

Update protocol for a client: fetch `manifest.json`, diff the per-file hashes, download only the changed
shards, rebuild a local SQLite index. Offline-capable after first fetch. `make db` regenerates the
SQLite file locally (it is not committed, because it is derived and CI rebuilds it).

## Run the reader (nothing to install, nothing to send anywhere)

```bash
python3 app/server.py            # then open the printed URL
```

A cast, a question, the sources that answer it, and what they do not answer - the whole pipeline in a page you
can hold in your hands before you write a line of integration code. It reads `app/preferences.json` on every
request, so a preference (which works you trust first, whether verbatim quotations are shown, how loudly the
gaps are named) is one edit and a reload. `python3 app/test_app.py` proves its 55 contract checks; `how it
works` in the header prints the eight build stages with live counts, generated from the shipped files, so the
explanation cannot drift from the thing it explains.

### On a phone

The same server answers `/m` with an installable app: cast by piercing sixteen hills of sand, by tapping rows, by
four rows to a page with the others asleep, or by holding a button while the phone taps for you; read all sixteen
places in three layouts; copy all the houses as text; hold a saved chart to share its shield as an image; open a
proof on any paragraph and get the arithmetic plus the work and folio behind it, never a citation melted into the
sentence. Nothing is re-implemented on the device, and nothing leaves it except to the engine you pointed it at: charts
live in the phone's own storage, in `localStorage`, on this handset. `python3 app/check_render.py` drives it in headless Chromium at 412x915 and fails on a clipped name.
Three ways to get it onto a phone, and one refusal - [notes/APP.md](notes/APP.md) has the reasoning, and
[notes/ANDROID.md](notes/ANDROID.md) the shell. Termux on the device is the recommended one, because then
`http://localhost:8044/m` is a secure context and Chrome will install it. If you would rather have a real
package, `python3 android/build.sh` produces `android/dist/D-Gem.apk` (debug-signed, sideloaded, no Gradle and
nothing to buy). What is not offered is a static host: no Pages deployment, because the reading is computed and
this repository will not keep a second copy of the rules to make a serverless build work.

## The same library as an agent tool (MCP, no dependencies)

```bash
python3 server/mcp_geomancy.py --self-test && python3 server/mcp_geomancy.py --transport-test
```

Six tools — `cast_from_mothers`, `grounded_reading`, `voices_for`, `score_answer`, `grounding_pack`,
`coverage` — over JSON-RPC on stdio, so Claude Desktop, Cursor or any MCP client gets a geomancy server whose
every sentence is cited and whose every gap is named. `score_answer` runs the library's auditor over *your*
model's prose and returns which sentences have no source under them. <!--num:mcp_tools-->6 of them, in
`server/README.md`.

## Layout

| path | what it is |
|---|---|
| `library/dataset/` | **the deliverable**: `passages.jsonl`, `rules.jsonl`, `manifest.json`, JSON Schemas |
| `library/tools/` | `build_dataset.py` (sources → dataset), `validate.py` (licence + provenance + coverage gate), `check_schema.py` |
| `LICENSE_POLICY.md` | three-bucket rule for what may ship as full text vs cite-only vs never |
| `kb/` | the knowledge base: `figures.yaml`, `houses.yaml`, `techniques.yaml`, the extracted grids |
| `engine/` | `deep_read.py` (report), `export_reading.py` (JSON), `questions.py` (casebook), `elections.py` (planetary gate), `audit_chart.py`, `test_deep_read.py` |
| `scripts/` | the harvesters: Internet Archive enumeration, fetching, OCR, per-work extractors |
| `docs/` | `FINDINGS.md` (what the sources actually say), `USAGE.md`, `RESEARCH_LEDGER.md` (archives, access terms, communities) |
| `data/fixtures/` | the two measured castings the tests reproduce 16/16 against |

`corpus/` and `work/` are **gitignored by design**: they hold bulk text and page scans pulled from
third-party repositories, most of which you may read but not redistribute. Everything in the dataset is
reproducible with `scripts/` from public identifiers — that is what makes the repo small *and* clean.

## The three things that make this different

1. **Provenance over prose.** Every ruling cites `work + locator`. Deep-link the locator to a page image
   (`https://archive.org/details/<id>/page/n<p>/mode/2up`) and your app can answer "why?" honestly.
2. **Base rates.** "Translation between the significators" happens in 18.2% of all casts; `occupation` in
   exactly 6.25% (= 1/16, as the algebra demands). Only 8 figures can ever be Judge, and they are
   equiprobable — so a Judge carries 3 bits, not 4. Rarity, computed over the whole space, is what turns
   a lookup table into evidence. `kb/priors.json`, `perfection_priors.json`, `calibration.json`.
3. **A gate in CI.** `make check` fails the build if a copyrighted work appears as a text source, if a
   passage loses its locator, or if any engine rule stops reproducing the fixtures. A corpus that grows by
   hundreds of works without a gate becomes a rumour machine; with one, it compounds.

## How much of the corpus is here

`kb/coverage.json` is generated from the shipped files and published for exactly this question, with
denominators instead of adjectives: **<!--num:coverage_score-->50/100** against our own targets today
(`<!--num:voices-->1,408 attributed voices`, <!--num:outcomes-->22 outcome routings,
<!--num:grid_cells-->184 of <!--num:grid_possible-->192 Calatarama cells, <!--num:rule_cases-->29 rule cases
of which 20 are proved twice). The file also lists the next moves, computed worst-component-first, so the
roadmap is a build output and not a mood. `python3 library/tools/score_coverage.py` prints it.

## Sources

Public-domain prints and open deposits: Cattan (1591, 1608), Heydon's *Theomagia* (1663), the
*Opus/Fasciculus geomanticum* compendia (1638, 1704 — including the *Quaestiones* of al-Fakini), Jean de
la Taille's French treatise, Hartmann (1889) with his 2,048-cell answer table, the *Libro de los
juysios de calatarama* via an open university deposit, Agrippa's second and "fourth" books, plus the
Voices (<!--num:voices-->1,408 attributed statements, each traceable to an author, an edition and
a folio) live in `kb/voices.jsonl`; `engine/ground.py` assembles them into a reading where an uncited
sentence is a validation error, not a style choice.

Latin/Castilian routing tables. Full list with licences: `library/dataset/manifest.json` and
`NOTICE`. Modern scholarship (Skinner, Greer, Regardie, Charmasson) is **cited, not quoted**.

## Licence and citation

Three layers, enforced by a gate rather than by trust — see `LICENSING.md` and `LICENSE_DATA.md`:

| layer | licence | what |
|---|---|---|
| code, schemas, generated types | **MIT** | run it, sell software built on it |
| `library/dataset/core_facts.json` | **CC0** | figure bits, house numbering, and what the arithmetic over all 65,536 casts implies |
| everything curated: `kb/`, dataset indexes/shards/tables, notes, findings | **CC BY-NC 4.0 + commercial licence** | translations, voices, glosses, adjudication |

A revenue-bearing product needs the L3 licence (open an Issue titled "commercial licence"); a free or
research tool needs only honest attribution. <!--num:licence_layers-->3 layers, and
`library/tools/check_licence_scope.py` fails the build if a tracked path is claimed by none of them or by two. Living-tradition material (Ifá verses, taboos, prescriptions)
is deliberately **not** included — see `LICENSE_POLICY.md` and `PRIVACY.md`. `check_licence_scope.py` fails
the build if a tracked path has undeclared or double-declared licensing.

```
Usman, A. (2026). geomancy-library: a source-cited dataset and rules engine for traditional
geomancy (v0.1.0) [Data set]. GitHub. https://doi.org/<zenodo-doi>
```

## Not a claim

This is a documented divination system, modelled faithfully. It predicts nothing that has been shown to
be predictable; treat readings as structured reflection with citations. See `NOTICE`.

## v0.2 - outcome-first retrieval, a source control plane, and a differential audit

* **`registry/works.jsonl`** - the corpus control plane. Every work is addressed by a persistent
  identifier (IA id, ARK, bitstream UUID, DOI, shelfmark) with its licence bucket, its disposition
  (`full` / `summarize` / `cite` / `drop`), the API recipe that fetches it, and a one-line reason the
  host is trusted. `make sync` rebuilds the corpus from that file; `make health` proves the links are
  still alive (weekly CI). New files go to `corpus/inbox/` and `make triage` proposes a bucket - it
  never admits anything itself. See `docs/SOURCES.md`.
* **Outcome indexes** - `library/dataset/index/by_outcome.jsonl` has one row per answerable outcome
  (22 today): quesited house, houses to read alongside it, every figure's ruling for that house with
  its folio, the exact base rate of each perfection mode, the passage ids, and the rules to apply.
  `bundles.json` tells a screen which files to download (50-350 KB) with a sha256 for cache-busting.
* **`engine/retrieve.py`** - the app's only import: `by_figure`, `by_house`, `outcomes`,
  `passages(...)`, `screen(...)`, `coverage()`. Offline, deterministic, no network.
* **`verdict` on the reading** - one object to render first: `does_it_perfect`, `mode`,
  `base_rate_pct`, `news_value`, `blockers`, `planetary_gate`, `trace_heads`, `headline`.
* **Differential accuracy** - `engine/oracle.py` re-codes the rules independently; `make eval`
  compares them over all 65,536 casts (currently 100% agreement on 7 checks) and `make rules`
  executes 29 rule cases. `docs/EVALUATION.md` records what was found and fixed, including a real
  bug: the old `via_puncti` dropped every branch but the last.
* **Generated contract artefacts** - `library/schema/*.json` → `types/geomancy.d.ts` (8 interfaces)
  and `library/dataset/openapi.yaml` via `make types`. Swift/Kotlin/TS apps have a typed target.

```bash
make full && python3 engine/retrieve.py --topic marriage --json | head -40
```
