# Setup (re-run after any sandbox/session reset)

Workspace files and apt packages persist; **pip installs do not**. One-liner:

```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-ara tesseract-ocr-fas \
  tesseract-ocr-hin tesseract-ocr-san tesseract-ocr-urd tesseract-ocr-deu tesseract-ocr-ita \
  tesseract-ocr-lat tesseract-ocr-por
pip install pymupdf pyyaml requests beautifulsoup4 lxml pandas
```

Why these language packs: the corpus is Latin (1655/1704), Fraktur/blackletter German (1704/1746),
Italian (1552), Persian + Arabic + Urdu (raml manuscripts), Devanagari (Hindi prashnavali
literature), and English. `lat` alone lifted the recoverable-word count on a Cattan page from 4/11
(the archive's own layer) to 8/11.

Verification after setup:
```bash
cd geomancy && python3 engine/test_deep_read.py   # expect: FAILURES: 0
```

## After a fresh clone

```bash
pip install -r requirements.txt     # pyyaml + jsonschema (tesseract only if you re-OCR)
make build                          # generates library/dataset/geomancy.sqlite - not tracked in git
make full                           # build + indexes + types + eval + gates
git config core.hooksPath scripts/git-hooks   # optional: run the gates before every commit
```

`library/dataset/shards/*.jsonl`, `index/*.jsonl`, `tables/`, `bundles.json` and `evaluation.json`
**are** tracked, so a clone already has everything an app needs; only the SQLite search index is
generated. `corpus/raw/` (the fetched text layers, 60 MB+) is never tracked: `make sync` rebuilds it
from `registry/works.jsonl`, and `corpus/manifest.lock.json` records the sha256 of what was fetched.
