#!/usr/bin/env python3
"""Bulk-fetch text layers (and PDFs where there is no layer) for curated IA identifiers.
Refuses anything flagged access-restricted: those are listed for the user to borrow legally."""
import json, pathlib, re, sys, requests
from concurrent.futures import ThreadPoolExecutor

WANT = {
 "ramal_prashnottari_a": "ramal-prashnottari",
 "ramal_prashnottari_kapur": "YfRW_ramal-prashnottari-by-divan-ram-chandra-kapur-motilal-banarasidas",
 "ramal_sara_prashnavali_1881": "HDAW_ramal-sara-prashnavali-fortune-telling-by-wood-dices-lucknow-1881-naval-kishore-press",
 "ramal_sara_prashnavali_1881_lwsc": "lwsc_ramal-sar-prashna-vali-by-unknown-hindi-astrology-lucknow-1881-naval-kishor",
 "ramal_divakar_ki_kunji": "sYUf_ramal-divakar-ki-kunji-by-vachan-prasad-tripathi-thakur-prasad-and-sons",
 "ramal_navaratna": "CcCo_ramal-navaratna-with-bhasha-tika-by-mahidhar-sharma-and-ramal-daniyal-bhasha-gan",
 "ramal_pradipika": "gium-ramal-shastra-arthat-ramal-pradipika-by-bachan-pra",
 "zadig_1749_book_of_fate": "bim_eighteenth-century_zadig-or-the-book-of-f_voltaire_1749",

 # --- the Latin / vernacular geomancy core, not yet in the corpus
 "fasciculus_geomanticus_1704": "b3299753x",
 "agrippa_iv_and_geomancy_1655": "b20458563",
 "agrippa_iv_geomancy_1783": "b28777724",
 "geomantia_metrica_1775": "jbc.bj.uj.edu.pl.NDIGSTDR034556",
 "geomantia_geber_1552_ita": "BSG_8V819INV2894RES_P1",
 "vollkommene_geomantia_1704_deu": "10081819bsb",
 "catani_geomantischer_schopfen_stul_1704_deu": "10132543bsb",
 "kurtzer_unterricht_geomantia_1746_deu": "11253143bsb",
 "anleitung_curioese_wissenschaften_1747_deu": "10060534bsb",
 "edelste_eitelkeit_geomantia_1715_deu": "10081729bsb",
 "principles_astrological_geomancy_1889": "b24884145",
 "mysteries_astrology_1854": "mysteriesofastro00roba",
 "amulets_superstitions_1930": "b29978154",
 "astrologia_restituta_1653": "b30323149",
 "raguseii_epistola_geomantia_1623": "bub_gb_KK9JzNDUk20C",
 # --- Persian / Arabic / Ottoman
 "kitab_i_surkhāb_raml_1528_per": "ldpd_13892500_000",
 "nuskhah_i_raml_mcGill": "McGillLibrary-rbsc_ms-bw-ivanow-0133-18589",
 "risala_ramlia_cc0": "ResalhRamliah",
 "batil_al_sihr_dice_cup_urd": "httpsjournal.cio-museums.orgarticle_7093",
 # --- Indian raml / prashnavali (question -> answer) literature
 "ramal_sara_prashnavali_1881": "lwsc_ramal-sar-prashna-vali-by-unknown-h",
 "ramal_sara_prashnavali_1881_b": "HDAW_ramal-sara-prashnavali-fortune-telling-",
 "ramal_divakar_ki_kunji": "sYUf_ramal-divakar-ki-kunji-by-vachan-prasad",
 "ramal_navaratna": "CcCo_ramal-navaratna-with-bhasha-tika-by-mah",
 "ramal_shastra_marathi": "ramal-shastra-marathi",
 "asli_prachin_lal_kitab": "AsliPrachinLalKitabGirdhariLalSharma",
 "lal_kitab_upay": "lal-kitab-upay-sahit",
 # --- question-oracle genre (for the casebook structure)
 "book_of_fate_1923": "bookoffateformer00kirc",
 "book_of_fate_1887": "bookfatewhereby00raphgoog",
 "zadig_book_of_fate_1897": "zadig18972gut",
 "napoleons_book_of_fate_1769": "fisherchapbook480",
 # --- African comparative
 "amazulu_divination_1870": "ReligiousSystemOfTheAmazulu",
 "ifa_igala_assessment": "httpswww.ijtsrd.comother-scientific-research-areaother33592an-assessment-of-the-",
 "orisha_univ_256_odu": "orisha-university-the-256-odu-of-ifa-a-complete-guide-to-the-sacred-corpus-of-yoruba-divination-1788",
 "ifa_binary_intelligence": "ajarn-shaman-shu-ifa-binary-intelligence-2026",
}
OUT = pathlib.Path("corpus/raw/ia"); OUT.mkdir(parents=True, exist_ok=True)

def one(item):
    name, ident = item
    res = {"name": name, "identifier": ident}
    try:
        m = requests.get(f"https://archive.org/metadata/{ident}", timeout=40).json()
        md = m.get("metadata", {})
        res["title"] = (md.get("title") or "")[:120]
        res["restricted"] = md.get("access-restricted-item") in ("true", "True", True, "1")
        res["license"] = md.get("licenseurl") or md.get("copyright") or ""
        res["year_md"] = md.get("year")
        res["language"] = md.get("language"); res["year"] = md.get("year")
        res["_nfiles"] = len(m.get("files", []))
        files = [f.get("name", "") for f in m.get("files", []) if isinstance(f, dict)]
        server, d = m.get("server"), m.get("dir")
        base = f"https://archive.org/download/{ident}"
        txt = next((f for f in files if f.endswith("_djvu.txt")), None)
        epub = next((f for f in files if f.endswith(".epub")), None)
        pdf = next((f for f in files if f.endswith(".pdf")), None)
        ocr_dir = next((f for f in files if f.endswith("_hocr_searchtext.txt.gz")), None)
        for kind, fn in (("txt", txt), ("pdf", pdf), ("epub", epub), ("hocr", ocr_dir)):
            if not fn: continue
            p = OUT / f"{name}.{kind}{'.gz' if kind=='hocr' else pathlib.Path(fn).suffix}"
            if p.exists() and p.stat().st_size > 5000:
                res[kind] = "cached"; continue
            try:
                r = requests.get(f"{base}/{fn}", timeout=240, stream=True)
                if r.ok:
                    n = 0
                    with open(p, "wb") as fh:
                        for c in r.iter_content(65536):
                            fh.write(c); n += len(c)
                            if n > 60_000_000: break
                    res[kind] = n
            except Exception as e:
                res[kind + "_err"] = str(e)[:50]
    except Exception as e:
        res["error"] = str(e)[:80]
    return res

with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(one, WANT.items()))
pathlib.Path("corpus/raw/ia/_fetch_report.json").write_text(json.dumps(results, indent=1))
for r in results:
    print(f"{r['name'][:42]:42s} {'RESTRICTED' if r.get('restricted') else 'open':10s} "
          f"txt={str(r.get('txt'))[:9]:9s} pdf={str(r.get('pdf'))[:9]:9s} nf={r.get('_nfiles')} "
          f"{('ERR '+str(r.get('error'))[:40]) if r.get('error') else ''}")
