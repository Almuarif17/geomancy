#!/usr/bin/env python3
"""Send the checked-in v1 examples to a running local reader and print its responses."""
import json
import pathlib
import sys
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8044"
ROOT = pathlib.Path(__file__).resolve().parents[1]
examples = json.loads((ROOT / "examples/atelier_position_v1_requests.json").read_text())
for item in examples:
    req = urllib.request.Request(
        BASE + "/api/v1/read-position",
        data=json.dumps(item["request"]).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        result = json.loads(response.read())
    print(f"\n## {item['name']}\n{json.dumps(result, indent=2, ensure_ascii=False)}")
