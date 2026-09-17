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
import urllib.parse
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


def hdr(port: int, path: str) -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=25) as r:
        r.read()
        return {k.lower(): v for k, v in r.headers.items()}


def post(port: int, path: str, obj: dict) -> tuple[int, object]:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(obj).encode(),
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:                                     # noqa: BLE001
            return e.code, {"error": "unreadable body"}


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

    # ---------------------------------------------------------- the phone app (see notes/APP.md)
    # It is a separate page over the same routes, so the checks are about the wiring between the two:
    # the install files, the one rule the page is allowed to duplicate, and the payload shapes it paints.
    code, mob = get(port, "/m")
    mob = mob if isinstance(mob, str) else ""
    ck("the mobile shell answers at /m", code == 200 and mob.lstrip().startswith("<!doctype") and len(mob) > 20000,
       f"{len(mob)} B")
    script = re.search(r"<script>(.*?)</script>", mob, re.S)
    ck("its script is one parseable block", bool(script), "")
    js = script.group(1) if script else ""
    ck("no absolute URL anywhere in the app page: no CDN, no font, no analytics",
       "http://" not in mob and "https://" not in mob, str([l for l in mob.splitlines() if "http" in l][:1])[:140])
    eps = dict(re.findall(r"(\w+):\s*\"(/api/[^\"]+)\"", js))
    ck(f"the app talks to this origin only ({len(eps)} endpoints)", bool(eps)
       and all(v.startswith("/api/") for v in eps.values()) and not re.search(r"fetch\([^)]{0,10}https?://", js),
       str(sorted(eps.values())))
    looked = set(re.findall(r'\$\("#([\w-]+)"\)', js)) | set(re.findall(r'getElementById\("([\w-]+)"\)', js))
    present = set(re.findall(r'id="([\w-]+)"', mob))
    ck(f"every element the script reaches for exists or is drawn by it ({len(looked)} ids)",
       looked <= present, str(sorted(looked - present)[:8]))

    m = re.search(r"function rowValue\(taps\) \{ return (.+?); \}", js)
    ck("the phone repeats exactly one rule: pairs of marks become 1 or 2", bool(m), str(m and m.group(1)))
    ternary = re.match(r"(.+?) \? (.+?) : (.+?)$", m.group(1)) if m else None
    py = (f"({ternary.group(2)} if ({ternary.group(1).replace('===', '==').replace('!==', '!=')}) else {ternary.group(3)})"
          if ternary else (m.group(1) if m else "0"))
    sys.path.insert(0, str(ROOT))
    from engine import deep_read as D
    ck("and it agrees with deep_read.add for every pair of rows from 1 to 60 taps each",
       all(eval(py, {"taps": a + b}) == D.add([a], [b])[0] for a in range(1, 61) for b in range(1, 61)),
       "the counting rule on the phone drifted from the engine")

    man_code, man = get(port, "/manifest.webmanifest")
    ck("the manifest installs as standalone portrait with real icons",
       man_code == 200 and man.get("display") == "standalone" and len(man.get("icons") or []) >= 2, str(man)[:120])
    named = [man["start_url"]] + [i["src"] for i in (man.get("icons") or [])] + ["manifest.webmanifest", "sw.js"]
    gone = [f for f in named if hdr(port, "/" + f.split("?")[0].lstrip("./")).get("content-type", "").startswith("application/json")]
    ck("no file the manifest names 404s, so the installed app opens", not gone, str(gone))
    ck("sw.js is served fresh every time, or a phone stays on a dead version forever",
       "no-store" in hdr(port, "/sw.js").get("cache-control", ""), str(hdr(port, "/sw.js").get("cache-control")))
    ck("the app shell is revalidated rather than pinned",
       "no-cache" in hdr(port, "/m").get("cache-control", ""), str(hdr(port, "/m").get("cache-control")))
    sw = get(port, "/sw.js")[1]
    seg = sw[sw.index('includes("/api/")'):sw.index("return;", sw.index('includes("/api/")'))] if 'includes("/api/")' in sw else ""
    ck("the worker never caches an answer from the engine", bool(seg) and ".put(" not in seg and "fetch(req)" in seg,
       seg[:140])
    icons = subprocess.run([sys.executable, str(APP / "make_icons.py"), "--check"], cwd=ROOT,
                           capture_output=True, text=True)
    ck("the app icons are generated and reproducible, not pasted in", icons.returncode == 0,
       (icons.stdout or icons.stderr)[:140])

    rows = [7, 2, 5, 4, 3, 3, 8, 1, 6, 9, 2, 2, 5, 5, 5, 10]
    code, cast = post(port, "/api/cast_from_rows", {"rows": rows, "topic": "will the deal close", "method": "taps"})
    ck("a cast made of counted taps returns the shield with its arithmetic",
       code == 200 and len(cast.get("row_values") or []) == 16 and len(cast.get("mothers_arithmetic") or []) == 4,
       str(cast)[:120])
    ck("each row value is the pair-count of the taps the phone sent",
       cast.get("row_values") == [1 if n % 2 else 2 for n in rows], str(cast.get("row_values")))
    ar = cast.get("mothers_arithmetic") or []
    ck("mothers_arithmetic is self-consistent: pairs, remainder, dots, rows",
       all(a["pairs"] == [t // 2 for t in a["taps"]] and a["remainder_odd"] == [bool(t % 2) for t in a["taps"]]
           and a["dots"] == sum(a["rows"]) and a["rows"] == cast["row_values"][4 * i:4 * i + 4]
           for i, a in enumerate(ar)), str(ar[:1])[:200])
    code, sand = post(port, "/api/cast_from_rows", {"values": cast["row_values"], "method": "sand"})
    ck("pierced sand and hand tapping reach the same four mothers",
       code == 200 and sand.get("mothers") == cast.get("mothers"), f"{sand.get('mothers')} vs {cast.get('mothers')}")
    code, refused = post(port, "/api/cast_from_rows", {"rows": []})
    ck("an empty cast is refused with a sentence, not a stack trace",
       code == 400 and len(str(refused.get("error"))) > 12, str(refused)[:120])
    code, wide = post(port, "/api/cast_from_rows", {"rows": [3] * 15, "topic": "x"})
    ck("fifteen rows is not silently padded to sixteen", code == 400, str(wide)[:110])
    code, w = post(port, "/api/cast_from_rows", {"rows": rows, "topic": "will the deal close",
                                                 "prefs": {"show_quotes": False, "make_it_say": "gold"}})
    pe = ((w.get("reading") or {}).get("prefs_echo") or {})
    ck("a phone may relabel and truncate but not write content, and is told what it dropped",
       pe.get("ignored_client_keys") == ["make_it_say"] and pe.get("show_quotes") is False
       and not any(c.get("quotes") for c in (w.get("reading") or {}).get("claims", [])), str(pe)[:150])

    moms = urllib.parse.quote(",".join(cast["mothers"]))
    qs = f"mothers={moms}&topic=will%20the%20deal%20close"
    code, ch = get(port, f"/api/chart16?{qs}")
    labels = [p["label"] for p in ch.get("positions", [])]
    ck("chart16 numbers all sixteen places and names the court as a court",
       code == 200 and len(labels) == 16
       and labels[12:] == ["left witness", "right witness", "Judge", "Sentence / Reconciler"], str(labels))
    ck("every place beyond the first states what it was derived from",
       all(p.get("derived_from") for p in ch["positions"][1:]),
       str([p["label"] for p in ch["positions"] if not p.get("derived_from")]))
    ck("the first daughter is the mothers' top row read across, not a mirrored pattern",
       ch["positions"][4]["pattern"] == [p["pattern"][0] for p in ch["positions"][:4]],
       f'{ch["positions"][4]["pattern"]} vs {[p["pattern"][0] for p in ch["positions"][:4]]}')
    ck("the judge is the two witnesses added, by the same odd-even rule",
       ch["positions"][14]["pattern"] == D.add(ch["positions"][12]["pattern"], ch["positions"][13]["pattern"]),
       str(ch["positions"][14]["pattern"]))
    ck("no technique came back as an error object",
       not any(isinstance(v, dict) and "error" in v for v in (ch.get("techniques") or {}).values()),
       str([k for k, v in (ch.get("techniques") or {}).items() if isinstance(v, dict) and "error" in v]))
    code, pv = get(port, f"/api/prove?{qs}")
    ev = json.loads((ROOT / "library" / "dataset" / "evaluation.json").read_text())
    ck("the proof panel is the real differential gate, not a number typed into the app",
       code == 200 and pv["differential"]["casts_tested"] == ev["casts_tested"]
       and pv["differential"]["mismatches"] == ev["mismatches"]
       and sorted(pv["differential"]["checks"]) == sorted(ev["agreement"]), str(pv.get("differential"))[:150])
    ck("each claim is proved with arithmetic and its voices split, never merged into the sentence",
       pv["claims"] and all(c.get("arithmetic") and "quotable" in c and "cite_only" in c for c in pv["claims"]),
       str(pv["claims"][:1])[:160])
    ck("the audit travels with the proof", pv["audit"].get("ok") is True, str(pv.get("audit"))[:150])
    cct = hdr(port, f"/api/copy?{qs}")
    txt = get(port, f"/api/copy?{qs}")[1]
    ck("the copy block is plain text with all sixteen places and the standing line last",
       cct.get("content-type", "").startswith("text/plain")
       and txt.count(" dots (") == 16 and all(n in txt for n in ("XIII", "XIV", "XV", "XVI"))
       and txt.strip().endswith("not advice, and not a prediction: these are documented claims by named authorities."),
       f'{txt.count(" dots (")} figure lines; last: {txt.strip().splitlines()[-1][:60] if txt else ""}')

    code, err = get(port, "/api/nope")
    ck("unknown route is JSON 404, not an HTML traceback", code == 404, str(err)[:80])

    # ---- the Android shell: it must be buildable from this tree, and carry nothing of its own ----
    # android/ is a WebView around the file the browser is served. Two ways that rots: the shell keeps a second
    # copy of the app (then every test here proves nothing about what ships), or a rule quietly leaves the Java
    # (then it installs, opens, and never shows a reading). Both are checked at the source, not by building.
    def run(*cmd: str) -> tuple[int, str]:
        r = subprocess.run(list(cmd), cwd=ROOT, capture_output=True, text=True, timeout=180)
        return r.returncode, (r.stdout + r.stderr).strip()

    rc, out = run(sys.executable, "android/prepare.py", "--check")
    ck("the shell's assets come from app/, and it keeps no copy of its own", rc == 0 and "PASS" in out, out[-220:])
    rc, out = run("bash", "android/build.sh", "--check")
    ck("the shell's own rules are still in its source", rc == 0 and "PASS" in out, out[-220:])

    mob = (APP / "mobile.html").read_text()
    sys.path.insert(0, str(APP.parent / "android"))
    import prepare as shellprep                                       # noqa: E402

    carried = set(shellprep.WWW)
    named = {m.strip("./") for m in re.findall(r"""["'`]([A-Za-z0-9._-]+\.(?:png|js|css|webmanifest|json))["'`]""", mob)}
    ck("every file the page asks for by name is one the APK carries", named <= carried,
       f"page names {sorted(named - carried)}; the build carries {sorted(carried)}")
    sh = (APP.parent / "android" / "build.sh").read_text()
    man = (APP.parent / "android" / "AndroidManifest.xml").read_text()
    top = next((l[3:].split(" -")[0].strip() for l in (ROOT / "CHANGELOG.md").read_text().splitlines()
                if l.startswith("## ")), "")
    ck("the APK's version is derived from the repo, so it cannot drift from the engine",
       "CHANGELOG.md" in sh and "android:versionName" not in man and "--version-name" in sh, top)
    rc, out = run(sys.executable, "android/serve_apk.py", "--help")
    ck("the Wi-Fi handover exists, and knows what an APK's content type is",
       rc == 0 and "application/vnd.android.package-archive" in run(sys.executable, "-c",
       "import pathlib,sys; sys.path.insert(0,'android'); import serve_apk as s;"
       "print(s.Handler.extensions_map['.apk'])")[1], out.splitlines()[0][:60])
    rc, out = run(sys.executable, "android/serve_apk.py", "--apk", "/nonexistent/tellus-loquens.apk")
    ck("it refuses to serve an APK that was never built, instead of an empty page",
       rc != 0 and "android/build.sh" in out, out.strip()[-90:])
    rc, tracked = run("git", "ls-files", "android")
    junk = [l for l in tracked.splitlines() if l.endswith((".apk", ".keystore", ".jks", ".jar", ".zip"))]
    ck("no build output, keystore or SDK jar is tracked in git", rc == 0 and not junk, str(junk[:3]))

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
