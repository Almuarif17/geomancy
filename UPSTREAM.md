# UPSTREAM — free hosting that works from anywhere, with the exact commands

Everything here is a free tier, no card required except where noted. Do them in order; step 1 alone
gives you "accessible anywhere".

## 1. Git repo as the spine (5 minutes)

```bash
cd geomancy
git init -q && git add -A && git commit -qm "geomancy library: kb, extracts, engine, gates"
# GitHub / GitLab / Codeberg: create an empty repo named geomancy-library, then:
git branch -M main
git remote add origin git@github.com:USERNAME/geomancy-library.git
git push -u origin main
```

`.gitignore` for the repo (keep the repo light; the scans stay external):
```
corpus/raw/**/*.pdf
corpus/raw/**/*.pdf.pdf
corpus/raw/**/*.epub*
work/
__pycache__/
*.sqlite
```
**Why these exclusions:** a git host will not love you for 500 MB of scans, and the scans are
re-downloadable from their own repositories. What you commit is the *knowledge*: texts you transcribed,
rules, extracts, provenance. Then the repo is a few MB and clones in seconds on any network.

## 2. Serve the data with a CDN, not a server

Once the repo is public, jsDelivr mirrors every file at a fast, cached, HTTPS URL — no origin, no bill:

```
https://cdn.jsdelivr.net/gh/USERNAME/geomancy-library@main/library/build/shards/passages.jsonl
https://cdn.jsdelivr.net/gh/USERNAME/geomancy-library@main/library/build/manifest.json
https://cdn.jsdelivr.net/gh/USERNAME/geomancy-library@main/kb/techniques.yaml
```

Pin a release instead of `main` for production: `@v1.0.0`. App update protocol:

1. fetch `manifest.json`; 2. compare `files{}` hashes to the local copy;
3. download only the changed shards; 4. rebuild the local SQLite index.
That is a versioned content library with no backend, and it works offline after first install.

## 3. Static app surface (still free)

```bash
npm i -g wrangler            # or use the Pages UI; Cloudflare Pages, GitHub Pages, Netlify all work
# GitHub Pages, zero setup:
git mkdir -p docs && cp library/build/manifest.json docs/  # plus your app bundle
gh api repos/USERNAME/geomancy-library/pages -X POST -f source[branch]=main -f source[path]=/docs
```

## 4. Publish your own bundles to archive.org (free, permanent, and it gives you a citation)

Uploading your extracted text and notes to Internet Archive is the cheapest "library card" there is:
permanent URLs, full-text search over your own extracts, and a stable identifier to cite in the app.

```bash
pip install internetarchive
ia configure                                    # uses your free account
# one bundle per work: your transcription/extracts + a README + metadata
ia upload geomancy-alfagini-quaestiones library/build/ \
   --metadata="collection:opensource" --metadata="license:CC0-1.0" \
   --metadata="title:Alfagini Quaestiones Geomantici - extracted rulings (leaf-cited)"
```
Set `license` honestly: your *extracts and notes* are yours (MIT for code, CC0 for definitions and derived
arithmetic, CC BY-NC for curated text - the same three layers as `LICENSING.md`); the underlying scan is not
yours
to re-license — link to its identifier instead of uploading the images.

## 5. Make releases citable (this is what turns a repo into a library)

Zenodo + the GitHub integration: enable it once on the repository, then every `git tag -a v1.2.0` and
`git push --tags` produces a **DOI** for that exact state of the dataset. Free, permanent, and it means
your corpus can be cited by other people — which is how it grows without you.

## 6. Search/records when JSONL stops being enough

Start on free tiers, in this order, and move only when a number forces you to:

| tier | free allowance | use it for |
|---|---|---|
| SQLite in the app | unlimited | everything until you have accounts |
| **Turso** (libSQL) | 9 GB, generous reads | sync + per-user reading history |
| **Supabase** | 500 MB Postgres, auth, storage | accounts, payments later, row-level security |
| **Neon** | serverless Postgres | if you prefer bare Postgres |
| **Cloudflare R2** | 10 GB, no egress fee | shard blobs, page images you are allowed to host |
| **Backblaze B2** | 10 GB | mirror of the above |

## 7. IIIF: how to deep-link a folio instead of shipping it

Most of these hosts expose IIIF. Build a link, not a file:

```
https://archive.org/details/<IDENTIFIER>/page/n<PAGE>/mode/2up     # readable scan, no storage on you
https://gallica.bnf.fr/ark:/12148/<ARK>/image                      # BnF
https://digitalcollections.universiteitleiden.nl/...                # Leiden (where SurkhAb raml lives)
https://www.digitale-sammlungen.de/en/view/bsb<NNNNNNNN>?page=,     # Munich (the German Geomantia)
```
Store `{"work": "fasciculus", "locator": "leaf 474", "deep_link": "..."}` and your app's "why?" button
becomes a jump to the 1704 page itself. That single affordance will out-market every competitor.

## 8. CI so the corpus cannot rot

Put this at `.github/workflows/validate.yml`:

```yaml
name: gate
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install pyyaml requests beautifulsoup4 lxml pymupdf
      - run: python3 scripts/ia_fetch.py --check-only || true     # licences may change upstream
      - run: python3 library/tools/build_dataset.py
      - run: python3 library/tools/validate.py
```
If a licence changes upstream or a copyrighted passage sneaks in, the build goes red and nothing ships.

## 9. Backups that cost nothing and are actually restorable
- `git push` to **two** hosts (GitHub + Codeberg) — same remote, no extra work after `git remote add second …`.
- One `ia upload` of each release tarball per year: durable, searchable, free.
- Keep the **SQLite build out of git**; it is reproducible from `build_dataset.py`, and reproducibility is
  cheaper than storage.

## 10. Two rules worth obeying from day one
1. **Never let the app invent.** If the JSON says `gaps: ["where.direction: not attested"]`, the UI shows
   exactly that. Confidence is a visible field, not a tone of voice.
2. **Every rule needs a test.** `engine/test_deep_read.py` (23 checks, incl. exhaustive over all 65,536
   casts) is the reason this library can grow by hundreds of works without becoming a rumour machine.
