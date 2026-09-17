"""Download IA full-text layers for target geomancy sources; score quality; flag for OCR."""
import json, re, requests, os, pathlib

TARGETS = {
 "heydon_theomagia_1663":   "theomagiaortempl00heyd",
 "cattan_geomancie_1591":   "b30337860",
 "cattan_geomancie_1608":   "bim_early-english-books-1475-1640_the-geomancie-of-maister_cattan-christophe-de_1608",
 "opus_geomantiae_1638":    "BSG_8V821INV2896FA",
 "fr_geomancie_nomancie":   "b3299414x",
 "agrippa_ocp_book2":       "HenryCorneliusAgrippaThreeBooksOfOccultPhilosophyBook2",
 "BSG_ms_occult_sciences":  "BSG_MS2226",
}
KW = ["geomanc","figure","mother","daughter","nieces","nephew","witness","judge",
      "house","judgment","judgement","shield","acquisit","amissio","populus","via","puella","puer"]
raw = pathlib.Path("corpus/raw"); raw.mkdir(parents=True, exist_ok=True)
report = {}
for name, ident in TARGETS.items():
    url = f"https://archive.org/download/{ident}/{ident}_djvu.txt"
    rec = {"identifier": ident, "txt_url": url}
    try:
        r = requests.get(url, timeout=180)
        rec["http"] = r.status_code
        if r.ok and len(r.text) > 2000:
            p = raw / f"{name}.txt"; p.write_text(r.text, encoding="utf-8", errors="replace")
            low = r.text.lower()
            rec["bytes"] = len(r.text)
            rec["kw_hits"] = {k: low.count(k) for k in KW if low.count(k) > 0}
            rec["words"] = len(r.text.split())
        else:
            rec["needs_ocr"] = True
    except Exception as e:
        rec["error"] = str(e)[:120]; rec["needs_ocr"] = True
    # metadata: page count + whether images exist
    try:
        m = requests.get(f"https://archive.org/metadata/{ident}", timeout=60).json()
        rec["title_short"] = (m.get("metadata", {}).get("title") or "")[:70]
        rec["pages"] = m.get("metadata", {}).get("pagecount")
    except Exception:
        pass
    report[name] = rec
print(json.dumps(report, indent=1))
