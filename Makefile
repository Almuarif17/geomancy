PY ?= python3

.PHONY: help build check test read ocr clean core-facts

help:
	@echo "make build   regenerate library/dataset (jsonl + manifest) from kb/ + extracts"
	@echo "make check   licence + provenance + schema + engine gates (CI runs this)"
	@echo "make test    engine checks only (23 assertions, incl. exhaustive over all 65,536 casts)"
	@echo "make read    print a sample reading (markdown) for the demo cast"
	@echo "make json    print the app-facing JSON reading for the demo cast"
	@echo "make ocr     example: OCR one page of a scan (set PDF= and PAGE=)"

core-facts:
	$(PY) library/tools/build_core_facts.py

build: core-facts
	$(PY) library/tools/build_dataset.py

check: build
	$(PY) library/tools/check_schema.py
	$(PY) library/tools/validate.py

test:
	$(PY) engine/test_deep_read.py
	$(PY) tools/test_shield.py

read:
	$(PY) engine/deep_read.py --mothers "Carcer,Amissio,Caput Draconis,Populus" \
	  --topic travel_journey --day Wednesday --hour 4

json:
	$(PY) engine/export_reading.py --mothers "Carcer,Amissio,Caput Draconis,Populus" \
	  --topic travel_journey --out reading.json

ocr:
	@test -n "$(PDF)" || { echo "usage: make ocr PDF=/path/scan.pdf PAGE=172 LANG=frk+eng"; exit 1; }
	$(PY) scripts/ocr_pages.py $(PDF) $(PAGE) /tmp/ocr-out $(LANG) lat+eng 400

clean:
	rm -rf library/dataset/*.sqlite **/__pycache__ reading.json

index:            ## rebuild the outcome indexes + app bundles
	python3 engine/retrieve.py --build
	@python3 library/tools/finalize_dataset.py
	@python3 engine/evaluate.py --json library/dataset/evaluation.json
	@python3 library/tools/check_docs_consistency.py

types:            ## regenerate types/geomancy.d.ts and openapi.yaml from library/schema/
	python3 library/tools/gen_types.py

rules:            ## execute every rule's test case
	python3 library/tools/run_rule_tests.py

eval:             ## differential sweep: engine vs engine/oracle.py over all 65,536 casts
	python3 engine/evaluate.py --json library/dataset/evaluation.json

sync:             ## fetch whatever the registry says may be carried in full
	python3 library/tools/sync_corpus.py

health:           ## check every registered source still resolves (no writes)
	python3 library/tools/sync_corpus.py --check

triage:           ## propose a licence bucket + disposition for corpus/inbox/
	python3 library/tools/triage.py

full: build index types eval rules check   ## everything a release needs
.PHONY: index types rules eval sync health triage full
