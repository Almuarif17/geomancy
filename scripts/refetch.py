#!/usr/bin/env python3
"""Re-download the page scans (kept out of the workspace because they are gigabytes).
Usage:  python3 scripts/refetch.py fasciculus_geomanticus_1704 [name2 ...]
        python3 scripts/refetch.py --all
Names map to corpus/raw/ia/<name>.pdf.pdf, which the extractors expect."""
import json, pathlib, subprocess, sys
REPO = pathlib.Path(__file__).resolve().parent.parent
REP = json.loads((REPO / "corpus/raw/ia/_fetch_report.json").read_text())
HAVE = {r["name"]: r["identifier"] for r in REP if r.get("pdf")}
if "--all" in sys.argv:
    want = list(HAVE)
else:
    want = sys.argv[1:]
for name in want:
    ident = HAVE.get(name)
    if not ident:
        print(f"  skip {name}: no recorded pdf"); continue
    dest = REPO / f"corpus/raw/ia/{name}.pdf.pdf"
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"  have {name}"); continue
    url = f"https://archive.org/download/{ident}/{ident}.pdf"
    print(f"  fetching {name}  <- {ident}")
    subprocess.run(["curl", "-sL", "--max-time", "900", "-o", str(dest), url], check=False)
