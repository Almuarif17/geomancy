# Privacy

Castings in this project came from real questions asked by a real person. The published record keeps only
what is analytically necessary:

- `data/fixtures/*.json` holds **patterns only** (rows of 1s and 2s) for two castings. No question text,
  no querent name, no date, no location, no device identifiers, no screenshots.
- `readings/` (generated reports against a live question) and `uploads/` (the screenshots) are
  **gitignored** and never committed.
- `docs/USAGE.md` and `docs/FINDINGS.md` describe the questions only in generic terms
  ("a relocation question"), because a reading plus a question is identifying in a small community.

If you are extending this repository: keep it that way. Store real client work outside the repo. If you
want example castings for docs or tests, generate them or abstract them to patterns, and never paste a
person's question next to the answer.
