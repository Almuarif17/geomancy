# Feeding an app from this library

Everything an app needs is under `library/dataset/`. There is no server to run: the files are the
API, and `bundles.json` tells each screen which files to download.

```
library/dataset/
├── manifest.json          counts, licence summary, sha256 of every file
├── bundles.json           screen -> files + bytes + content hash (CDN cache key)
├── openapi.yaml           the same contract in OpenAPI 3.1, if you do host it
├── shards/passages.jsonl  1,140 sourced passages {work, kind, figure, house, locator, text, confidence}
├── shards/rules.jsonl     23 computable techniques
├── index/by_outcome.jsonl ONE ROW PER ANSWERABLE OUTCOME (22)
├── index/by_figure.jsonl  per figure: attributes, judge attainability, 12 house rulings, passage ids
├── index/by_house.jsonl   per house: scope, folio, figure->verdict table, perfection base rates
├── index/by_work.jsonl    provenance drill-down
├── tables/*.json|yaml       the kb artefacts an app needs, copied so the dataset is self-contained
├── evaluation.json          accuracy numbers for this exact build
└── geomancy.sqlite          FTS5 full-text search over passages
```

## Casting, then sorting by outcome

```python
import sys; sys.path.insert(0, "engine")
import deep_read, export_reading, retrieve

mothers = ["Carcer", "Amissio", "Caput Draconis", "Populus"]
reading = export_reading.reading(mothers, "marriage", day="Monday", hour=3)
```

`reading["verdict"]` is the one object a results screen renders first:

```json
{"does_it_perfect": "qualified", "mode": "Translation", "base_rate_pct": 18.803,
 "news_value": "ordinary", "judge": "Conjunctio", "sentence": "Via", "blockers": [],
 "planetary_gate": "UNKNOWN", "trace_heads": 4,
 "headline": "YES, but only through outside help (by Amissio) - and the helper is ill-dignified, so expect an unpleasant passage"}
```

`base_rate_pct` is the differentiator: the mode is priced against all 65,536 casts, so the UI can
say "this happens in 6.2% of casts" instead of "49%, which means nothing". `blockers` carries the
validity gates (recast / distrust / suspend); `planetary_gate` is UNKNOWN until the app supplies the
weekday and temporal hour (`engine/elections.py`).

## Choosing what to fetch for a screen

```python
retrieve.screen("verdict")       # {"files": [...], "bytes": 360448, "resolved": [{path, bytes, sha256}]}
retrieve.by_figure("Populus")    # pattern, attributes, judge attainability, house rulings, passage ids
retrieve.by_house(7)             # Uxor: scope, folio 47v, figure->verdict, perfection base rates, outcomes
retrieve.outcomes("love")        # the outcome rows whose key/label match
retrieve.passages(figure="Carcer", house=4, limit=5)
retrieve.coverage()              # what the library can and cannot answer, for honest empty states
```

CLI, for humans and shell scripts:

```bash
python3 engine/retrieve.py --topic marriage --json
python3 engine/retrieve.py --figure Populus --json
python3 engine/retrieve.py --screen reading --json
python3 engine/retrieve.py --search buried --limit 5
```

## Outcome routing (22 outcomes shipped)

Each row already contains the quesited house, the houses to read alongside it, the ruling table for
every figure in that house, the exact base rates, the passage ids, and **which rules to apply**:

```json
{"outcome": "marriage", "quesited_house": 7, "extra_houses": [5], "triplicities": [[7, 8, 12]],
 "priors_key": "question_in_house_VII", "base_rates": {"no relation": {"pct": 49.254}, ...},
 "ruling_table": {"Acquisitio": "Good company and defeat of an enemy. And good marriages...", ...},
 "significator_rules": ["perfection", "significators_by_house", "parentage", "house_quality_tiebreak", "timing"],
 "always_read": ["validity_gates", "reconciler", "via_puncti", "motus_and_passing"]}
```

If an app sends a topic we do not have, `reading["flags"]` says so - a quiet empty bank is the one
thing this library refuses to produce.

## Rendering rules

* **Show `gaps[]`** as an explicit "the source does not say" - it lists every unfilled table cell
  (e.g. `who.trade_or_disposition: not in the extracted source table`).
* **Names ending `*`** are contested labels (Puer/Puella are swapped between Britannica/Golden Dawn
  and Digital Ambler/Skinner). `kb/figures.yaml` records both readings; do not pick one silently.
* **`kind: NAMED_ONLY`** rules (`hidden_figure_of_a_house`, `suffrages_and_lots`) are documented but
  deliberately not computed - never render them as if they were computed.
* Cache-bust with the `sha256` in `bundles.json`; a release is content-addressed, so an app can pin
  `manifest.json` and verify every file.
