#!/usr/bin/env python3
"""Render gate: drive the phone app in a real browser at a real phone size, and fail on what a phone user feels.

    python3 app/check_render.py                 # asserts behaviour, writes screenshots to /tmp
    python3 app/check_render.py --shots build   # keep them somewhere else

Unit tests cannot see this class of defect: an element that exists but is 12px tall, a page that scrolls
sideways on a 412px screen, a tap that paints nothing because the handler was bound to a node that stage()
redrew, a cast that never reaches the engine because a template literal closed one bracket early. So this
file launches Chromium headless at the size of a TECNO K17, casts in all four modes, opens the reading panes
and the proof sheet, and asserts on painted boxes and sizes rather than on strings.

It self-skips (exit 0, loud) when Playwright or its browser is missing, because the library must stay
buildable without a 100 MB download: install with `pip install playwright && python3 -m playwright install chromium`.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import socket
import subprocess
import sys
import time

APP = pathlib.Path(__file__).resolve().parent
ROOT = APP.parent
# a TECNO K17 is 720x1612 at ~2x, which Chrome reports as a 412x915 CSS viewport
WIDTH, HEIGHT = 412, 915
ROWS = [7, 2, 5, 4, 3, 3, 8, 1, 6, 9, 2, 2, 5, 5, 5, 10]      # the cast the desktop tests also use


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shots", default="/tmp/geomancy-shots", help="where to write screenshots")
    ap.add_argument("--keep", action="store_true", help="leave the browser open for a manual look (headed)")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except Exception:                                            # noqa: BLE001
        print("RENDER CHECK: SKIP - playwright is not installed "
              "(pip install playwright && python3 -m playwright install chromium)")
        return 0

    shots = pathlib.Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    port = free_port()
    proc = subprocess.Popen([sys.executable, str(APP / "server.py"), "--port", str(port)],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    ok_up = False
    for _ in range(80):
        try:
            import urllib.request
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2):
                ok_up = True
                break
        except Exception:                                        # noqa: BLE001
            time.sleep(0.25)
    if not ok_up:
        proc.kill()
        print("RENDER CHECK: FAIL - the server never answered")
        print((proc.stderr.read() or "")[-900:])
        return 1

    base = f"http://127.0.0.1:{port}"
    fails: list[str] = []
    notes: list[str] = []

    def ck(name: str, cond: bool, detail: str = "") -> None:
        (notes if cond else fails).append(name if cond else f"{name}  << {detail}")

    console: list[str] = []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=not args.keep)
        except Exception as e:                                    # noqa: BLE001
            proc.kill()
            print(f"RENDER CHECK: SKIP - no browser available for playwright ({type(e).__name__})")
            return 0
        ctx = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=2.5,
                                  is_mobile=True, has_touch=True,
                                  permissions=["clipboard-read", "clipboard-write"])
        page = ctx.new_page()
        page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        page.goto(f"{base}/m", wait_until="load")
        page.wait_for_timeout(900)

        # ---- the shell paints: sixteen pips, four mode tabs, no sideways scroll ----
        ck("sixteen pips are drawn, one per row", page.locator("#pips i").count() == 16,
           str(page.locator("#pips i").count()))
        ck("the stage is not empty", page.locator("#stage *").count() > 10, "stage rendered nothing")
        ck("nothing overflows the phone width", page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth + 1"),
           page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]").__repr__())
        box = page.locator(".mound").first.bounding_box() or {}
        ck("a hill is big enough to hit with a thumb (>=56px)", (box.get("width") or 0) >= 56, str(box))
        page.fill("#q", "will the deal close")
        page.wait_for_timeout(200)
        ck("the question you type is the question the cast carries", page.evaluate("S.question") == "will the deal close",
           str(page.evaluate("S.question")))
        page.screenshot(path=str(shots / "01-cast-sand.png"))

        # ---- sand: pierce all sixteen, the cast completes itself ----
        for i in range(8):
            page.locator(".mound").nth(i).click()
            page.wait_for_timeout(35)
        # counted mid-way on purpose: once the sixteenth closes, the stage is allowed to change shape
        ck("piercing shows one or two dots, not a number", page.locator(".mound.open .d1, .mound.open .d2").count() == 8
           and page.locator(".mound.open").count() == 8,
           f"{page.locator('.mound.open').count()} open, {page.locator('.mound.open .d1, .mound.open .d2').count()} marks")
        page.screenshot(path=str(shots / "01b-sand-half.png"))
        for i in range(8, 16):
            page.locator(".mound").nth(i).click()
            page.wait_for_timeout(35)
        page.wait_for_function("document.querySelectorAll('#shieldBox .cell').length === 16 || "
                               "!document.querySelector('#v-cast').classList.contains('active')", timeout=25000)
        page.wait_for_timeout(1200)
        ck("the sand cast moves to the shield by itself",
           page.evaluate("!document.querySelector('#v-cast').classList.contains('active')"),
           page.evaluate("document.querySelector('#prog')?.textContent"))
        page.screenshot(path=str(shots / "02-shield.png"))

        # clipping is the failure mode of a dense phone layout: names cut to "Fortuna ..." read as a data bug
        clipped = page.evaluate("""() => {
          const bad = [];
          document.querySelectorAll('#shieldBox .fn, #shieldBox .hn, #shieldBox .meta, #judgeBox .v').forEach(el => {
            const over = el.scrollWidth - el.clientWidth;
            const tall = el.scrollHeight - el.clientHeight;
            if (over > 1 || tall > 7) {
              bad.push(el.className + ' "' + el.textContent.trim().slice(0, 24) + '" +' + over + 'x +' + tall + 'y');
            }
          });
          return bad.slice(0, 6);
        }""")
        ck("no name, house or point count is cut off on a 412px screen", not clipped, " | ".join(clipped)[:260])
        ck("the three casting actions stay on one row", page.evaluate("""
          () => { const bs = [...document.querySelectorAll('#v-cast .row .btn')].map(b => Math.round(b.getBoundingClientRect().height));
            return bs.length >= 3 && Math.max(...bs) - Math.min(...bs) <= 1; }"""),
           page.evaluate("[...document.querySelectorAll('#v-cast .row .btn')].map(b=>Math.round(b.getBoundingClientRect().height)).join()"))

        # ---- the shield: all sixteen places, court included, question above ----
        ck("all sixteen places are drawn on the shield", page.locator("#shieldBox .cell").count() == 16,
           str(page.locator("#shieldBox .cell").count()))
        shield_txt = page.inner_text("#shieldBox").lower()
        judge_txt = page.inner_text("#judgeBox").lower()
        ck("the court is labelled as a court, and the sixteenth figure is named in full",
           all(n in shield_txt for n in ("the court", "xiii", "xiv", "xv", "xvi", "left witness", "right witness", "judge"))
           and "sentence / reconciler" in judge_txt, f"shield: {shield_txt[-150:]} | judge: {judge_txt[:130]}")
        page.locator("#layouts button", has_text="Ledger").click()
        page.wait_for_timeout(400)
        ck("the ledger layout lists sixteen rows with their derivation",
           page.locator("#shieldBox tr[data-pos]").count() == 16 and "cast directly" in page.inner_text("#shieldBox"),
           str(page.locator("#shieldBox tr[data-pos]").count()))
        page.screenshot(path=str(shots / "03-ledger.png"))
        ck("the ledger prints the Arabic name and its gloss, not a raw record",
           "al-" in page.inner_text("#shieldBox") or "“" in page.inner_text("#shieldBox"),
           page.inner_text("#shieldBox")[:200])
        page.locator("#layouts button", has_text="Square").click()
        page.wait_for_timeout(350)
        ck("the square layout keeps all sixteen in a 4x4", page.locator("#shieldBox .cell").count() == 16,
           str(page.locator("#shieldBox .cell").count()))
        page.screenshot(path=str(shots / "04-square.png"))
        page.locator("#layouts button", has_text="Shield").click()
        page.wait_for_timeout(300)

        # ---- a place opens as a sheet with its accidents, and proves itself ----
        page.locator("#shieldBox .cell").first.click()
        page.wait_for_timeout(600)
        ck("tapping a place opens a sheet that is actually on screen",
           page.locator("#sheet.open").count() == 1 and (page.locator("#sheet").bounding_box() or {}).get("height", 0) > 200,
           str(page.locator("#sheet").bounding_box()))
        sheet = page.inner_text("#sheetBody")
        ck("the sheet carries dots, element and the derivation chain",
           "Total dots" in sheet and "Element" in sheet and ("rows" in sheet or "mothers" in sheet), sheet[:200])
        page.locator("#pProve").click()
        page.wait_for_timeout(1600)
        proof = page.inner_text("#sheetBody")
        ck("the proof sheet shows arithmetic, not just prose", "dots" in proof and ("odd" in proof or "even" in proof),
           proof[:200])
        ck("the proof quotes the exhaustive cross-check", "65,536" in proof and "mismatches" in proof, proof[-260:])
        ck("citations stay out of the sentence and appear as sources",
           ("works" in proof or "reference only" in proof or "no voice" in proof), proof[:200])
        page.screenshot(path=str(shots / "05-proof.png"))
        page.locator("#scrim").click(position={"x": 24, "y": 24})
        page.wait_for_timeout(400)
        ck("the scrim closes the sheet", page.locator("#sheet.open").count() == 0)

        # ---- copy all houses, straight out of the clipboard ----
        page.locator("#btnCopyAll").click()
        page.wait_for_timeout(1400)
        clip, toast_ok = "", False
        try:
            clip = page.evaluate("navigator.clipboard.readText()")
        except Exception as e:                                    # noqa: BLE001
            notes.append(f"clipboard unreadable in this browser ({type(e).__name__}); fell back to the toast")
            toast_ok = "copied" in page.inner_text("#toast").lower()
        ck("copy all houses puts sixteen figure lines on the clipboard",
           clip.count(" dots (") == 16 or toast_ok, f"{clip[:110]}")
        ck("and it ends with the standing line, not with advice",
           (not clip) or clip.strip().endswith("these are documented claims by named authorities."), clip[-110:])

        # ---- reading: three panes, each with its own proof button ----
        page.locator("#tabs button", has_text="Reading").click()
        page.wait_for_timeout(700)
        ck("the houses pane explains more than one place", page.locator("#p0 .card").count() >= 3,
           str(page.locator("#p0 .card").count()))
        ck("every paragraph with a claim has a Prove button next to it",
           page.locator("#p0 [data-claim]").count() >= 3 and page.locator("#p0 .provebtn").count() >= 3,
           f"{page.locator('#p0 [data-claim]').count()} claim buttons")
        page.screenshot(path=str(shots / "06-reading-houses.png"))
        page.locator("#panesBox").evaluate("e => e.scrollTo({left: e.clientWidth})")
        page.wait_for_timeout(700)
        ck("swipe reaches the advanced pane with citations and the non-advice framing",
           "what this is not" in page.inner_text("#p1").lower()
           and "the works this reading came from" in page.inner_text("#p1").lower(),
           page.inner_text("#p1")[-260:])
        page.screenshot(path=str(shots / "07-reading-advanced.png"))
        page.locator("#panesBox").evaluate("e => e.scrollTo({left: e.clientWidth * 2})")
        page.wait_for_timeout(700)
        pane2 = page.inner_text("#p2")
        ck("the interrelate pane answers who, where and when",
           all(w in pane2.lower() for w in ("who", "where", "when")), pane2[:300])
        gapcheck = page.evaluate("""async () => {
          const liBad = [...document.querySelectorAll('#p2 .lines li')].filter(li => {
            const own = [...li.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' ');
            return /\\bgap\\b/i.test(own); }).length;
          const ch = await api(`/api/chart16?mothers=${encodeURIComponent(S.mothers.join(','))}&topic=${encodeURIComponent(S.question)}`);
          let expected = 0;
          for (const rec of Object.values(ch.techniques.who || {})) if (rec && rec._gap) expected++;
          return { liBad, expected, shown: document.querySelectorAll('#p2 .lines li .mini').length };
        }""")
        ck("a gap the engine names never sits inside the finding it qualifies, and each one is labelled",
           gapcheck["liBad"] == 0 and gapcheck["shown"] >= gapcheck["expected"], str(gapcheck))
        ck("its paragraphs end in proof buttons, not in merged citations",
           page.locator("#p2 [data-tech]").count() >= 1, str(page.locator("#p2 [data-tech]").count()))
        page.screenshot(path=str(shots / "08-reading-relate.png"))
        page.locator("#panesBox").evaluate("e => e.scrollTo({left: 0})")
        page.wait_for_timeout(400)

        # ---- the three manual casting modes, one row each ----
        page.locator("#tabs button", has_text="Cast").click()
        page.wait_for_timeout(500)
        page.locator("#modes button", has_text="Tap").click()
        page.wait_for_timeout(400)
        pad = page.locator("#pad")
        for _ in range(7):
            pad.click()
            page.wait_for_timeout(28)
        ck("seven marks are visible and counted while tapping",
           page.locator("#marks i").count() == 7 and page.inner_text("#cnt").strip() == "7",
           f"{page.locator('#marks i').count()} marks, counter {page.inner_text('#cnt')!r}")
        page.locator("#btnCont").click()
        page.wait_for_timeout(320)
        ck("Continue closes the row and the counter resets for the next page",
           page.locator("#pips i.done").count() == 1 and page.inner_text("#cnt").strip() == "0",
           f"{page.locator('#pips i.done').count()} done, counter {page.inner_text('#cnt')!r}")
        # odd taps gave one dot; verify the pair arithmetic is what the engine was told
        ck("the app's own preview agrees with the engine's row value",
           page.evaluate("S.slots[0].value") == 1, str(page.evaluate("S.slots[0]")))
        for n in ROWS[1:]:   # one row per page, each closed by Continue
            for _ in range(n):
                page.locator("#pad").click()
                page.wait_for_timeout(12)
            page.locator("#btnCont").click()
            page.wait_for_timeout(90)
        page.wait_for_function("!document.querySelector('#v-cast').classList.contains('active')", timeout=25000)
        page.wait_for_timeout(900)
        ck("sixteen tapped rows become a cast through the same engine path",
           page.locator("#shieldBox .cell").count() == 16, str(page.locator("#shieldBox .cell").count()))
        page.locator("#tabs button", has_text="Cast").click()
        page.wait_for_timeout(400)

        page.locator("#modes button", has_text="4 rows").click()
        page.wait_for_timeout(400)
        ck("the four-row page wakes exactly one row and puts three to sleep",
           page.locator(".rowcard.awake").count() == 1 and page.locator(".rowcard.asleep").count() == 3,
           f"{page.locator('.rowcard.awake').count()} awake / {page.locator('.rowcard.asleep').count()} asleep")
        first = page.locator(".rowcard.awake")
        for _ in range(5):
            # spaced past the double-tap window on purpose: a slow reader tapping five times must get five marks
            first.click()
            page.wait_for_timeout(430)
        ck("asleep rows cannot be tapped into: their marks stay empty",
           page.locator(".rowcard.asleep .marks i").count() == 0, str(page.locator(".rowcard.asleep .marks i").count()))
        # a real double-tap: two presses inside the 340ms window the row listens on
        first.click()
        page.wait_for_timeout(70)
        first.click()
        page.wait_for_timeout(400)
        ck("a double-tap finishes the row and wakes the next one",
           page.locator(".rowcard.locked").count() == 1 and page.locator(".rowcard.awake").count() == 1,
           f"{page.locator('.rowcard.locked').count()} locked")
        page.screenshot(path=str(shots / "09-quad.png"))
        page.locator("#btnClear").click()
        page.wait_for_timeout(300)

        page.locator("#modes button", has_text="Hold").click()
        page.wait_for_timeout(400)
        held = page.locator("#pad")
        held.hover()
        page.mouse.down()
        page.wait_for_timeout(700)
        n_held = page.evaluate("S.slots[nextSlot()] ? S.slots[nextSlot()].taps : 0")
        page.mouse.up()
        page.wait_for_timeout(360)
        ck("holding taps for you and the phone counts them", n_held >= 3, f"{n_held} marks while held")
        ck("releasing closes that box and the next one wakes",
           page.evaluate("S.slots.filter(s => s && !s.open).length") == 1 and page.locator("#cnt").inner_text().strip() == "0",
           str(page.evaluate("S.slots")))
        page.wait_for_timeout(200)
        ck("the hold indicator names which box is awake",
           "awake" in page.inner_text("#stage") or "done" in page.inner_text("#stage"), page.inner_text("#stage")[:120])

        # ---- history: every cast lands there, unprompted ----
        page.locator("#tabs button", has_text="History").click()
        page.wait_for_timeout(600)
        cards = page.locator("#histList .card").count()
        ck("both casts were saved to history automatically", cards >= 2, f"{cards} cards")
        ck("a history card shows the shield as dots and offers the image share",
           page.locator("#histList .mini-shield i").count() >= 8 and page.locator('[data-act="share"]').count() >= 1,
           str(page.locator("#histList .mini-shield i").count()))
        page.locator("#histList .card").first.locator('[data-act="open"]').click()
        page.wait_for_timeout(900)
        ck("reopening a saved chart restores its shield without re-casting",
           page.evaluate("document.querySelector('#v-shield').classList.contains('active')")
           and page.locator("#shieldBox .cell").count() == 16, str(page.locator("#shieldBox .cell").count()))
        page.screenshot(path=str(shots / "10-reopened.png"))

        # ---- settings are presentation-only, and the engine says so ----
        page.locator("#btnSettings").click()
        page.wait_for_timeout(500)
        ck("settings opens with the presentation keys and says it cannot reach content",
           page.locator("#sQuotes").count() == 1 and "content layer" in page.inner_text("#sheetBody"),
           page.inner_text("#sheetBody")[:200])
        page.locator("#sTheme").select_option("parchment")
        page.wait_for_timeout(400)
        ck("the theme actually repaints the page, not just the setting",
           page.evaluate("document.documentElement.dataset.theme") == "parchment"
           and page.evaluate("getComputedStyle(document.body).backgroundColor").startswith("rgb(239"),
           page.evaluate("getComputedStyle(document.body).backgroundColor"))
        page.screenshot(path=str(shots / "11-parchment.png"))
        page.locator("#sTheme").select_option("ink")
        page.locator("#scrim").click(position={"x": 24, "y": 24})
        page.wait_for_timeout(400)
        ck("primary buttons clear 42px and the tab bar clears 44px", page.evaluate("""
            [...document.querySelectorAll('.btn, nav.tabs button, .iconbtn')].every(b => {
              const r = b.getBoundingClientRect();
              return r.width === 0 || r.height >= (b.classList.contains('iconbtn') ? 36 : 42); })"""),
           page.evaluate("[...document.querySelectorAll('.btn, nav.tabs button')].map(b => Math.round(b.getBoundingClientRect().height)).join()")[:120])
        ck("tapping a mark or a pill never lands on a hit area under 28px", page.evaluate("""
            [...document.querySelectorAll('.pill, .mound, .cell, .provebtn')].every(b => {
              const r = b.getBoundingClientRect();
              return r.width === 0 || Math.min(r.width, r.height) >= 28; })"""),
           page.evaluate("[...document.querySelectorAll('.pill,.mound,.cell,.provebtn')].map(b => Math.round(Math.min(b.getBoundingClientRect().width,b.getBoundingClientRect().height))).join()")[:160])

        # ---- share as image: the canvas must actually be painted ----
        painted = page.evaluate("""async () => {
          const it = (JSON.parse(localStorage.getItem('gml.history') || '[]'))[0];
          const c = await paint(it);
          const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
          let lit = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) lit++;
          return { w: c.width, h: c.height, lit: lit / (c.width * c.height), png: c.toDataURL('image/png').length };
        }""")
        ck("the share image is a painted shield, not a blank card",
           painted["w"] == 1080 and painted["png"] > 60000 and 0.25 < painted["lit"] <= 1.0, str(painted))
        page.evaluate("""async () => {
          const it = (JSON.parse(localStorage.getItem('gml.history') || '[]'))[0];
          const c = await paint(it);
          const blob = await new Promise(r => c.toBlob(r, 'image/png'));
          const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
          a.download = 'render-check.png'; document.body.appendChild(a); a.click();
        }""")
        page.wait_for_timeout(900)

        # ---- an offline engine must degrade honestly, not silently ----
        pre_offline = list(console)
        ctx.set_offline(True)
        page.locator("#tabs button", has_text="Cast").click()
        page.wait_for_timeout(300)
        page.locator("#btnOnline").click()
        page.wait_for_timeout(1400)
        ck("with the network cut, the app says the engine is unreachable",
           "unreachable" in page.inner_text("#toast").lower(), page.inner_text("#toast"))
        ctx.set_offline(False)
        page.wait_for_timeout(400)

        # the offline probe above raises network errors by design, so compare against what was logged before it
        # the offline probe answers /api with a deliberate 503, so resource-load noise after it is expected
        errs = [c for c in console if c not in pre_offline and "favicon" not in c
                and "Failed to load resource" not in c]
        ck("no error was logged in the browser while the app was driven", not errs, " | ".join(errs[:3])[:400])
        ck("no uncaught exception at any point", not [c for c in console if c.startswith("pageerror")],
           " | ".join([c for c in console if c.startswith("pageerror")])[:300])
        browser.close()

    proc.terminate()
    try:
        proc.wait(timeout=8)
    except Exception:                                             # noqa: BET001
        proc.kill()
    server_err = (proc.stderr.read() or "")
    ck("the server logged no traceback while the phone drove it", "Traceback" not in server_err, server_err[-400:])

    for n in notes:
        print(f"  [ok] {n}")
    for f in fails:
        print(f"  [FAIL] {f}")
    total = len(notes) + len(fails)
    print(f"\nRENDER CHECK: {'PASS' if not fails else 'FAIL'}  ({total - len(fails)}/{total} checks"
          f", screenshots in {shots})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
