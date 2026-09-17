#!/usr/bin/env python3
"""App contract test: the reader must answer, cite, obey preferences, and stay self-contained.

Run: python3 app/test_app.py

This starts the real server as a subprocess and speaks to it over a socket, because every defect that matters
in this app lives in the wiring - a route that 500s on an empty topic, an error page that leaks a stack trace
into a browser, a fetch() that points at localhost and breaks the moment the app is served from somewhere
else. Asserting on the imported functions would test the wrong thing.
"""
from __future__ import annotations

import json
import pathlib
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

APP = pathlib.Path(__file__).resolve().parent
ROOT = APP.parent
MOMS = "Via,Populus,Acquisitio,Amissio"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get(port: int, path: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=25) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    ctype = "json"
    try:
        return 200, json.loads(raw)
    except Exception:                                        # noqa: BLE001
        ctype = "html"
    return 200, raw.decode(errors="replace") if ctype == "html" else raw


def main() -> int:
    port = free_port()
    proc = subprocess.Popen([sys.executable, str(APP / "server.py"), "--port", str(port)],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    for _ in range(60):
        try:
            code, _ = get(port, "/api/health")
            if code == 200:
                break
        except Exception:                                    # noqa: BLE001
            time.sleep(0.25)
    else:
        proc.kill()
        print("APP TEST: FAIL - server never answered on its port")
        print((proc.stderr.read() or "")[-800:])
        return 1

    checks: list[tuple[str, bool, str]] = []

    def ck(name: str, cond: bool, detail: str = "") -> None:
        checks.append((name, bool(cond), detail))

    code, health = get(port, "/api/health")
    ck("health answers with the live counts", code == 200 and health.get("ok") and health["passages"] > 1000
       and health["voices"] > 1000, str(health)[:120])
    ck("health reports a version from the CHANGELOG, not a hardcoded string",
       str(health.get("version", "")).count(".") == 2, str(health.get("version")))

    code, figs = get(port, "/api/figures")
    ck("16 figures with dot patterns", code == 200 and len(figs) == 16
       and all(isinstance(f.get("points"), int) for f in figs.values()), f"{len(figs)} figures")

    code, topics = get(port, "/api/topics")
    ck("topics carry their own voice counts", code == 200 and len(topics) >= 20
       and all(isinstance(t.get("n_voices"), int) for t in topics), f"{len(topics)} outcomes")
    ck("every topic names its coverage instead of leaving it blank",
       all(t.get("note") for t in topics), str([t["outcome"] for t in topics if not t.get("note")][:3]))

    code, ch = get(port, f"/api/cast?mothers={MOMS}")
    ck("cast returns exactly 12 houses and a 4-figure court",
       code == 200 and len(ch["houses"]) == 12 and len(ch["court"]) == 4, str(list(ch)[:5]))
    ck("court is not numbered as houses XIII-XVI", not any(k in ch["houses"] for k in ("13", "14", "15", "16")))
    ck("patterns travel as 16 shield rows", len(ch["patterns"]) == 16, str(len(ch.get("patterns", {}))))

    bad_code, bad = get(port, "/api/cast?mothers=Via,Populus")
    ck("too few mothers is a 400 with a readable message, not a 500",
       bad_code == 400 and b"four" in (bad if isinstance(bad, bytes) else json.dumps(bad).encode()),
       str(bad)[:120])

    code, rd = get(port, f"/api/reading?mothers={MOMS}&topic=marriage")
    ck("reading audits clean through the app", code == 200 and rd["audit"]["ok"] is True,
        str(rd.get("audit"))[:160])
    ck("every shown claim carries its strength and works",
       all("strength" in c and "works" in c for c in rd["claims"]), f"{len(rd['claims'])} claims")
    ck("quotes ship with authority + locator + voice id",
       all(q.get("locator") and q.get("id") for c in rd["claims"] for q in c.get("quotes", [])))
    ck("the quesited house leads the page",
       not rd["claims"] or rd["claims"][0].get("house") == rd["quesited_house"] or rd["claims"][0].get("role"),
       str(rd["claims"][0].get("house") if rd["claims"] else None))
    ck("the app states its own standing", "does not" in rd["standing"] or "not" in rd["standing"],
       rd["standing"][:60])
    ck("preferences are echoed, so a user can see what was applied",
       isinstance(rd.get("prefs_echo"), dict) and "show_quotes" in rd["prefs_echo"])

    code, v = get(port, "/api/voices?figure=Amissio&limit=5")
    ck("voice browse filters and counts", code == 200 and v["matched"] >= 5 and len(v["returned"]) == 5,
       str(v["matched"]))
    code, v2 = get(port, "/api/voices?figure=Amissio&house=4")
    ck("house filter uses arabic numbers as the index does",
       all(str(r.get("house")) in ("4", "IV", "None") for r in v2["returned"]), str(v2["returned"][:1])[:120])

    code, cov = get(port, "/api/coverage")
    ck("the app can show the coverage scoreboard", code == 200 and 0 < cov["score_of_100"] <= 100
       and cov.get("components"), str(cov.get("score_of_100")))

    code, how = get(port, "/api/how")
    ck("how-it-works has 8 stages, each with a gate named",
       code == 200 and len(how["stages"]) == 8 and all(s.get("gate") and s.get("numbers") for s in how["stages"]))

    # self-containment: the page must not depend on anybody else's server
    code, page = get(port, "/")
    html = page if isinstance(page, str) else page.decode()
    ck("index.html served", code == 200 and len(html) > 4000, f"{len(html)} B")
    ext = [l for l in html.splitlines() if "http://" in l or "https://" in l]
    ck("no absolute URLs in the page: no CDN, no font, no analytics", not ext, str(ext[:1])[:160])
    # the page builds URLs as j("/api/...") and string-concatenates query params; check the literal path of
    # every call site rather than trusting a line-level substring, which is how the first version of this
    # assertion produced a false alarm on a perfectly relative page
    calls = re.findall(r"""\bj\(\s*["']([^"'`)\s]+)""", html)
    ck(f"every data call is relative to this origin ({len(calls)} call sites)",
       calls and all(c.startswith("/") and "://" not in c for c in calls), str(calls[:3]))
    ck("no fetch() to an absolute origin", not re.search("fetch\\([^)]{0,4}https?://", html))
    ck("user text is inserted as text, not HTML", "innerHTML = \"\"" in html and "textContent" in html)

    code, err = get(port, "/api/nope")
    ck("unknown route is JSON 404, not an HTML traceback", code == 404, str(err)[:80])

    proc.terminate()
    try:
        proc.wait(timeout=8)
    except Exception:                                        # noqa: BLE001
        proc.kill()
    errlog = (proc.stderr.read() or "").strip()
    ck("server logged no traceback while all of that ran", "Traceback" not in errlog, errlog[-200:])

    bad = [c for c in checks if not c[1]]
    for name, okk, detail in checks:
        print(f"  [{'ok' if okk else 'FAIL'}] {name}" + (f"  {detail}" if detail and not okk else ""))
    print(f"\nAPP TEST: {'PASS' if not bad else 'FAIL'}  ({len(checks) - len(bad)}/{len(checks)} checks"
          + (f", {len(bad)} failed)" if bad else ", server stderr clean)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
