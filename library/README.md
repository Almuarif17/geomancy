# THE LIBRARY — what it is, how it grows, what it costs

You are not building a folder of PDFs. You are building **a dataset with provenance**, and an app that
reads it. Everything below follows from that one decision.

## 1. The shape

```
library/
  README.md              this file
  LICENSE_POLICY.md      what may be shipped, what may only be cited, and how to record it
  schema/                the contracts (JSON Schema) the data and the app must satisfy
  tools/
    build_dataset.py     kb/ + corpus/  ->  geomancy.sqlite + shards/*.jsonl + manifest.json
    validate.py          the gate: licence, provenance, coverage floors, engine tests
  dataset/               the published artefacts: shards + manifest + schemas (sqlite is derived, gitignored)
```

Four layers, and they never mix:

| layer | contents | who writes it | changes how |
|---|---|---|---|
| **L0 sources** | the works themselves: identifiers, licences, page images, folio cites | nobody edits | never (immutable, addressed by `sha256`) |
| **L1 extracts** | passages with `work + locator + confidence` — rulings, quaestiones, tables | harvesters + you | append |
| **L2 rules** | `kb/techniques.yaml`, `kb/figures.yaml`, `kb/houses.yaml` — computable procedures | you, by hand | rarely, and with a test |
| **L3 statistics** | `priors.json`, `perfection_priors.json`, `calibration.json` — generated from the whole finite space | `engine/build_*.py` | regenerate, don't edit |

The app renders **L2 + L1**: a rule fires, and each firing carries the source line that authorises it.
L3 gives it the sentence nobody else's app can say: *"this configuration occurs in 6.2% of all casts —
that is news"* versus *"...in 49% of all casts — that is nothing."*

## 2. The app contract

`python3 engine/export_reading.py --mothers ... --topic ... --day ... --hour ... --out reading.json`

`reading.json` (schema `1.0`) is the whole product surface: `chart`, `court`, `validity[]` (with
`planetary_gate` and `recast_options`), `relations` (motus, parentage, perfection **+ its base rate and
news-value**, triplicities with the medieval routing), `trace` (Via Puncti with branches, projection,
Part of Fortune), `sub_questions` (the casebook: which houses, the turned chart, the figura extracta,
the tie-break, the call), `specifics` (who / where / when / constitution + remedy), `cross_read`
(Arabic names, Ifá column flagged as comparative), and **`gaps[]`**.

`gaps[]` is the feature that will make your app trusted: when the source table has no colour or
direction for Fortuna Major, the JSON says so explicitly, and the UI renders *"not attested in the
extracted tables"* instead of inventing something. Never let the UI draw a blank as silence, and never
let a model fill it.

## 3. Zero-cost build and hosting (all free tiers, all usable from anywhere)

**Do not rent a server.** Git is your database host, a CDN is your API, and SQLite is your client cache.

| need | tool | cost | why this one |
|---|---|---|---|
| versioned source of truth | **git on GitHub/GitLab/Codeberg** (private repo ok) | free | every change to a rule is a commit with a diff and a discussion; rollback for free |
| serving the data | **jsDelivr CDN** over the repo, or **GitHub Pages / Cloudflare Pages** | free | works well on poor networks, cached, no origin server; the app fetches `shards/*.jsonl` |
| big blobs (scans, page images) | **archive.org upload** of your own derived bundle, or leave them where they are and store the identifier | free | you never ship 400 MB in an app; you ship `ia_identifier + page` and link out |
| citable snapshots | **Zenodo** via the GitHub integration | free | every release gets a DOI — this is what makes your corpus citable and defensible |
| search + records, if you outgrow JSONL | **Supabase** or **Neon** or **Turso** free tier (Postgres/SQLite) | free to ~500 MB | only needed once you have user accounts; start without it |
| full-text search over the corpus | **SQLite FTS5 inside the app** (already built) | free | <!--num:passages-->1,140 passages ship in ~900 KB and search offline; no server round-trip |
| CI that enforces the licence gate | **GitHub Actions** (`.github/workflows/validate.yml`) | free for public/2,000 min private | the build fails if copyrighted text sneaks in |
| notes, backlog, "who found what" | repo **Issues** + `docs/FINDINGS.md` | free | your harvest scripts become issue templates; contributors can add works safely |

