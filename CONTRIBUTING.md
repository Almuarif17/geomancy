# Contributing

The whole point of this repository is that a claim can be traced to a page. So the bar for an addition is
mechanical, not stylistic.

## Adding a ruling or passage
1. It must come from a **public-domain or openly licensed** work (bucket A of
   `LICENSE_POLICY.md`). If you are unsure, add it to the cite-only list instead — do not paste text.
2. Every row needs `work`, `kind`, `locator` (folio/leaf/page — what a reader would cite), `text`,
   `confidence`. `library/tools/validate.py` fails the build without them.
3. Keep the source text **as printed** (long-s normalisation is fine, and say so in the extract script);
   do not modernise wording. A tidy quotation is a false quotation.
4. Note the OCR method if you made it (`scripts/ocr_pages.py`, model, dpi, psm). Confidence strings like
   "LOW (OCR pointer, verify on the image)" are welcome — they are how this stays honest.

## Adding a technique (`kb/techniques.yaml`)
- `procedure`: the algorithm, in imperative steps, complete enough to implement without guessing.
- `source`: work + folio/page, or the edition and translator.
- `conf`: `HIGH` (stated explicitly in a source I read in full) / `MED` (secondary or single-sourced) /
  `LOW`, or `status: NAMED_ONLY` when a source names the technique but never states how to do it.
  **`NAMED_ONLY` entries are not implemented, and must stay unimplemented.** That is not laziness; it is
  the difference between a documented tradition and an invention with citations bolted on.
- Add a check to `engine/test_deep_read.py` that pins the behaviour — including the invariants over all
  65,536 casts, which is where several wrong-but-plausible rules have already died.

## Disagreements between sources
Record them side by side (see `naming_conflict` and `planet_attribution_conflict` in `kb/figures.yaml`) and
let the output show both. Do not average two traditions into a third one that nobody practised.

## Living traditions
Do not add Ifá verses, ẹ̀wọ, ẹbọ, or comparable material from a lineage without that lineage's consent and
credit. See `NOTICE`. This is not a licensing technicality.

## Pull requests
`make check` must pass. If you changed a rule, paste a before/after reading for the demo cast so the
effect on output is visible.

## Before you commit

```bash
git config core.hooksPath scripts/git-hooks   # runs the leakage scan + the library gate on every commit
```

CI enforces the same gates, so this only saves you a round trip.

## Adding a resource (the only sanctioned path)

1. Drop the file in `corpus/inbox/` (never in `kb/`, never in `library/dataset/`).
2. `make triage` - it hashes, sniffs year/language/signature words and appends a **proposal** to
   `registry/proposed.jsonl` with a bucket, a disposition and its reasons. It changes nothing else.
3. Read the front matter yourself, then move the row into `registry/works.jsonl` with a
   `stable_id` (IA identifier, ARK, DOI, bitstream UUID or shelfmark - not a bare URL),
   a `licence_bucket`, a `disposition`, a `retrieval` recipe and a `why_trusted` line.
4. `make sync` to pull the text layer for `full` works, extract into `kb/`, then `make full`.

`make check` will fail you if a passage cites a work that is not registered, if a `full` row is not
bucket A, or if a HIGH-confidence technique has no executable case. That is intentional: those three
gates are what let the corpus grow at speed without becoming unsellable or unfalsifiable.

## Adding a rule

`kb/techniques.yaml` needs `answers`, `conf`, `source` (work + folio/page), and the procedure. Then
add a case to `kb/rule_tests.yaml` via `scripts/build_rule_tests.py` and mark it `proof` only if you
derived the expectation from the source or from `engine/oracle.py` - otherwise `pin`.
