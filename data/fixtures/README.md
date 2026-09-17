# Fixtures — measured ground truth, not a transcription

Two live castings captured from a mobile geomancy app were used as the regression reference for this
project. Each value is the number of markers counted in a row of a house figure, read **top to bottom**
(`1` = a single marker, `2` = a pair), obtained by connected-component counting of the marker sprites
inside each cell with the label zone masked, then cross-checked against enlarged crops by eye.

| file | what |
|---|---|
| `chart2.json` | 15 houses of the first reference cast (the one whose Daughters differ from its Mothers, which is what made the nephew rule decidable) |
| `spread_rows.json` | 15 houses of the second cast (a "square" cast where Daughters equal Mothers) |

The source screenshots are **not redistributed here** — they are personal divination records. Anyone
reproducing these numbers needs their own castings; the tests only require the 15 patterns.

Why `spread_rows.json` is in the repo at all: on it, the classical nephew rule and a naive "repeat the
Mothers' sums" rule agree, so it is the counter-example that proves a rule is *determined* rather than
merely *compatible*. Both files together are what `engine/test_deep_read.py` checks 16/16 against.
