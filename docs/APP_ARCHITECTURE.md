# App architecture (decided)

This is the runtime plan for the phone app. It does **not** replace the Python research
engine. It stops the phone from having to run Python.

The problem we had: `app/mobile.html` is a window onto `app/server.py`. Casting and
reading required a Python process (Termux on the phone, or a laptop on the LAN). That
is why the APK asked for an engine address, why GitHub Pages was refused, and why
updates felt like “open the Python engine”. Python is the right language for OCR,
harvesting, and proving the library. It is the wrong language to ship on a 1 MB APK.

## Decision

| Piece | Stays | Moves |
|---|---|---|
| OCR, harvest, provenance gates, 65,536 Python oracle | `engine/`, `scripts/`, `kb/` | — |
| Chart arithmetic (Mothers → Daughters → Nieces → Witnesses → Judge → Reconciler, Via Puncti, projection, Part of Fortune, motus) | Python as **reference** | `web/engine.js` as **runtime** |
| Knowledge (passages, outcomes, voices) | GitHub `library/dataset/` | fetched by the app via jsDelivr, cached on the phone |
| UI | Prototype look (`CAST NOW`, sand, tap, hold, shield, prove) | `web/` then wrapped by the existing `android/` shell |
| AI | Optional, later | Never decides a rule. Receives a grounding pack only |

**Python on the phone: no.**
**Paid host / paid LLM for v1: no.**
**New GitHub account: no.** We update `Almuarif17/geomancy`.
**New data repo (`geomancy-data`): later**, if the research tree gets too heavy for the CDN path. Not required to start.

This is the backlog item already named in `notes/APP.md`:

> Generate `app/engine.js` from the Python engine, then run *node* over all 65,536
> shields and require zero mismatches against Python before the artefact may be committed.

`web/engine.js` is that artefact’s first commit. It is allowed to exist **only** because
it will be proved against `engine/oracle.py`, not because we wanted a second opinion.

## Flow on the phone

```
CAST (local, no network)
  sixteen rows → four Mothers
        ↓
COMPUTE (web/engine.js, local)
  Daughters, Nieces, Witnesses, Judge, Reconciler
  Via Puncti, projection, Part of Fortune, motus
        ↓
RETRIEVE (jsDelivr, only what this question needs)
  manifest.json → hash diff → one outcome shard / figure shard
  cache in localStorage / IndexedDB
        ↓
INTERPRET (templates + library rows)
  every sentence carries CALCULATED / SOURCED / CORROBORATED / DISPUTED / NOT ATTESTED
  gaps stay gaps
        ↓
PROVE
  arithmetic + work + folio
        ↓
optional AI (later)
  grounding pack in, no extra rules out
```

Offline after the first fetch of `core_facts.json` (CC0, tiny) plus any shards already
cached. A new cast never needs the radio. A new *reading* needs the radio only if that
outcome shard is not on the device yet.

## What the APK contains

- HTML/CSS/JS UI (prototype v2 look)
- `web/engine.js` (chart math)
- `library/dataset/core_facts.json` (CC0 figure bits and house routing)
- Android WebView shell already in `android/`

What the APK does **not** contain: OCR dumps, `corpus/`, Python, the full passage set.

Knowledge updates: fetch `library/dataset/manifest.json` from

`https://cdn.jsdelivr.net/gh/Almuarif17/geomancy@<tag>/library/dataset/manifest.json`

diff per-file hashes, download only changed shards. The APK version does not have to
move when a book is added.

## Licence (do not mix the layers)

- L1 code — MIT (`web/engine.js` included)
- L2 `core_facts.json` — CC0 (may ship in the APK, including commercially)
- L3 curated dataset — CC BY-NC 4.0 + commercial licence on request

The phone may cache L3 for the owner’s own reading. A revenue-bearing product needs
the commercial licence before it redistributes L3. See `LICENSING.md`.

## What we will not do

- Require Termux or `app/server.py` for a normal user.
- Send a whole chart to an LLM and ask it to interpret.
- Download the whole GitHub tree onto the phone.
- Invent a ruling the registry marks `NAMED_ONLY`.
- Put a second, unproved copy of the rules in Java.

## Status

- [x] Architecture written (this file)
- [x] `web/engine.js` chart core + 65,536 self-check in Node
- [ ] Node vs `engine/oracle.py` differential in CI
- [ ] CDN retrieval + manifest hash cache
- [ ] Phone UI (prototype v2) talking only to `web/engine.js` + CDN
- [ ] APK with no engine-address dialog
