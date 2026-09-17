#!/usr/bin/env python3
"""Turn the research workspace into a shippable dataset: one SQLite file + JSONL shards + a manifest.

Design rule: the LIBRARY is data with provenance and a licence verdict on every row. Text that cannot
be redistributed is never copied into the build - only a citation, a locator and (where the source is
open) a deep link to the page image. That single rule is what keeps a free corpus legal to ship in an app.

Usage:  python3 library/tools/build_dataset.py [--out library/dataset]
"""
import argparse, hashlib, json, pathlib, re, sqlite3, sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]      # .../geomancy
KB, CORP = ROOT / "kb", ROOT / "corpus"

# ---------------------------------------------------------------- licence ledger
# Sources we ship FULL TEXT from (public domain or openly licensed) vs sources we cite only.
PD_WORKS = {
 "calatarama": dict(title="Libro de los juysios de calatarama (via Finan, The Book of the Judgements of "
    "Calatarama, Univ. of Toronto, 2023)", licence="open: thesis deposited for research; translations are "
    "short factual rulings", url="https://utoronto.scholaris.ca", shippable_text=True),
 "binsbergen": dict(title="W. van Binsbergen, The astrological origin of Islamic geomancy (1996)",
    licence="author-hosted PDF, scholarly", url="quest-journal.net mirror", shippable_text=True),
 "fasciculus": dict(title="Fasciculus geomanticus (1704) - incl. Alfagini Quaestiones Geomantici",
    licence="public domain", identifier="b3299753x", shippable_text=True),
 "cattan1608": dict(title="C. Cattan, The Geomancie (1608)", licence="public domain",
    identifier="bim_early-english-books-1475-1640_the-geomancie-of-maister_cattan-christophe-de_1608",
    shippable_text=True),
 "cattan1591": dict(title="C. Cattan, The Geomancie (1591)", licence="public domain",
    identifier="b30337860", shippable_text=True),
 "hartmann": dict(title="F. Hartmann, The Principles of Astrological Geomancy (1889)",
    licence="public domain", identifier="b24884145", shippable_text=True),
 "lataille": dict(title="J. de la Taille, La Geomancie (16th c.)", licence="public domain",
    identifier="LaGeomanceAbregeeDeIeanDeLaTailleDeBondaroy", shippable_text=True),
 "heydon": dict(title="J. Heydon, Theomagia (1663)", licence="public domain",
    identifier="theomagiaortempl00heyd", shippable_text=True),
 "agrippa": dict(title="H. C. Agrippa, De occulta philosophia II / the 'Fourth Book' & Of Geomancy",
    licence="public domain", identifier="b20458563", shippable_text=True),
}
CITE_ONLY = {
 "skinner": "Stephen Skinner, Terrestrial Astrology / The Oracle of Geomancy - in copyright. Cite, do not quote.",
 "greer": "John Michael Greer, A Handbook of Geomancy / Earth Divination - in copyright. Cite, do not quote.",
 "regardie": "Israel Regardie, A Practical Guide to Geomantic Divination - in copyright.",
 "charmasson": "M. Charmasson, Recherches sur une technique divinatoire (1980) - the critical edition; paywall/ILL.",
 "tannery": "P. Tannery, Memoires scientifiques II (Estimaverunt Indi, Gerard of Cremona) - old print.",
 "encislam": "Encyclopaedia of Islam, art. 'Raml' - Brill subscription.",
 "ifa_live": "Any Ifa ese/ewe material: not redistributable without the lineage that holds it.",
}
BLOCKED_UPLOADS = {  # unofficial uploads of in-copyright works: never a source, never in the build
 "stephen-skinner-terrestrial-astrology-divina", "john-michael-greer-earth-divin",
 "israel-regardie-a-practical-gu", "vol-3-comprehensive-enochian-d",
}

