#!/usr/bin/env python3
"""Triage an uploaded resource instead of letting it become an undocumented PDF.

Anything a human drops into `corpus/inbox/` (or names on the command line) is hashed,
sniffed for year / language / signature words, and given a **proposed** licence bucket and
disposition with reasons. It writes one line to `registry/proposed.jsonl` and stops there -
admission is a human edit into `registry/works.jsonl`, because a machine must not be the one
deciding that a book may be redistributed.

    python3 library/tools/triage.py [path ...]        # default: whole inbox
"""
from __future__ import annotations

import argparse, datetime as dt, hashlib, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
INBOX, OUT = ROOT / "corpus" / "inbox", ROOT / "registry" / "proposed.jsonl"

PD_BEFORE = 1900                     # works published this year or earlier: safe to bundle
SUMMARIZE_WORDS = ("copyright", "all rights reserved", "brill", "reedition", "translated with")
PD_MARKERS = ("public domain", "domain", "open access", "cc0", "cc by", "creative commons att")
SIGNATURES = {
    "calatarama": "calatarama_thesis", "alfagini": "fasciculus_1704", "geomantic": "fasciculus_1704",
    "raml": "risala_ramlia", "رملي": "risala_ramlia", "izinyanga": "amazulu_1870",
    "horary": "shatpanchashika", "prasna": "shatpanchashika", "lal kitab": "lal_kitab_1939",
}


def sniff(text: str) -> dict:
    years = [int(y) for y in re.findall(r"\b(1[4-9]\d\d|20[0-2]\d)\b", text[:40000])]
    early = [y for y in years if y < 1801]
    low = text[:60000].lower()
    hits = {SIG: row for SIG, row in SIGNATURES.items() if SIG in low}
    lang = ("arabic" if len(re.findall(r"[\u0600-\u06ff]", text[:20000])) > 300 else
            "persian" if len(re.findall(r"[\u0600-\u06ff]", text[:20000])) > 150 else
            "latin" if len(re.findall(r"\b(quod|est|in|de)\b", low[:8000])) > 60 else
            "english" if re.search(r"\bthe\b", low[:4000]) else "unknown")
    return {"candidate_year": min(early or years or [0]) or None, "language_guess": lang,
            "signature_matches": hits,
            "pd_markers": [m for m in PD_MARKERS if m in low],
            "restrictive_markers": [m for m in SUMMARIZE_WORDS if m in low]}


def propose(meta: dict) -> dict:
    yr, restr, pdm = meta.get("candidate_year"), meta["restrictive_markers"], meta["pd_markers"]
    if restr and not pdm:
        bucket, disp, why = "C", "drop", "restrictive language and no open-access marker"
    elif yr and yr <= PD_BEFORE:
        bucket, disp, why = "A", "full", f"imprint year {yr} <= {PD_BEFORE}: public domain"
    elif yr:
        bucket, disp, why = "B", "summarize", f"year {yr} - in copyright until verified; take notes only"
    else:
        bucket, disp, why = "B", "cite", "no year found in the first 40k chars - unverified, cite only"
    return {"licence_bucket": bucket, "disposition": disp, "reason": why}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args()
    files = [pathlib.Path(p) for p in a.paths] or (sorted(INBOX.iterdir()) if INBOX.exists() else [])
    files = [f for f in files if f.is_file() and f.suffix.lower() in {".txt", ".md", ".pdf", ".html"}]
    if not files:
        print("inbox empty - nothing to triage")
        return 0
    reg_ids = {json.loads(l)["id"] for l in (ROOT / "registry" / "works.jsonl").read_text().splitlines() if l.strip()}
    lines = []
    for f in files:
        raw = f.read_bytes()
        text = raw.decode("utf-8", "replace") if f.suffix.lower() in {".txt", ".md", ".html"} else ""
        meta = sniff(text)
        match = next(iter(meta["signature_matches"].values()), None)
        h = hashlib.sha256(raw).hexdigest()
        row = {"id": f"proposed_{h[:10]}", "title": f.stem[:70], "year": meta["candidate_year"],
               "language": meta["language_guess"], "host": "local_upload", "stable_id": f"sha256:{h[:16]}",
               "bytes": len(raw), "sha256": h, "detected": meta,
               "may_duplicate": match if match in reg_ids else None,
               "proposed": propose(meta), "proposed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "note": "NOT admitted - a human must move this line into registry/works.jsonl after checking the front matter"}
        if match:
            row["note"] += f"; looks like the same text family as {match}"
        lines.append(row)
        p = row["proposed"]
        print(f"  {f.name[:40]:42s} yr={str(row['year']):6s} {p['licence_bucket']}/{p['disposition']:9s} "
              f"{p['reason'][:46]}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as fh:
        for r in lines:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n{len(lines)} proposal(s) appended to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
