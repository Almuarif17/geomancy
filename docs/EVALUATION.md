# Accuracy audit of the active code (2026-09-17)

The question was "is the active code accurate?". Two instruments answer it, and both are in CI.

## 1. Differential verification — engine vs an independent implementation

`engine/oracle.py` re-codes the rules from the sources in the most literal way (no import of
`deep_read`, no shared helpers), and `engine/evaluate.py` runs both over the entire domain:

```
differential sweep over 65,536 casts  (exhaustive)
  chart            agree 65,536/65,536  100.00%
  sentence         agree 65,536/65,536  100.00%
  via_puncti       agree 65,536/65,536  100.00%
  projection       agree 65,536/65,536  100.00%
  part_of_fortune  agree 65,536/65,536  100.00%
  motus            agree 65,536/65,536  100.00%
  judge_parity     agree 65,536/65,536  100.00%
```

4.6 s on a laptop, in `make eval`, results pinned to `library/dataset/evaluation.json`.

## 2. Executable rule cases — 29 across 22 rules

`kb/rule_tests.yaml`, run by `make rules`. Each case declares its `strength`:

* **proof (20)** — the expectation follows from a stated source rule or from arithmetic checked
  against the oracle: e.g. `court.sentence == "Via"` because Conjunctio + Carcer = 1-1-1-1
  (al-Zanati's "from the first and the fifteenth"); 24 single dots → house XII (projection);
  72 points → house XII (Part of Fortune); `validity` must carry `SUSPEND` when Populus is Judge and
  `RECAST` when Cauda Draconis is in house I.
* **pin (9)** — "this is what the code does today", nothing more: table-lookup rules (who/where/when,
  triplicities, constitution). Upgrading a pin to a proof requires reading the folio.

Two preconditions were **found by search over all 65,536 casts** rather than guessed, because a test
that cannot fire proves nothing: a cast whose Judge is Populus (SUSPEND), and a cast whose head-row
trace dies at the witnesses (`formed == false`, endpoint `kind == "died"`).

## What the audit found and fixed

1. **`via_puncti` lost branches.** The old loop kept one line and *overwrote* the branch record at
   every split, so a trace that split at the witnesses and again at the nieces reported only the last
   split. Sources are explicit that a split must be followed ("two-headed" / *bicéphale*). The
   engine now follows every branch and returns `(path, branch_names, endpoints)`;
   `trace.via_puncti.endpoints` and `branch_count` are in the reading schema and required by
   `check_schema.py`. *Consequence for your own audited chart:* Carcer·Amissio·Caput·Populus is a
   **four-headed** way of the points, not a single line with one branch.
2. **Silent empty banks.** An unrecognised `topic` returned `{}` with no complaint. Now
   `flags[]` says the topic has no sub-question entry; and the topics an app will actually send
   (`theft`, `lost_item`, `treasure`, `missing_person`, `lawsuit`, `litigation`, `court_case`) are
   aliased in `engine/questions.py`.
3. **Contract drift.** `trace.via_puncti.endpoints` was computed but never written into the exported
   reading; caught by a rule case failing, not by review.
4. **Missing citation.** `suffrages_and_lots` (NAMED_ONLY) shipped with a note but no `source:`;
   `validate.py` now requires a source on *every* technique, implemented or not.
5. **Paths that a snapshot deletes.** The build wrote to `library/build/` (gitignored and excluded
   from workspace snapshots). Everything published now lives in `library/dataset/`, schemas in
   `library/schema/`, fixtures in `data/fixtures/`, examples in `examples/`.

## Also: why the GitHub scaffold was not usable as a base

`Almuarif17/geomancy@129aebd` (single commit) is a partial copy of this work: 31 tracked files, no
`engine/deep_read.py`, no `engine/questions.py`/`elections.py`, no `kb/figures.yaml`/`houses.yaml`,
no `data/fixtures/` — so its own CI run ends **failure**. Its `kb/techniques.yaml` is corrupted
(parses as a bare 10-item list, not `techniques: {…}`), and its `engine/export_reading.py` is a
stand-alone re-implementation (`generate_chart`, `compute_via_punti`) that no longer calls the rules
engine, so its "23 checks" test a copy rather than the library. `FINDINGS.md` there is 75 lines
against 321 here. Decision: keep this tree as source of truth, adopt its two good ideas
(`library/schema/`, root `examples/`) and its `test_case` concept — and leave its CI red no longer.

## What this does not prove

* Arithmetic and rule-shape are verified; **interpretive fidelity** is bounded by the extracts.
* Transcription is still the weak seam. The 142 Calatarama figure×house rulings and the 859 Hartmann
  answer cells are transcriptions, and a wrong cell is invisible to both instruments above.
  **Partly closed today:** `library/tools/check_hartmann_grid.py` measures the grid against its real
  shape (8 attainable Judges × 16 cofigures × 16 questions), and every extracted cell independently
  confirms the parity theorem - only even-pointed figures appear as judge, and all 8-of-16 blocks are
  the ones our enumeration produces. **Open:** the Carcer block (0/256) and 1,189 other cells, which
  need page-level OCR because IA's text layer for `b24884145` stops before the appendix (173 KB, two
  mentions of Carcer); and a cell-by-cell re-OCR diff of the 32 Calatarama leaves.
