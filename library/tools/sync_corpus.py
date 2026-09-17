#!/usr/bin/env python3
"""Fetch / re-verify the corpus from the registry. No manual clicking.

Reads `registry/works.jsonl`. For every row with disposition `full`, resolves the work by
its **stable identifier** (archive.org id, ARK, handle, DOI) using the host's API, downloads
the text layer into `corpus/raw/`, and records size + sha256 + retrieved_at in
`corpus/manifest.lock.json`. Rows marked `summarize` or `cite` are never bulk-fetched:
only their locator is recorded, which is exactly what keeps the repo free of material we
are not allowed to redistribute.

    --dry-run   show what would be fetched and where it comes from
    --check     health-check every registered host; report rot; no writes
    --only id   restrict to one or more ids
    --force     re-download even when the lock says it is present

Exit codes: 0 ok, 1 a registered source is unreachable (link rot or licence change).
"""
from __future__ import annotations

import argparse, datetime as dt, hashlib, json, pathlib, re, sys, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registry" / "works.jsonl"
CORPUS = ROOT / "corpus"
LOCK = CORPUS / "manifest.lock.json"
UA = "geomancy-library/0.2 (research build; source integrity check)"


def rows():
    return [json.loads(l) for l in REGISTRY.read_text().splitlines() if l.strip()]


def get(url: str, binary: bool = False, tries: int = 3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except Exception as e:                                    # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"{url} :: {last}")


def ia_files(identifier: str) -> dict:
    """Ask IA which files actually exist - never assume a filename pattern."""
    meta = json.loads(get(f"https://archive.org/metadata/{identifier}"))
    out = {}
    for f in meta.get("files", []):
        name = f.get("name", "")
        if name.endswith("_djvu.txt"):
            out["text"] = name
        elif name.endswith("_hocr.html"):
            out["ocr"] = name
        elif name.endswith("djvu.xml"):
            out["coords"] = name
    out["server"] = meta.get("server")
    out["dir"] = meta.get("dir")
    out["title"] = (meta.get("metadata") or {}).get("title")
    out["license"] = (meta.get("metadata") or {}).get("licenseurl")
    return out


def resolve(row: dict) -> tuple[str, str] | None:
    """Return (kind, url) for a registry row, or None when the row is not fetchable."""
    host, sid = row["host"], row["stable_id"]
    if host == "archive.org" and re.fullmatch(r"[A-Za-z0-9_\-]+", sid or ""):
        return "ia", f"https://archive.org/download/{sid}/{sid}_djvu.txt"
    if host == "archive.org" and (sid or "").startswith("search:"):
        return None                                            # needs a human to pin the id
    if host == "utoronto.scholaris.ca" and sid.startswith("bitstream:"):
        return "pdf", "https://utoronto.scholaris.ca/server/api/core/bitstreams/" + sid.split(":", 1)[1]
    if "gallica" in host and sid.startswith("ark:"):
        return "iiif", f"https://gallica.bnf.fr/ark:/{sid}/textVersion"
    if "bsb" in host or "digitale-sammlungen" in host:
        return "iiif", sid
    return None


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def load_lock() -> dict:
    if LOCK.exists():
        return json.loads(LOCK.read_text())
    return {"generated": None, "sources": {}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true", help="health-check hosts, write nothing")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    reg, lock = rows(), load_lock()
    if a.only:
        reg = [r for r in reg if r["id"] in set(a.only)]
    bad, changed = [], []

    for row in reg:
        rid, bucket, disp = row["id"], row["licence_bucket"], row["disposition"]
        res = resolve(row)
        entry = lock["sources"].get(rid, {})

        if a.check:
            if not res:
                print(f"  manual   {rid:24s} no automated recipe ({row['host']})")
                continue
            kind, url = res
            if kind == "ia":
                try:
                    f = ia_files(url.split("/download/")[1].split("/")[0])
                    ok = bool(f.get("text"))
                    print(f"  {'alive  ' if ok else 'DEAD   '}{rid:24s} IA:{url.split('/')[3]}"
                          f" title={str(f.get('title'))[:40]!r} text={'yes' if ok else 'NO'}")
                    if not ok:
                        bad.append((rid, "no text layer on IA any more"))
                except Exception as e:                          # noqa: BLE001
                    print(f"  DEAD   {rid:24s} {e}")
                    bad.append((rid, str(e)[:120]))
            else:
                try:
                    get(url)
                    print(f"  alive  {rid:24s} {url[:60]}")
                except Exception as e:                          # noqa: BLE001
                    print(f"  DEAD   {rid:24s} {url[:60]}")
                    bad.append((rid, str(e)[:120]))
            continue

        if disp != "full":
            print(f"  skip     {rid:24s} disposition={disp} bucket={bucket} - locator only")
            if not a.dry_run:
                lock["sources"][rid] = {**entry, "locator": row["stable_id"], "host": row["host"],
                                        "fetched": False, "note": f"disposition {disp}"}
            continue
        if bucket != "A":
            print(f"  BLOCKED  {rid:24s} bucket {bucket} may not be bundled in full - fix the registry, not the gate")
            bad.append((rid, f"disposition=full but licence_bucket={bucket}"))
            continue
        if not res:
            print(f"  manual   {rid:24s} no recipe for host {row['host']}")
            continue
        kind, url = res
        dest = CORPUS / "raw" / f"{rid}.txt"
        if dest.exists() and not a.force:
            print(f"  present  {rid:24s} {dest.name} ({dest.stat().st_size//1024}K)")
            continue
        if a.dry_run:
            print(f"  would    {rid:24s} GET {url}")
            continue
        print(f"  fetch    {rid:24s} {url[:70]}")
        CORPUS.joinpath("raw").mkdir(parents=True, exist_ok=True)
        txt = get(url)
        dest.write_text(txt)
        digest = sha256(dest)
        lock["sources"][rid] = {"locator": row["stable_id"], "host": row["host"], "fetched": True,
                                "path": str(dest.relative_to(ROOT)), "bytes": dest.stat().st_size,
                                "sha256": digest, "sha256_prefix": digest[:16],
                                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        changed.append(rid)
        time.sleep(1.0)                                         # be polite to free hosts

    if not a.dry_run and not a.check:
        lock["generated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n")
    print(f"\n{len(changed)} fetched | {len(bad)} problems"
          + (f" | report: {LOCK.relative_to(ROOT)}" if not a.check else ""))
    for rid, why in bad:
        print(f"  ! {rid}: {why}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