Realistic bill at "giant" scale: **₦0**. The first time you pay anything is when you want a custom
domain or >1 GB of user data — and even then a $5 VPS is unnecessary; move blobs to R2/B2.

**Offline first.** Ship the SQLite file inside the app bundle (it is under 1 MB now, and even 50 MB of
passages is fine). Sync = fetch a new `manifest.json`, diff by `sha256`, download only changed shards.
That's a versioned content library with no backend: it works with the network switched off entirely.

## 4. Growing it "giant" — the loop, not the wish

The harvest is already a pipeline; point it at volume and keep the gate on.

1. **Enumerate**: `scripts/ia_harvest_all.py` (paginated, dedup, licence+text-layer probe).
   Add queries in `QUERIES`; 38 queries already produced 1,604 unique items → 259 relevant.
2. **Triage**: `corpus/ia/IA_CATALOG.md` — one row per item: `txt` / `rstr` / `scans`.
   Borrow-only → your free account; scans-only → OCR; open+text → fetch.
3. **Fetch**: `scripts/ia_fetch.py`, `scripts/ia_complete.py` (metadata-driven file lists, not guessed URLs).
4. **OCR where needed**: `scripts/ocr_pages.py` — parallel, resumable, cached; `lat+eng` for early print,
   `frk` for blackletter, `ara/fas/hin/san/urd` for raml manuscripts. ~25 s/page.
5. **Extract into L1**: one small script per work (`scripts/extract_*.py`) emitting rows with
   `work, locator, figure, house, kind, text, confidence`. Keep raw OCR text — never silently "clean" it.
6. **Distil into L2**: only what a source actually *states* becomes a rule; anything merely named is
   `NAMED_ONLY` and the engine must refuse to compute it. This is the rule that keeps you honest and
   keeps your app from becoming a horoscope generator with a fancy vocabulary.
7. **Regenerate L3**: `engine/build_priors.py`, `engine/build_perfection_priors.py` whenever L2 changes.
8. **Validate**: `python3 library/tools/validate.py` → must print `BUILD IS CLEAN`.

Volume you can realistically reach in a few unattended nights: **every public-domain geomancy print on
Internet Archive plus the HathiTrust/Gallica/BSB/Leiden mirrors of the same corpus** — call it 300–600
works, 5–15 k passages, 40–120 computable rules. That is already larger than anything published in
English on the subject, and it is legal to ship.

## 5. What will actually be hard (so you plan for it)

- **Non-Latin scripts.** Arabic/Persian/Devanagari text layers exist but need real OCR + bidi handling;
  budget sessions, not afternoons. Do the Latin/French/German/Italian first — that is where the
  *computable* rules already are (al-Zanāṭī's algebra reached us in Latin and Castilian anyway).
- **Attribution conflicts.** Three early sources give three element/planet tables; Puer/Puella patterns
  swap between Britannica/GD and the Skinner line. Store variants, re-run under each, and show the
  disagreement — do not average. `kb/figures.yaml` already models this.
- **Copyright discipline.** Full text only for PD/open works; everything modern = citation + your own
  words. The gate in `validate.py` is not bureaucracy; it is the difference between a shippable product
  and a takedown.
- **Evaluation.** Before you market "advanced explanation", define a test set: 30 historical castings
  with the casebook's own answer (Alfagini's quaestiones and the Calatarama's example questions give
  you labelled data for free). Measure how often your engine reproduces the source's ruling. That
  number — not eloquence — is your moat.

## 6. Decisions I would make today

1. Public repo, `main` protected, `validate.py` in CI. Data-as-code, releases tagged, Zenodo DOI on release.
2. Ship `geomancy.sqlite` + `manifest.json` in the app; fetch updates as shards; no backend until you have users.
3. Keep the inference **deterministic**. Add an LLM only as an optional *renderer* of the JSON — never as
   the thing that decides. If a model can produce a ruling that no rule emitted, the app is a fortune cookie.
4. Every UI line is a link: rule id → source work → folio/leaf → (where open) the page image. "Why?" is your differentiator.
5. Publish `FINDINGS.md`-style notes openly. The corpus will grow fastest through other people's
   corrections — and a citable, attributed dataset is worth more to your project than a secret one.
