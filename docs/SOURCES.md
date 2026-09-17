# Where the material lives, and how it stays reachable

Three questions decide every resource: **will this URL still work in five years**, **can a program
fetch it without a human**, and **may we ship it**. `registry/works.jsonl` records the answer per
work; `library/tools/validate.py` refuses a build that breaks the rules below.

## Host tiers, by durability

| Tier | Host | Addressed by | Programmatic access | Verdict |
|---|---|---|---|---|
| 1 | **archive.org** | item identifier (`b3299753x`) | `/metadata/{id}` (JSON, lists real filenames) + `/download/{id}/{id}_djvu.txt`, IIIF page images at `/details/{id}/page/n{N}` | primary corpus host: identifier-addressed, self-mirrored, 25+ years of stable URL shape |
| 1 | **Gallica (BnF)** | **ARK** `ark:/12148/…` | `/ark:/…/image`, `/textVersion`, IIIF manifest; SRU for search | best French return; ARK is a handle, so redesigns cannot break it (SRU needs no key for reads; anonymous search returned 403 here, so use the resolver URLs) |
| 1 | **HathiTrust** | `pst`/AA id | BibTex API, page text for PD items where permitted | duplicate copy of most pre-1900 prints - use as the second opinion when IA's OCR layer is thin |
| 1 | **BSB digitale-sammlungen** | `bsb` number | IIIF manifest + `?page={n}` | the German Hartmann/Opus family at source quality |
| 1 | **Leiden UB / McGill DDRS / Beinecke** | shelfmark or ARK | IIIF manifests, some METS | the Arabic/Persian raml manuscripts; IIIF is stable, per-page fetch only |
| 2 | **Institutional repositories** (Toronto scholaris, quest-journal mirrors) | handle / **bitstream UUID** | `server/api/core/bitstreams/{uuid}` (verified alive) | theses are the richest open scholarship we have; deposit licence permits our use, mirrors do move |
| 2 | **DOI (Brill, Brepols)** | DOI | `doi.org` resolves; content is paywalled | cite, never quote |
| 3 | **Personal sites, blogs, wikis** (serenapowers, digitalambler, kitchentoad, caduceus) | URL | none | technique leads only; re-host the *finding* in `kb/` with the URL in `source:` and treat loss as expected |
| 4 | **Scans of in-copyright books on file hosts** | - | - | **never**: inspected, deleted, named in `corpus/raw/ia3/_REMOVED_because_in_copyright.txt` |

**The rule that keeps links intact is not "pick a good site" - it is "store identifiers, not
URLs."** A row's `stable_id` is an IA identifier, an ARK, a bitstream UUID, a DOI or a shelfmark.
`sync_corpus.py` rebuilds the URL from the recipe, so a redesign costs us a resolver function, not
the corpus.

## Automation: no manual fetching

* `make sync` → `library/tools/sync_corpus.py`: for every row with `disposition: full` and
  `licence_bucket: A`, ask `/metadata/{id}` which file exists, download the text layer into
  `corpus/raw/{id}.txt`, and write `corpus/manifest.lock.json` with bytes + `sha256` +
  `retrieved_at`. Re-runs are no-ops; `--force` re-fetches; `--only id` targets one work.
* `make health` → the same tool with `--check`: resolves every registered identifier and prints
  `alive`/`DEAD`. CI runs it weekly (`sources-health.yml`) and fails on `0 problems` missing.
* Bulk discovery (the 259 relevant IA items behind our 23) is
  `scripts/ia_harvest_all.py` + `corpus/ia/IA_CATALOG.md`; advanced-search is metadata-only, so
  catalog rows carry identifiers, never scraped prose.

## Triage: carry fully / summarise / cite / drop

| Disposition | Meaning | What lands in the repo | Current count |
|---|---|---|---|
| `full` | public-domain with a text layer | extracted passages in `library/dataset/shards/passages.jsonl`, each with `work` + `locator`; the text itself stays out of git (66 MB of bulk) and is re-fetchable via `make sync` | 9 works → {{num:passages}}1,140 passages |
| `summarize` | readable but not redistributable, or needs OCR first | notes and rules in `kb/` (`techniques.yaml`, `calatarama_grid.json`), never prose | 8 works (Persian/Arabic mss pending OCR: `nuskhah_raml_mcgill`, `surkhab_raml_leiden`, `risala_ramlia`) |
| `cite` | modern scholarship, the digging map | a `source:` string on a rule; zero quotes | 7 (`skinner`, `greer`, `regardie`, `charmasson`, `tannery`, `encislam_raml`, `binsbergen_1996`) |
| `drop` | in-copyright upload of a whole book | a line in `_REMOVED_because_in_copyright.txt` | 4 deleted, 3 registered as `drop` so nobody re-adds them |

`corpus/ia/IA_CATALOG.md` holds the wider sweep (99 open with a text layer, 16 borrow-only behind a
free account, 45 scan-only). Each of those 160 stays a *candidate* until a human promotes it into
`registry/works.jsonl`.

## Anything new goes through triage first

`make triage` reads `corpus/inbox/`, hashes each file, sniffs imprint year / language / signature
words, and appends a **proposal** to `registry/proposed.jsonl` with its reasons. It never edits
`works.jsonl`, never deletes, never uploads. If a proposal says "looks like the same text family as
`fasciculus_1704`", you have found a duplicate before it doubles the corpus.

## Corpus state (deliberate)

`corpus/raw/` (66 MB) is gitignored: bulk scans and text layers are reproducible from the registry,
so shipping them in git only bloats every clone. Tracked provenance: `corpus/ia/IA_CATALOG.md`,
`corpus/MANIFEST.md`, `corpus/manifest.lock.json`. If a disk dies: `make sync`, then `make check`.
