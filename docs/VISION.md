# What this is, what it is worth, and how it becomes the standard

Written 2026-09-17. Every number below was measured from this tree on that date, not remembered.
Sources for the market paragraphs are dated and linked at the bottom; they are 2026 pricing pages,
which is the point — the competitive line moves.

---

## 1. The one-sentence version

A **computable, citable, self-verifying geomancy library**: the figure arithmetic, the interpretive
rules, the historical rulings themselves, and a machine-checked guarantee that the first two are right
and the third says where it came from.

That sentence is the product. Everything else in this file is about making it defensible.

## 2. Capability audit (measured)

| plane | what exists today | measured |
|---|---|---|
| computation | shield, house chart, sentence, Via Puncti, projection, Part of Fortune, motus, judge parity | **65,536 / 65,536 agreement on all 8 checks** vs an independent oracle (`library/dataset/evaluation.json`, `engine/oracle.py`) |
| rules | executable interpretation rules with citations | **23** in `kb/techniques.yaml`; **19 HIGH**, 2 MED, 2 `NAMED_ONLY`; **29** cases in `kb/rule_tests.yaml` (20 proofs, 9 pins) |
| figures | cross-tradition attribute base | **16** figures, planet attribution conflicts (3) and naming conflicts (2) recorded rather than averaged |
| houses / questions | significators, court, question→house routing | **12** houses, 4 court, **22** question topics → houses |
| historical rulings | figure×house judgements from manuscripts and early prints | **184 / 192** Calatarama cells over all 12 houses; la Taille 8 tables; Cattan danger bank 23; Cattan motus 24; Alfagini 42 quaestiones; Hartmann casebook 138 KB |
| passages | located, citable text an app can render | **1,140** rows in `shards/passages.jsonl`, **all** with `work` + `locator`; SQLite FTS5 index shipped |
| corpus control plane | trusted-host registry with fetch/verify | **23** works: 7 `full`, 9 `summarize`, 3 `cite`, 4 `drop`; hosts = archive.org (16), utoronto scholaris, quest-journal, brill, worldcat/sudoc |
| app surface | pre-sliced indexes + bundles + generated contracts | `by_figure`(16) `by_house`(12) `by_outcome`(22) `by_work`(6); bundles `casting 76K / reading 160K / verdict 362K / topics 50K / search 840K / offline_full 349K`; `types/geomancy.d.ts`, `openapi.yaml`, JSON Schemas |
| integrity gates | things that fail the build | oracle differential, 29 rule cases, golden reading contract, schema validation, leak scan (220 files, 0), **extraction integrity** (`check_calatarama_grid.py`), reproducibility guard, weekly source-health CI, release verifier |
| honesty machinery | declared ignorance, machine-readable | `missing_figure_rulings` / `missing_house_rulings` per index row, `_meta.editorial_notes` (source lacuna vs suspected mislabel), `_meta.unmatched_labels`, `text_conflicts` |

The last row is the one people will not copy. Anyone can publish figure meanings. Almost nobody can
publish *the absence of a ruling, with the reason, in a field an app can branch on*.

## 3. How it gets used

Four real integration patterns, cheapest to richest.

**(a) Static files, no backend, no key.** Point a client at the CDN and pin the version:

```
https://cdn.jsdelivr.net/gh/Almuarif17/geomancy@v0.2.3/library/dataset/index/by_outcome.jsonl
https://raw.githubusercontent.com/Almuarif17/geomancy/v0.2.3/library/schema/reading.json
```

Offline apps ship `bundles.json`'s file list verbatim — that is the whole reason bundles exist: it tells
a build script which 5 files a *screen* needs, with hashes for cache-busting, so a casting screen ships
76 KB and not the 840 KB search bundle.

**(b) One SQLite file.** `geomancy-v0.2.3.sqlite` (528 KB): `passages`, `rules`, `priors`, `works`,
`cite_only`, plus `passages_fts` for search. No server, no migration, works on a phone.

```sql
select figure, locator, text from passages where house='VIII' and figure='Carcer';
-- ('Carcer', 'f.50 (house VIII)', 'Death of sick men and acquiring inheritances')
```

**(c) The engine as a library.** `engine/questions.py` routes a question sentence to a house,
`engine/deep_read.py` reads a chart, `engine/elections.py` gates on planetary validity,
`engine/retrieve.py --topic marriage --json` answers "what does this outcome need" in one call.

**(d) A generated contract.** `types/geomancy.d.ts` + `openapi.yaml` are *generated from*
`library/schema/`, so a consumer's compiler is checking our shape, not our README. The same schemas back
the JSON, so a producer/consumer drift is a build failure, not a bug report.

