#!/usr/bin/env python3
"""The app's only entry point: ask for an outcome, get exactly the pieces that answer it.

A casting screen does not need 1,098 passages. It needs the figures, the routing, the rulings and
the priors for *one* outcome - so the dataset ships pre-sliced indexes and this module reads them
without touching the network or the corpus.

    python3 engine/retrieve.py --build                       (re)write the index shards
    python3 engine/retrieve.py --figure Populus --house 7
    python3 engine/retrieve.py --topic marriage --json
    python3 engine/retrieve.py --search "buried" --limit 5
    python3 engine/retrieve.py --screen verdict --json       which files a screen must download
"""
from __future__ import annotations

import argparse, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
KB = ROOT / "kb"
DS = ROOT / "library" / "dataset"
IDX = DS / "index"
sys.path.insert(0, str(HERE))

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def _jsonl(p: pathlib.Path):
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _write_jsonl(p: pathlib.Path, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- build
TABLES = ["figures.yaml", "houses.yaml", "techniques.yaml", "calatarama_grid.json", "priors.json",
          "perfection_priors.json", "calibration.json", "alfagini_quaestiones.json",
          "hartmann_casebook.json", "lataille_grid.json", "cattan_motus_bank.json",
          "cattan1591_dangers.json", "question_inventory.json"]


def build():
    """Derive outcome indexes + copy the tables an app needs, all offline and deterministic.

    Shapes (verified against the files, not assumed):
      kb/calatarama_grid.json  {"grid": {"II": {"folio": "26v", "entries": {figure: verdict}}}}
      kb/priors.json           {"possible_judges": {figure: n_casts}, "per_house": {roman: {figure: {...}}}}
      kb/perfection_priors.json{"priors": {"question_in_house_VII": {mode: {"pct": ..}}}}
      kb/houses.yaml           houses: {int: {latin, english, cal, extra_houses, triplicities}}
                               question_to_house: {topic: int}
      dataset passages         {work, kind, figure, house, locator, text, confidence}   <- singular
    """
    passages = _jsonl(DS / "shards" / "passages.jsonl")
    rules = _jsonl(DS / "shards" / "rules.jsonl")
    figs = _yaml(KB / "figures.yaml").get("figures", {})
    hdata = _yaml(KB / "houses.yaml")
    houses_raw = hdata.get("houses", {})
    routing = hdata.get("question_to_house", {})
    grid = (json.loads((KB / "calatarama_grid.json").read_text()).get("grid")
            if (KB / "calatarama_grid.json").exists() else {})
    priors = json.loads((KB / "priors.json").read_text()) if (KB / "priors.json").exists() else {}
    pp = (json.loads((KB / "perfection_priors.json").read_text()).get("priors", {})
          if (KB / "perfection_priors.json").exists() else {})
    judges = priors.get("possible_judges", {})

    # ship the tables the app needs alongside the shards, so a device never reads ../kb
    (DS / "tables").mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        src = KB / name
        if src.exists():
            (DS / "tables" / name).write_bytes(src.read_bytes())

    # a stable id per passage, since the shard rows carry none; and houses are stored as romans
    for i, r in enumerate(passages):
        r["id"] = f"P{i:04d}"
        h = r.get("house")
        if isinstance(h, str) and h.upper() in ROMAN:
            r["house_n"] = ROMAN.index(h.upper()) + 1
        elif h is not None:
            try:
                r["house_n"] = int(h)
            except (TypeError, ValueError):
                r["house_n"] = None
        else:
            r["house_n"] = None

    fig_names = list(figs)
    by_figure = {}
    for name, meta in figs.items():
        ruling = {h: grid[h]["entries"].get(name) for h in grid if name in (grid[h].get("entries") or {})}
        pats = [r["id"] for r in passages if (r.get("figure") or "").lower() == name.lower()]
        by_figure[name] = {
            "figure": name, "pattern": list((meta or {}).get("pattern") or []), "points": (meta or {}).get("points"),
            "arabic": (meta or {}).get("arabic"), "ifa_odu": (meta or {}).get("ifa_odu"),
            "element": (meta or {}).get("element"), "planet": (meta or {}).get("planet"),
            "quality": (meta or {}).get("quality"), "motion": (meta or {}).get("motion"),
            "gender": (meta or {}).get("gender"), "time_unit": (meta or {}).get("time_unit"),
            "attainable_as_judge": name in judges, "judge_casts": judges.get(name),
            "house_rulings": ruling, "missing_house_rulings": sorted(set(grid) - set(ruling)),
            "passages": pats[:60],
            "rules": sorted({r["id"] for r in rules if name.lower() in json.dumps(r, ensure_ascii=False).lower()}),
        }
    by_house = {}
    for h, meta in houses_raw.items():
        roman = ROMAN[int(h) - 1]
        meta = meta or {}
        entries = (grid.get(roman) or {}).get("entries") or {}
        by_house[str(h)] = {
            "house": str(h), "roman": roman, "latin": meta.get("latin"), "english": meta.get("english"),
            "cal": meta.get("cal"), "extra_houses": meta.get("extra_houses", []),
            "triplicities": meta.get("triplicities", []),
            "figure_rulings": entries, "folio": (grid.get(roman) or {}).get("folio"),
            "per_house_figure_p": (priors.get("per_house", {}).get(roman) or {}),
            "outcomes": sorted(t for t, v in routing.items() if str(v) == str(h)),
            "passages": [r["id"] for r in passages if r.get("house_n") == int(h)][:60],
            "perfection_base_rates": pp.get(f"question_in_house_{roman}", {}),
            # a blank in the source is information: name it, so the app renders "the source does not
            # say" rather than silently showing a shorter list than it should
            "missing_figure_rulings": sorted(set(fig_names) - set(entries)),
        }
    by_outcome = []
    for topic, h in routing.items():
        h = int(h)
        roman = ROMAN[h - 1]
        meta = houses_raw.get(h) or houses_raw.get(str(h)) or {}
        by_outcome.append({
            "outcome": topic, "label": meta.get("english") or topic, "quesited_house": h, "quesited_roman": roman,
            "latin": meta.get("latin"), "extra_houses": meta.get("extra_houses", []),
            "triplicities": meta.get("triplicities", []),
            "cal_scope": (meta.get("cal") or {}).get("aspect"),
            "priors_key": f"question_in_house_{roman}",
            "base_rates": pp.get(f"question_in_house_{roman}", {}),
            "ruling_table": ((grid.get(roman) or {}).get("entries")) or {},
            "passages": by_house.get(str(h), {}).get("passages", [])[:30],
            "n_passages_for_house": len(by_house.get(str(h), {}).get("passages", [])),
            "significator_rules": ["perfection", "significators_by_house", "parentage",
                                   "house_quality_tiebreak", "timing"],
            "always_read": ["validity_gates", "reconciler", "via_puncti", "motus_and_passing"],
        })
    _write_jsonl(IDX / "by_figure.jsonl", list(by_figure.values()))
    _write_jsonl(IDX / "by_house.jsonl", list(by_house.values()))
    _write_jsonl(IDX / "by_outcome.jsonl", by_outcome)
    _write_jsonl(IDX / "by_work.jsonl", [
        {"work": w, "passages": [r["id"] for r in passages if r.get("work") == w],
         "kinds": sorted({r.get("kind") for r in passages if r.get("work") == w if r.get("kind")})}
        for w in sorted({r.get("work") for r in passages if r.get("work")})])

    bundles()
    print(f"indexes: {len(by_figure)} figures, {len(by_house)} houses, {len(by_outcome)} outcomes, "
          f"{len(_jsonl(IDX / 'by_work.jsonl'))} works")
    print("bundles: " + ", ".join(f"{k}({v['bytes']//1024}K)" for k, v in bundle["screens"].items()))
    return 0


def bundles() -> None:
    """(Re)write bundles.json. Split out of build() because the manifest is refreshed after the
    indexes, and bundles.json digests the manifest - so it has to be the last file written."""
    bundle = {"README": ("one entry per app screen: the exact files to ship with the screen, with byte size "
                        "and a content hash for cache-busting on a CDN"),
              "generated_by": "engine/retrieve.py --build", "screens": {
                  "casting": ["index/by_outcome.jsonl", "index/by_figure.jsonl"],
                  "reading": ["index/by_outcome.jsonl", "index/by_figure.jsonl", "index/by_house.jsonl",
                              "shards/rules.jsonl", "tables/priors.json", "tables/perfection_priors.json"],
                  "verdict": ["index/by_house.jsonl", "shards/passages.jsonl"],
                  "topics": ["index/by_outcome.jsonl"],
                  "search": ["geomancy.sqlite", "shards/passages.jsonl"],
                  "offline_full": ["shards/passages.jsonl", "shards/rules.jsonl", "manifest.json"],
              }}
    for name, files in bundle["screens"].items():
        res = []
        for rel in files:
            f = DS / rel
            if f.exists():
                import hashlib
                if f.suffix == ".sqlite":
                    # sqlite is generated but not byte-reproducible; pinning its hash would make
                    # every build look stale, so the bundle lists it without a digest
                    res.append({"path": f"library/dataset/{rel}", "bytes": f.stat().st_size, "sha256": None,
                                "note": "regenerate with `make build`; not byte-stable, not hashed"})
                    continue
                b = f.read_bytes()
                res.append({"path": f"library/dataset/{rel}", "bytes": len(b),
                            "sha256": hashlib.sha256(b).hexdigest()[:16]})
            else:
                res.append({"path": f"library/dataset/{rel}", "bytes": 0, "sha256": None, "missing": True})
        bundle["screens"][name] = {"files": [r["path"] for r in res if not r.get("missing")],
                                   "resolved": res, "bytes": sum(r["bytes"] for r in res)}
    (DS / "bundles.json").write_text(json.dumps(bundle, indent=1) + chr(10))


def _yaml(p):
    if not p.exists():
        return {}
    import yaml
    try:
        return yaml.safe_load(p.read_text()) or {}
    except Exception:                                                  # noqa: BLE001
        return {}


# ---------------------------------------------------------------- read
def by_figure(name):
    return next((r for r in _jsonl(IDX / "by_figure.jsonl") if r["figure"].lower() == name.lower()), None)


def by_house(h):
    if isinstance(h, str) and h.upper() in ROMAN:
        h = ROMAN.index(h.upper()) + 1
    return next((r for r in _jsonl(IDX / "by_house.jsonl") if str(r["house"]) == str(h)), None)


def outcomes(match=None):
    rows = _jsonl(IDX / "by_outcome.jsonl")
    if match:
        m = match.lower()
        rows = [r for r in rows if m in r["outcome"].lower() or m in str(r.get("label", "")).lower()]
    return rows


def rules_for(topic=None, figure=None):
    """Techniques relevant to a topic/figure, with their procedure text and source citation."""
    out = []
    for p in (KB / "techniques.yaml",):
        d = _yaml(p).get("techniques", {})
        for k, v in d.items():
            if not isinstance(v, dict):
                continue
            hay = " ".join([k, str(v.get("answers", "")), str(v.get("also", ""))]).lower()
            if topic and topic.lower() not in hay:
                continue
            if figure and figure.lower() not in hay:
                continue
            out.append({"id": k, "conf": v.get("conf"), "status": v.get("status"),
                        "answers": v.get("answers"), "procedure": v.get("procedure"),
                        "source": v.get("source")})
    return out


def passages(figure=None, house=None, kind=None, q=None, limit=25):
    """Filter the published passages by figure / house / kind / substring (the sqlite file has FTS5)."""
    rows = _jsonl(DS / "shards" / "passages.jsonl")
    if figure:
        f = figure.lower()
        rows = [r for r in rows if f in [str(x or "").lower() for x in (
            r.get("figures") or ([r["figure"]] if r.get("figure") else []))]]
    if house:
        want = ROMAN.index(str(house).upper()) + 1 if str(house).upper() in ROMAN else int(house)
        rows = [r for r in rows if (r.get("house_n") == want or str(r.get("house")) == str(want)
                                    or str(r.get("house")).upper() == ROMAN[want - 1])]
    if kind:
        rows = [r for r in rows if (r.get("kind") or "").lower() == kind.lower()]
    if q:
        t = q.lower()
        rows = [r for r in rows if t in (r.get("text") or "").lower() or t in (r.get("note") or "").lower()]
    return rows[:limit]


def screen(name):
    b = json.loads((DS / "bundles.json").read_text()) if (DS / "bundles.json").exists() else {}
    return b.get("screens", {}).get(name)


def coverage():
    """What the library can and cannot answer today - the app renders this instead of guessing."""
    tech = _yaml(KB / "techniques.yaml").get("techniques", {})
    implemented = [k for k, v in tech.items() if isinstance(v, dict) and str(v.get("status", "")).upper() != "NAMED_ONLY"]
    named_only = [k for k, v in tech.items() if isinstance(v, dict) and str(v.get("status", "")).upper() == "NAMED_ONLY"]
    cases = _yaml(ROOT / "kb" / "rule_tests.yaml").get("cases", []) if (ROOT / "kb" / "rule_tests.yaml").exists() else []
    tested = {c.get("rule") for c in cases}
    holes = {}
    for r in _jsonl(IDX / "by_house.jsonl"):
        holes[r["house"]] = len(r.get("missing_figure_rulings") or [])
    return {"techniques": len(tech), "implemented": len(implemented), "named_only": named_only,
            "source_table_holes": {"houses_missing_figure_rulings": holes,
                                   "total_missing_cells": sum(holes.values()),
                                   "meaning": "the extracted ruling grid has no entry here; the app "
                                              "must render an explicit blank, never a guess"},
            "with_executable_case": sorted(tested), "passages": len(_jsonl(DS / "shards" / "passages.jsonl")),
            "outcomes": len(outcomes())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--bundles-only", action="store_true", help="rewrite bundles.json only")
    ap.add_argument("--figure"), ap.add_argument("--house"), ap.add_argument("--topic")
    ap.add_argument("--kind"), ap.add_argument("--search"), ap.add_argument("--screen")
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.bundles_only:
        bundles(); print("bundles.json refreshed against the current manifest"); return 0

    if a.build:
        return build()
    res = None
    if a.figure:
        res = by_figure(a.figure)
    elif a.house:
        res = by_house(a.house)
    elif a.topic:
        res = outcomes(a.topic)
    elif a.screen:
        res = screen(a.screen)
    elif a.coverage:
        res = coverage()
    elif a.search or a.kind:
        res = passages(q=a.search, kind=a.kind, limit=a.limit)
    if res is None:
        print(__doc__)
        return 0
    print(json.dumps(res, indent=1, ensure_ascii=False) if a.json else json.dumps(res, ensure_ascii=False)[:1600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