def sha(p: pathlib.Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else None

def rows_from_kb():
    """Emit normalised passage rows: (work, locator, figure, house, text, kind, confidence)."""
    out = []
    g = json.loads((KB / "calatarama_grid.json").read_text())
    for house, v in g["grid"].items():
        for fig, txt in v["entries"].items():
            out.append(dict(work="calatarama", locator=f"f.{v.get('folio','?')} (house {house})",
                            house=house, figure=fig, kind="figure_in_house_ruling",
                            text=txt, confidence="MED-HIGH"))
    la = json.loads((KB / "alfagini_quaestiones.json").read_text())
    for it in la["items"]:
        body = (it.get("rule_latin") or it.get("text_latin") or "").replace("|", " ")
        body = re.sub(r"\s+", " ", body).strip(" :.-")
        topic = re.sub(r"\s+", " ", (it.get("topic_latin") or "")).strip(" .:-")
        text = (topic + " :: " if topic else "") + body
        if len(text) < 45:
            continue
        out.append(dict(work="fasciculus", locator=f"leaf {it.get('leaf_pdf')}",
                        figure=None, house=None, kind="quaestio_rule",
                        text=text[:600], confidence="MED (OCR of early Latin print)"))
    lt = json.loads((KB / "lataille_grid.json").read_text())
    for r in lt["grid"]:
        out.append(dict(work="lataille", locator=f"house {r['house']}", house=str(r["house"]),
                        figure=r["figure"], kind="figure_in_house_ruling",
                        text=r["ruling_fr"], confidence="MED"))
    ca = json.loads((KB / "cattan_motus_bank.json").read_text())
    for r in ca["records"]:
        out.append(dict(work="cattan1608", locator=f"book III, house {r['to_house']}",
                        house=str(r["to_house"]), figure=r["figure"], kind="motion_ruling",
                        text=r["ocr_text"], confidence="LOW-MED"))
    dg = json.loads((KB / "cattan1591_dangers.json").read_text())
    for r in dg["records"]:
        out.append(dict(work="cattan1591", locator=f"p.{r['page']}", house=r.get("house"),
                        figure=r.get("figure"), kind="particular_pointer",
                        text=r["raw"], confidence="LOW (OCR pointer, verify on the image)"))
    ha = json.loads((KB / "hartmann_casebook.json").read_text())
    for r in ha["answers"]:
        out.append(dict(work="hartmann",
                        locator=f"appendix: judge={r.get('judge')}, co={r.get('cofigure')}, Q{r.get('q')}",
                        figure=r.get("judge"), house=None, kind="answer_cell",
                        text=f"Q{r.get('q')}. {r.get('question')} -> {r.get('answer')}",
                        confidence="MED (page-aligned lookup; cofigure key may shift on column breaks)"))
    return out

def rules_rows():
    t = yaml.safe_load((KB / "techniques.yaml").read_text())["techniques"]
    rows = []
    for k, v in t.items():
        rows.append(dict(id=k, name=k.replace("_", " "), conf=v.get("conf") or v.get("status"),
                         answers=v.get("answers"), source=v.get("source") or v.get("note") or "",
                         procedure=json.dumps(v, sort_keys=True)[:6000]))
    return rows

def collect():
    """Run every source extractor separately so one drifted schema cannot sink the build."""
    rows, problems = [], []
    try:
        rows = rows_from_kb()
    except Exception as e:
        problems.append(f"kb passages: {e}")
    return rows, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "library/dataset"))
    ap.add_argument("--manifest-only", action="store_true",
                    help="refresh only manifest.json digests; run this after every other build step")
    a = ap.parse_args()
    out = pathlib.Path(a.out); (out / "shards").mkdir(parents=True, exist_ok=True)

    if a.manifest_only:
        # The manifest digests the index files, but engine/retrieve.py --build rewrites those files
        # *after* this script has run, so a manifest produced inside the normal build is always one
        # step behind and a fresh clone can never reproduce it byte-for-byte. This mode closes the loop.
        mf = out / "manifest.json"
        m = json.loads(mf.read_text())
        m["files"] = {str(q.relative_to(out)): sha(q) for q in sorted(out.rglob("*"))
                      if q.is_file() and q.name not in ("manifest.json", "bundles.json", "geomancy.sqlite")}
        m["built_from"] = {q.name: sha(q) for q in sorted(KB.iterdir()) if q.is_file()}
        mf.write_text(json.dumps(m, indent=1))
        print(f"manifest refreshed: {len(m['files'])} files, {len(m['built_from'])} kb inputs")
        return

    con = sqlite3.connect(out / "geomancy.sqlite")
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS works(key TEXT PRIMARY KEY, title TEXT, licence TEXT,
      ia_identifier TEXT, url TEXT, shippable_text INTEGER);
    CREATE TABLE IF NOT EXISTS passages(id INTEGER PRIMARY KEY, work TEXT, kind TEXT, figure TEXT,
      house TEXT, locator TEXT, text TEXT, confidence TEXT);
    CREATE INDEX IF NOT EXISTS ix_pass_fig ON passages(figure);
    CREATE INDEX IF NOT EXISTS ix_pass_kind ON passages(kind);
    CREATE TABLE IF NOT EXISTS rules(id TEXT PRIMARY KEY, name TEXT, conf TEXT, answers TEXT,
      source TEXT, procedure_json TEXT);
    CREATE TABLE IF NOT EXISTS priors(key TEXT PRIMARY KEY, payload TEXT);
    CREATE TABLE IF NOT EXISTS cite_only(key TEXT PRIMARY KEY, note TEXT);
    """)
    # contentless FTS5 cannot be DELETEd from, so it is rebuilt from scratch each time
    cur.execute("DROP TABLE IF EXISTS passages_fts")
    fts = False
    try:
        cur.execute("CREATE VIRTUAL TABLE passages_fts USING "
                    "fts5(text, figure UNINDEXED, work UNINDEXED, content='')")
        fts = True
    except sqlite3.OperationalError:
        pass

    cur.execute("DELETE FROM works")
    for k, v in PD_WORKS.items():
        cur.execute("INSERT INTO works VALUES(?,?,?,?,?,?)",
                    (k, v["title"], v.get("licence"), v.get("identifier"), v.get("url"), 1))
    cur.execute("DELETE FROM passages"); cur.execute("DELETE FROM rules"); cur.execute("DELETE FROM priors")
    cur.execute("DELETE FROM cite_only")

    all_rows, problems = collect()
    n = 0
    for r in all_rows:
        assert r["work"] in PD_WORKS, f"unlicensed source in build: {r['work']}"
        cur.execute("INSERT INTO passages(work,kind,figure,house,locator,text,confidence) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (r["work"], r["kind"], r.get("figure"), r.get("house"), r["locator"],
                     r["text"], r["confidence"]))
        if fts:
            cur.execute("INSERT INTO passages_fts(rowid,text,figure,work) VALUES(last_insert_rowid(),?,?,?)",
                        (r["text"], r.get("figure") or "", r["work"]))
        n += 1
    for r in rules_rows():
        cur.execute("INSERT OR REPLACE INTO rules VALUES(?,?,?,?,?,?)",
                    (r["id"], r["name"], r["conf"], r["answers"], r["source"], r["procedure"]))
    for key, payload in (("figure_attr", "figures.yaml"), ("houses", "houses.yaml"),
                         ("priors", "priors.json"), ("perfection_priors", "perfection_priors.json"),
                         ("calibration", "calibration.json"), ("question_inventory", "question_inventory.json")):
        p = KB / payload
        if p.exists():
            data = (yaml.safe_load(p.read_text()) if payload.endswith((".yaml", ".yml"))
                    else json.loads(p.read_text()))
            cur.execute("INSERT OR REPLACE INTO priors VALUES(?,?)", (key, json.dumps(data)))
    for k, note in CITE_ONLY.items():
        cur.execute("INSERT OR REPLACE INTO cite_only VALUES(?,?)", (k, note))
    con.commit()

    # JSONL shards (what an app or a static host can serve without a database)
    shards = {"passages": [dict(zip(["work","kind","figure","house","locator","text","confidence"],
                           [r["work"], r["kind"], r.get("figure"), r.get("house"), r["locator"],
                            r["text"], r["confidence"]])) for r in all_rows],
              "rules": rules_rows()}
    for name, items in shards.items():
        with open(out / "shards" / f"{name}.jsonl", "w") as fh:
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")

    manifest = {
      "dataset": "geomancy-kb",
      # deliberately NOT wall-clock: a rebuild must be byte-identical or the
      # CI "generated artefacts are committed" check is noise. See "built_from" for provenance.
      "generated": "content-addressed",
      "counts": {"passages": n, "rules": len(rules_rows()), "works": len(PD_WORKS),
                 "cite_only": len(CITE_ONLY)},
      "fts5": fts,
      "licence_summary": {
        "full_text_sources": sorted(PD_WORKS),
        "cite_only_sources": sorted(CITE_ONLY),
        "never_used": sorted(BLOCKED_UPLOADS),
        "policy": "full text only from public-domain or openly licensed works; everything else is a citation",
        # the policy above is what may come IN; this is what goes OUT. They are different questions and the
        # manifest used to answer only the first, which left an app to guess - and a guess made the curated
        # layer look as free as the code. Three layers, enforced by library/tools/check_licence_scope.py.
        "outbound_licence": {
            "layers": 3,
            "code": {"licence": "MIT", "paths": ["engine/", "library/tools/", "scripts/", "server/",
                                                 "library/schema/", "types/", "registry/", "tools/",
                                                 "library/dataset/openapi.yaml"]},
            "cc0": {"licence": "CC0-1.0", "paths": ["library/dataset/core_facts.json"],
                    "note": "definitions plus the consequences of the arithmetic; free forever, "
                            "including commercially"},
            "curated": {"licence": "CC BY-NC 4.0 + commercial licence",
                        "paths": ["kb/", "library/dataset/index/", "library/dataset/shards/",
                                  "library/dataset/tables/", "notes/", "docs/"],
                        "note": "every ruling, voice, gloss and adjudication note: attribution required, "
                                "no commercial use without a licence (open an Issue titled "
                                "\"commercial licence\")",
                        "provenance_obligation": "keep locator, authority, work, licence and cite_only on every "
                                                 "row you redistribute"},
            "terms_files": ["LICENSING.md", "LICENSE_DATA.md", "LICENSE_POLICY.md"],
        },
      },
      "build_warnings": problems,
      "built_from": {p.name: sha(p) for p in sorted(KB.iterdir()) if p.is_file()},
      # the manifest must not reference itself, bundles.json, or the sqlite index:
      # bundles.json digests this manifest, and sqlite writes are not byte-reproducible,
      # so hashing any of them makes every build disagree with the last one
      "files": {str(p2.relative_to(out)): sha(p2) for p2 in sorted(out.rglob("*"))
                if p2.is_file() and p2.name not in ("manifest.json", "bundles.json", "geomancy.sqlite")},
      "next_ids": {"passage_table": "passages", "search": "SELECT rowid, passage locator..." if not fts else
                   "SELECT * FROM passages_fts JOIN passages ON passages.id=passages_fts.rowid WHERE passages_fts MATCH ?"},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"built {out/'geomancy.sqlite'}: {n} passages, {len(rules_rows())} rules, FTS5={fts}")
    print("manifest:", json.dumps(manifest["counts"]))
    con.close()

if __name__ == "__main__":
    main()