**And, increasingly, the buyer is an agent, not a human.** A model answering "will I get the contract?"
needs the same thing a developer does, and is far more dangerous without it: it will invent a
seventeenth-century ruling happily. The read path here is designed so the *only* way to get a ruling is
through a row that carries a folio.

## 4. What it feels like to use it

Be honest here, because the honest version is what sells.

**The good part is trust, and it arrives fast.** Every judgement has a locator. Rules are not prose,
they are `test_case` blocks that execute, so you can run the 29 cases in your own CI and stop
disagreeing about what the source meant. When the library does not know, it *says* it does not know, in
data: `no_source_ruling: true` with `missing_figure_rulings: ["Acquisitio"]`. For anyone building a
product where a wrong answer costs money or a store listing, that is the feeling of putting down a
weight you did not know you were carrying.

**The second good part is that it is boring on purpose.** JSONL and SQLite, no daemon, no key, no
network at runtime, MIT-ish clarity about what you may ship. Nothing to upgrade. `make sync` re-fetches
from long-lived hosts and fails loudly when a host rots, so the corpus does not silently decay.

**The bad parts, said plainly:**

- The reading *text* is early-translation prose ("Boredom of a woman and fornication and removal and
  corrupted viragins"). That is fidelity, not polish — and it is a product decision someone must make
  explicitly (see §7, "the wording layer").
- Only 22 outcomes are wired; a real app asks for ~60 and for timing, location-of-loss, and "who is the
  person" queries.
- Nothing is hosted: no uptime, no SLA, no free tier to poke at. Consumers must run a build step to get
  the SQLite. `verify_release.py` proves the artefacts, but a buyer should not have to prove anything.
- 9 of 23 rules are **pins** — contract tests that would now break but do not *prove* the rule from the
  source. The number is in the data on purpose; so is the fact that it is not 23/23.
- The API surface is CLI-first and Python-first. No JS/TS package, no WASM, no MCP server — three of the
  four things the market currently buys.
- `corpus/raw` is 64 MB of gitignored bulk. A fresh clone reproduces every *shipped* byte but cannot
  re-derive the corpus without `make sync`. That is the right legal trade; it costs convenience.

## 5. The market as it actually is

Free single-purpose casters are a solved commodity: browser shield + houses + a paragraph per figure
(traditional-astrology.com, psychicscience.org, geomancy.tools, oracle sanctum's generator). The most
complete one, **Geofancy** (Shetler, since 2022), is *free*, has perfections, Way of Points, a wiki,
JSON export, and states plainly "reference, not an oracle" and "no AI in the app" — a good tool, not a
data source, and not licensable.

The paying market is **developer APIs selling esoteric modules by subscription**, and it is real and
priced:

- **AstroWay**: 714 endpoints, entry **$5**, 50K credits, 175 Western, 12 house systems, **MCP**,
  OpenAPI 3.1, and an "Esoteric Pack" of 164 endpoints that **already includes geomancy (16 figures)**.
- **Astrology-API.io**: $0/$11/$21/$37/$99/$399+ per month, ~300 ms, "AI interpretations", 99.9 % SLA.
- **RoxyAPI**: ~$39–$699/mo across 18 domains (Tarot, I-Ching, Numerology, Kabbalah…) with MCP and
  white-label templates.
- **Swiss Ephemeris**: **CHF 750 one-time** professional licence, 99 years — the ceiling benchmark for
  *a computation library with no content at all*.
- **AstroSeek**: no licensed commercial API at any price, and its ToS forbids scraping — which is exactly
  why the paid tier above exists.

Two conclusions, and they are uncomfortable in useful ways:

1. **"Geomancy is unserved" is false.** It is listed on at least one paid API — as *16 figure blurbs*.
   What is unserved is geomancy as **a corpus with provenance, question routing, verified derivation,
   and adjudicated disagreement**. Nobody sells the thing in §1.
2. **Free tools set the ceiling on "cast a chart"; the floor on "be trusted" is what is scarce.** The
   buyers are (i) app studios shipping divination to thousands of users who need offline data and a
   licence, (ii) AI-agent/tool builders who need a ground truth that will not hallucinate, (iii)
   scholars and students of the history of divination who need citable, versioned texts.

## 6. The moat: claims, not features

A paid dataset is only worth paying for if a competitor cannot write the same sentence about their own
product, and if the buyer can check it in an afternoon. Ship these six claims, each with the command
that demonstrates it:

| # | claim | how a buyer verifies it | who else can say it |
|---|---|---|---|
| 1 | **The arithmetic is exhaustive-correct, not spot-checked.** | `python3 engine/evaluate.py` — all 65,536 casts against a second independent implementation | no one; free tools have no oracle |
| 2 | **Every rule you ship is executable and cited.** | `python3 library/tools/run_rule_tests.py` → 29 cases, proof/pin status visible per case | no one |
| 3 | **Every judgement has a folio or a page.** | `passages.jsonl` → `locator` non-null on 1,140/1,140 | no one; figure blurbs have no source |
| 4 | **Absences are typed, not silently missing.** | `by_house.jsonl` → `missing_figure_rulings`; `_meta.editorial_notes` distinguishes a cited lacuna (XII/Populus, fn. 706) from a suspected mislabel (VIII/Acquisitio) | nobody — silence looks like data in every other product |
| 5 | **The build is reproducible from a clean clone and the release is provable.** | `git clone && make build && python3 library/tools/verify_release.py --tag vX` | almost no one in this niche |
| 6 | **You may ship it.** Rights are decided per work, not assumed: public-domain or open hosts only, `cite_only` and `never_used` lists published in the manifest | `manifest.json.licence_summary` | free tools are silent; paid APIs are opaque |

Claims 1–6 are also the answer to "why not just scrape AstroSeek". Note the corollary: **a claim you
cannot demo with one command is marketing, not a moat.** If a feature does not produce a command for
that table, it does not get built.

### The compliance moat, which nobody in this niche talks about

Selling *readings* is classified **high-risk**: psychic/occult services were "not supported" by Stripe's
financial partners until Nov 2021, are still described as restricted, and the stated reason is chargebacks
and "claims not backed by science" (Wired, 2021; processor restriction lists, 2026). Selling *data and
computation* — a licence for a dataset, an ephemeris-style library, a hosted lookup API — is a different
merchant category entirely, which is how AstroWay and RoxyAPI operate openly with cards. Practical
consequences for this repo:

- Position and invoice as **developer infrastructure / scholarly data**, never as divination services.
- Keep "we do not assert predictive validity" in the licence text and in every contract artefact; it is
  a real liability posture and a real payment-risk reducer.
- Ship the **disclaimer + referral strings** (`engine/questions.py` routing health/legal/finite-life
  questions to "see a professional") as a first-class, documented feature. App-store reviewers care;
  buyers of white-label esoteric APIs have to solve this and currently do it badly. (Verified: this
  exists in the tree; the store-policy specifics are *not* verified here — check current App Store / Play
  rules before repeating this to a customer.)

## 7. What to build, in priority order

### Tier A — makes it buyable (weeks, not months)

1. **Hosted lookup + `POST /read`.** Not a rewrite: it is the SQLite file behind a thin FastAPI with
   edge caching, plus a 10K-request free tier and a key. Priced $19 / $49 / $199 to sit under the astrology
   API curve, since geomancy is a fraction of their surface. Without this, everything in §6 stays a
   hobby.
2. **MCP server (and an OpenAI/Gemini function spec).** This is 2026's distribution channel: AstroWay
   and RoxyAPI both advertise MCP. One tool, `geomancy.read(question|mothers, topic)`, returning the
   ruling **with locators and the typed absences**. Agents are the buyer most tormented by hallucinated
   occult content, and they cannot tell a folio citation from an invention — you are selling that
   difference.
3. **A real JS/TS package + WASM engine.** `@geomancy/core` with tree-shakeable bundles keyed off
   `bundles.json`, zero network at runtime, types generated from `library/schema/` (already done). Every
   app studio in this space is TypeScript; Python-only means no one can adopt you.
4. **The wording layer (decide, then ship both).** Right now one string per ruling. Split into
   `text_source` (verbatim, citable) and `text_plain` (modern paraphrase, editorially owned,
   versioned). The paraphrase is what an app shows; the verbatim is what a scholar cites; the separation
   is what keeps the product honest. This is the single biggest perceived-quality lever and it is cheap
   to *start*: do it for the 184 Calatarama cells + 8 la Taille tables first.
5. **`citation.pdf` / per-item citation export** (work, folio, translator, licence, version, DOI). Two
   buyer types want it: apps that show "source" in a tooltip, and academics.

### Tier B — makes it the standard (quarter-scale)

6. **Versioned dataset with a DOI + `CITATION.cff` + a methods paper.** Put it on Zenodo (free, versioned,
   mints DOIs) and write it up for *Journal of Open Humanities Data* or *De Historia* — a data descriptor,
   not a monograph. Free venue, and it converts "some guy's GitHub" into "the geomancy dataset that
   cites the Finan thesis and can be cited back". Citations are how a dataset becomes the default.
7. **A public coverage scoreboard, in CI, with the number going up.** One machine-readable file
   (`kb/coverage.json`) reporting: rules at proof vs pin (20/29), outcomes wired (22/~60), figure×house
   cells per source (184/192 Calatarama; 41.94 % of Hartmann's 2,048; Carcer 0/256), works fetched
   (7/23), translations with a `text_plain` (0 %). Publish the number *and* its trend. A buyer who sees
   a curve rising every month pays to stay on it; that is the subscription.
8. **A conformance spec + test suite for other implementations** (`geomancy-figure-spec v1`: bit order,
   mother/daughter/niece derivation, judge parity, Via Puncti, Reconciler). Whoever writes the spec owns
   the category. It is also the only defence against a big API vendor shipping "geomancy" as 16 blurbs
   and defining the term for everyone.
9. **An eval harness for LLM readers.** 300 frozen (chart, question) pairs with the *expected* sourced
   verdict, published with the dataset. Every AI app in this category will need to score its reader and
   currently cannot. Selling the exam is better than selling the answer.

### Tier C — the things only you can do (the actual "bigger than everyone" part)

10. **The West African / Sahelian living-tradition corpus.** The collector with regional access is the one who can do
    this. The Islamic geomancy manuscript and practitioner tradition — *ilm al-raml* in the Yoruba and Hausa north, sand-divination
    lineages, contemporaneous Arabic dictation with isnād-style chains of transmission — is essentially
    unpublished in machine-readable form, and no Berlin- or California-based competitor can collect it
    ethically or at all. Recorded, consented, transcribed, and licensed (even as "cite-only") that is not
    a better dataset, it is a *different category*, and it is the one thing here that cannot be
    reverse-engineered from a scan.
11. **Equating caution as a feature.** The best available scholarship warns against collapsing Ifá/
    Opon Ifá into European geomancy (they share the 4-bit/16 or 256 pattern space, not the practice).
    Publish the correspondence table **and** the boundary, with sources. Scholars will cite that discipline
    and app developers will trust it; the sloppy alternative gets you bad-pressed into a cultural
    appropriation fight that no paid product survives.
12. **Malagasy *sikidy*, Arabic printed editions, and the Sanskrit prasna line** (Prasna Marga,
    Shatpanchashika are already registered) — each is a separate axis of coverage that no one else in the
    price band has any of.

## 8. Research agenda: concrete, with expected yield

| target | what it unlocks | effort | first step |
|---|---|---|---|
| Barcelona, Biblioteca de Catalunya **MS 84.7.4**, f.50 and f.61v | resolves the VIII/Acquisitio suspected mislabel and confirms XII/Populus is genuinely blank; the only path to 186/192 | low | request/fetch folio images; transcribe the two rows |
| **Hartmann 1889 appendix** (cols. 1329 ff.) column-by-column OCR | the Carcer 0/256 block, and 2,048 answer cells → moves Hartmann coverage from 41.94 % upward; a *second independent* attestation of every Calatarama cell | medium | `scripts/ocr_pipeline.py` on IA `b24884145`; the appendix has no page breaks in the existing djvu — re-OCR from page images |
| **Agrippa, *De occulta philosophia* II.31–32** + **Trithemius, *Polygraphiae*** geomancy tables, Latin | a Latin recension to diff against Castilian; currently our Latin side is Alfagini's 42 quaestiones only | medium | IA text layer + `scripts/extract_*.py` per source |
| **Bruno, *De geomantia* (1587)** and **Fludd** | the "figure as meditation/memory" branch; mostly cited, never structured | medium | locate scans; summarise disposition, do not ship text without licence |
| **al-Zanātī / Abū ʿAlī al-Ḥasan** lineage texts, Arabic | the derivation algebra we already use for Judges (XI = 5+6, XII = 7+8) in its own words; van Binsbergen's paper is the map | high | track down editions via Brill/`worldcat`; `cite` disposition if closed |
| **Kitāb-i Surkhāb** (already registered, IA `ldpd_13892500_000`) | a Persian systematic treatise; would be the second full non-European source | medium | full page-image pass with `scripts/ocr_pages.py` |
| **9 pinned borrow-only items** needing an archive.org login | converts `cite_only` → `full` for several works; directly raises the fetched-work count | low | you log in once, download, `make sync --only …` |
| 9 pins → proofs (`kb/rule_tests.yaml`) | "every rule is *derived* from a source, not asserted" — claim 2 becomes 23/23 | low–med | pick the 4 timing pins; each proof needs a cited worked example |
| outcomes 22 → ~60 | closes the most visible functional gap; every added outcome needs house routing + a ruling set + a base rate | medium | extend `kb/question_taxonomy` from the Alfagini/Cattan question lists already in `kb/question_inventory.json` |
| **`text_plain` for 184 cells** | the wording layer (Tier A.4) | medium | 2 passes: literal gloss, then idiom; keep both fields |

## 9. Quality work this audit found (do it now, it is small)

- `library/dataset/evaluation.json` said **1,098** passages while the manifest said **1,140**: the file is
  written by a Makefile target only, so CI's freshness guard never looked at it. Regenerated; the guard now
  covers it.
- Six public files still announced 1,098 in prose. Numbers in prose must come from the build, so there is
  now a gate (`library/tools/check_docs_consistency.py`) that extracts claimed counts and compares them to
  `manifest.json`. This class of defect — *documentation asserting a stale measurement* — is the same failure
  mode that put a false claim into FINDINGS §21 on 2026-09-17. Treat any human-written number as a bug
  until a gate has touched it.
- `retrieve.py`'s help text and `by_outcome`'s key name (`ruling_table`, not `figure_rulings`) both tripped
  me up while writing §2. Rename to `figure_rulings` with a deprecated alias, or document the shape in the
  schema — a generated contract should not have a surprise in it.

## 10. Anti-goals (what makes this *worthless* if we do it)

- **Never invent a ruling to fill a cell.** A gap labelled "ours" is a to-do; a gap filled with plausible
  text is a defect that ships.
- **Never claim predictive validity, and never imply clinical or legal advice.** The disclaimer is part of
  the licence, not a footer.
- **No "AI reading" feature that dresses a model in the library's authority.** Sell the ground truth;
  do not sell the thing that hallucinates about it. (Geofancy's "no AI in the app, period" line is the
  market already asking for exactly this separation.)
- **Do not average conflicting sources.** `figures.yaml` keeps 3 planetary-attribution conflicts and 2
  naming conflicts as conflicts. A flattened value is how a dataset becomes unusable for scholarship and
  unremarkable for apps.
- **No copyrighted text, ever, however small the excerpt.** That rule is why 7 works are `full` and 3 are
  `cite_only`; it is also a selling point (§6, claim 6), so do not trade it for coverage.

## 11. The 90-day shape

1. **Weeks 1–2:** §9 fixes; DOI + `CITATION.cff`; the coverage scoreboard file, published and trending.
2. **Weeks 3–6:** hosted read-only API + free tier; MCP server; TS package from `bundles.json`. First ten
   users, chosen for ability to complain publicly.
3. **Weeks 7–10:** Barcelona folios (→ 186/192 or a documented no), Hartmann appendix OCR, wording layer
   on the Calatarama grid. Publish the methods paper.
4. **Weeks 11–13:** price page with the §6 verification commands on it, plus a "prove it yourself" page
   that runs nothing on our servers and shows the local commands instead. That page *is* the pitch.

The test of whether this became "the biggest": not stars, not size — it is whether someone else's
implementation is tested **against our spec**, whether a citation of a geomancy dataset in print points
at our DOI, and whether a paid API that lists geomancy has to say "powered by" to be believed.

---

### Sources used above

- traditional-astrology.com/geomancy.html; geofancy.up.railay.app (Geofancy v1.0.6, "reference, not an
  oracle", no AI, no server persistence); oraclesanctum.com; psychicscience.org/geomancy; geomancy.tools —
  the free-tool baseline, all $0.
- api.astroway.info — 714 endpoints, entry $5, "Geomancy (16 figures)", Esoteric Pack 164 endpoints, MCP,
  OpenAPI 3.1; comparison table with Astrology-API.io $11, Prokerala $19, RoxyAPI $39.
- astrology-api.io — tiers $0/$11/$21/$37/$99/$399+, ~300 ms, 99.9 % SLA, "AI interpretations".
- RoxyAPI — $39–$699/mo, 18 domains, MCP, white-label templates.
- Swiss Ephemeris — CHF 750 one-time professional licence (99 years), as the ceiling for a
  computation-only library.
- Wired, 2021, "Stripe Discriminates Against Witches" + Stripe's Nov 2021 policy update; 2026 processor
  restriction lists — the high-risk classification of psychic/occult *services*, and why a *data licence*
  is the commercially clean shape for this.
