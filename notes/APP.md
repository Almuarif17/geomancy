# The phone app

A reader that runs on an Android phone, casting geomancy by hand and reading it against the sources in this
repository. It is one HTML file, a manifest, a service worker and two icons - `app/mobile.html`,
`app/manifest.webmanifest`, `app/sw.js`, `app/icon-192.png`, `app/icon-512.png` - served by the same
`app/server.py` the desktop reader uses. There is no second app, no separate bundle, no build step.

## The rule this app lives by

**The phone counts marks. The library decides what they mean.**

Every figure, derivation, technique, quotation and citation comes from `engine/` over `/api/*`. The page sorts,
labels, truncates and paints; it never re-derives a rule, because a second implementation of the rules is a second
source of truth and the two drift. The one exception is deliberate: `rowValue(taps)` in `mobile.html` - pairs of
marks become two dots, a leftover single becomes one - is duplicated so a figure can appear the instant a row
closes. `app/test_app.py` extracts that expression from the shipped page and holds it against
`deep_read.add` for every pair of row counts from 1 to 60 (3,600 comparisons), so the preview cannot drift from
the cast.

Settings travel the same way. A phone sends its preferences with each request; `merge_prefs()` in the server
accepts nine presentation keys and drops everything else, then reports what it dropped in `prefs_echo` - and the
settings screen prints that line, so a user can see the engine refused to be told what a source said.

## Casting, four ways

All four produce the same object: sixteen rows, each one dot or two, in the order I-IV, V-VIII, IX-XII, XIII-XVI.
All four hand the raw counts to `POST /api/cast_from_rows` and let the engine re-count them.

| mode | what happens | how a row closes |
|---|---|---|
| **Sand** | sixteen patched hills. Piercing one gives up a dot - one or two, at random, in any order | the sixteenth pierce casts by itself |
| **Tap** | one row per page, sixteen pages. Tap as many times as the row wants | **Continue** pairs them off (odd leftover → 1, exact pairs → 2) and turns the page |
| **4 rows** | four rows on a page, four pages. Only the awake row takes taps; the other three are dimmed and deaf | double-tap the awake row, or press Done. After four rows the mother forms and the next page opens |
| **Hold** | press and hold; the phone taps for you and buzzes as it counts | release closes that box and wakes the next. Four boxes form a mother |

After each four rows a mother is fixed and shown with the taps behind it. After sixteen, the shield, the
daughters, the nephews, the witnesses, the Judge and the Reconciler are the engine's, not the app's.

## Screens

- **Shields** - three renderings of the same sixteen places: the classical shield (mothers, daughters, nephews,
  court, each block labelled with how it was made), a 4x4 square, and a ledger table with the Arabic figure name,
  the dots and the derivation chain per row. The question is drawn above the shield. Tap any place for its
  accidents and the sources that speak to it. **Copy all houses** puts the whole plain-text block on the
  clipboard; **Share as image** paints a 1080x1350 PNG - question, four mothers, daughters, Judge - and hands it
  to Android's share sheet, falling back to a download when there is none.
- **Reading** - three panes, swiped: **Houses** (each of the twelve, then the court, with the claimed lines and
  the named silences), **Advanced** (validity, perfection, complexions, motus, parentage, way of the points,
  projection, triplicities, the Arabic and Ifá correspondences, and which works the reading came from), and
  **Interrelate** (who, where, when and how many - the engine's own findings, not prose written by this app).
  Citations are never folded into a sentence: each paragraph ends in a **Prove** button that opens the arithmetic
  that produced the figure, the voices that carry the claim - quotations for what may be quoted, a work and folio
  for what may not - and the differential panel: 65,536 casts, 0 mismatches, seven fields, from
  `library/dataset/evaluation.json` rather than from a string typed into the page.
- **History** - every cast, saved on the device as it happens, with its dots drawn small. Tap to reopen without
  re-casting; press and hold to share it as an image. Export copies the whole list as JSON; clear all deletes it
  here and nowhere else.
- **About** (top left) and **Settings** (top right), plus an engine-reachable light by the title that is the only
  honest thing to show when the server is not there.

## Installing it on a phone

**No APK is built in this repository, and none can be: there is no Android SDK here, and anything that costs money
is out of scope.** The install path is the one Android already has: Chrome → *Add to home screen*. The manifest
makes it standalone, portrait, icon'd, with a service worker so the interface opens in a plane. `app/check_render.py`
and the CI render gate test the installed surface at 412x915 (a TECNO K17's CSS viewport).

Two ways to reach the engine, and one that is deliberately not offered:

1. **On the phone itself - recommended.** Termux (free, F-Droid or Play), then
   `pkg install python git && pip install pyyaml`, `git clone` the repo, `python3 app/server.py --port 8044`,
   and open `http://localhost:8044/m` in Chrome. Add to home screen. The engine is standard-library Python plus
   PyYAML; nothing else is needed, and nothing leaves the device. Termux:Boot starts it on power-up.
2. **Over the local network.** Run `python3 app/server.py --host 0.0.0.0 --port 8044` on a laptop and open
   `http://<laptop>:8044/m` on the phone. Same-origin, no tunnel, no third party. The server already binds
   `0.0.0.0` by default for this reason. Casts, readings, proofs and history all work this way; **the home-screen
   install will not**, because Android only treats `https://` and `http://localhost` as secure contexts, and a
   plain `http://192.168.x.x` address is neither, so the service worker and the install prompt stay switched off.
   That is the whole argument for path 1 over path 2: same code, same engine, and the phone lets it be installed.
3. **Not offered: GitHub Pages, and any other static host.** Pages serves files, not Python, and the interesting
   half of this library is computed - the cast and the audit. A static page would have to re-implement the engine,
   which is exactly the thing the rule above exists to prevent. If the app is ever to work with no server at all,
   it will be because the engine was *ported and proved*, not because a second copy was written:

   **Backlog - the offline engine.** Generate `app/engine.js` from `engine/deep_read.py` plus a committed
   claims-by-(figure,house) table, then extend the differential harness to run *node* over all 65,536 shields and
   require zero mismatches against Python before the artefact may be committed. That keeps one source of truth
   with a proof between the two copies, and it makes the PWA work with the radio off. It is a real build, not a
   flag.

## What the app will not do

- It will not fill a gap. If no passage reaches a house, the card says so, in the same voice as the rest, and the
  engine's own `_gap` fields are labelled "named gap in the library" rather than smoothed into the finding.
- It will not present itself as advice. The standing line ships with every copy block:
  *not advice, and not a prediction: these are documented claims by named authorities.*
- It will not quote what the licence does not allow. `cite_only` voices are rendered as work, folio and editor,
  never as a paraphrase dressed up as a quotation.
- It will not phone anything home. There is no analytics, no CDN, no font, no account; the request log on the
  server is one line per cast.

## Testing

```bash
python3 app/test_app.py        # 55 contract checks: routes, tap arithmetic, the whitelist, the copy block
python3 app/check_render.py    # 50 render checks in headless Chromium at 412x915
```

`check_render.py` drives the real thing: pierces sixteen hills, taps sixteen rows, double-taps a four-row page,
holds the button, opens the proof sheet, reads the clipboard, reopens a saved chart, cuts the network, and fails
if any name is clipped, any `[object Object]` reaches a screen, any console error appears, or the arithmetic shown
by the app stops agreeing with `deep_read.add`. It prints `SKIP` and exits 0 where Playwright is absent, so a
machine without a browser can still build the library - and CI installs one and runs it (`.github/workflows/validate.yml`).

Both are wired into `python3 library/tools/validate.py --build`, so a release cannot be published with a broken app.
