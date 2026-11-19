# Privacy

Castings in this project came from real questions asked by a real person. The published record keeps only
what is analytically necessary:

- `data/fixtures/*.json` holds **patterns only** (rows of 1s and 2s) for two castings. No question text,
  no querent name, no date, no location, no device identifiers, no screenshots.
- `readings/` (generated reports against a live question) and `uploads/` (the screenshots) are
  **gitignored** and never committed.
- `docs/USAGE.md` and `docs/FINDINGS.md` describe the questions only in generic terms
  ("a relocation question"), because a reading plus a question is identifying in a small community.

The optional reader integrations have separate data flows:

- The Research desk sends the search phrase to Internet Archive or GitHub when you press a search button.
  Saved leads stay in that browser/app's `localStorage` unless you explicitly copy/export the shelf.
- The AI study note is opt-in per click. It sends the current chart and the displayed sourced claims to the
  endpoint configured by the server operator. A local Ollama endpoint keeps that request on your machine;
  a hosted endpoint receives it under that provider's terms. No AI request is made while casting or reading.
- The chart arithmetic and source-grounded reading continue to work without either integration.

If you are extending this repository: keep it that way. Store real client work outside the repo. If you
want example castings for docs or tests, generate them or abstract them to patterns, and never paste a
person's question next to the answer.
