# The Android shell: why it is shaped like this

`android/` is a WebView around `app/mobile.html`, plus one proxy and four bridge methods. This is the record of why
those parts and not others. The user-facing how-to is `android/README.md`.

## The problem it solves

Two install paths already work: run the engine in Termux and add `http://localhost:8044/m` to the home screen, or
open `http://<laptop>:8044/m` on the LAN. The second is more convenient and cannot be installed at all — Android
counts only `https://` and `http://localhost` as secure contexts, so a service worker and an install prompt are
switched off on any address of the form `http://192.168.x.x`. Fixing that in the page would mean either hard-coding
a host (which breaks "the page carries no origin", and with it the ability to move the server) or re-implementing
the engine in JavaScript (which the repository refuses to do twice).

So the fix goes in the wrapper instead: give the page an origin of its own that nobody has to trust.

## The one trick worth reading twice

The WebView is pointed at `https://geomancy.local/mobile.html`, a host that will never resolve. Nothing is fetched
from it. `shouldInterceptRequest` answers every request that origin can make:

* paths that name a file come out of `assets/www/` in the package — the page's own `icon-192.png`, its manifest,
  and `mobile.html` itself, copied from `../app/` at build time by `android/prepare.py`
* paths under `/api/` go to the engine address the user named, and the answer is re-tagged as if it had come from
  the same origin, so the page never sees a cross-origin response and no CORS is configured anywhere
* any other host gets a 403 with a one-line reason, so a future edit cannot silently make this app load something
  from the internet

The consequences are all favourable: relative URLs need no change, `isSecureContext` is true so clipboard write
works, no website can be tricked into probing a local engine (only this process can, and only to the address stored
on the device), and the bytes inside the APK are byte-identical to the ones `app/check_render.py` drives — which is
a check, not a hope: `python3 app/test_app.py` fails if a hand-made copy of the page ever appears under `android/`.

`POST` is the exception that shaped the design. A WebView client is not given the *body* of a request it
intercepts, so a page inside one cannot POST to its own origin by proxying alone. `Android.request(method, path,
body)` — a synchronous `@JavascriptInterface` call returning one JSON string `{status, type, body}` — is the way
round it, chosen over adding a GET twin of `/api/cast_from_rows` because that would have put a second, weaker API
in the server forever, and over `WebViewAssetLoader`/`shouldInterceptRequest` + a request queue, which would have
made the page handle its own request lifecycle for no gain.

## What the shell refuses to know

No figure names, no house tables, no quotations, no arithmetic. The `--check` gate proves the absence of the thing
a copy would need rather than the thing a comment might mention: none of the sixteen bit patterns from
`library/dataset/core_facts.json` and no figure name in a string literal may appear in the Java. Mutating one in
does fail it — that mutation was run, not assumed.

The only arithmetic in the whole phone app remains `rowValue()` in the page, and `app/test_app.py` diffs it against
`deep_read.add` for 1..60 so it cannot drift from the engine's parity rule.

## Deliberately not used

| Option | Why not |
| --- | --- |
| Gradle + Android Studio | A wrapper that downloads a distribution, a daemon and a licence prompt, to configure four files and no dependencies. It also implies committing `gradle-wrapper.jar` — a binary in git that nothing here can audit. |
| Capacitor / Cordova | Both insist on owning a copy of the web app in their own `www/`, which is exactly the drift `prepare.py` exists to prevent, and both drag in npm for a WebView and five method calls. |
| TWA / Bubblewrap | A trusted web activity is a Chrome tab around an *already-installed* PWA: it needs a publicly reachable `https://` origin with a certificate, i.e. hosting to pay for and a domain to renew. |
| A Play Store listing | 44 € once, an upload key that must outlive the repository, and an AAB. Out of scope while "nothing that costs money" stands; the signing notes in `android/README.md` are the way round if that ever changes. |
| An emulator to prove it runs | Multi-hundred-MB image, KVM that a container will not have, and a first-run flow nobody is watching. The verification here is the compile, the link, the signature, and the browser gate over the same bytes — see "What is proved" below. |

## Two decisions that were argued and settled

**Cleartext is permitted** (`res/xml/network.xml`), against the reflex "cleartext on is insecure". The reasoning in
that file is the real one: the only component with a socket is `Engine.java`, the address it uses is one the user
typed, and the payload is dot counts plus a question with no account, cookie or identifier in it — so the exposure
is a neighbour on the same Wi-Fi reading a chart, while the alternative is an app that cannot reach its own engine.
Android cannot express "private ranges only" there anyway: `<domain>` matches hostnames, not CIDRs, and the engine
host is by design arbitrary. A public host is still refused until confirmed, with a toast that says plainly what
will leave the phone.

**No signing key in git.** `debug.keystore` is generated in `build/`, and `build/` is ignored. A committed keystore
would be indistinguishable from a leak to anyone reading the tree, and buys nothing: any self-signed key installs
fine off the Play Store.

**The version lives in one place.** `AndroidManifest.xml` has no `versionName`; `build.sh` reads the top CHANGELOG
heading — the line `/api/health` reports and the tagger tags — and passes `--version-name` to `aapt2 link`, with
`versionCode` as the same triple as an integer (0.2.6 → 206). An APK stamped with its own version is an APK that
quietly stops matching the engine inside it.

## What is proved, and what is not

Proved, on every build: `javac` compiles against `android.jar` (API 33) — which caught three real mistakes:
`setGeolocationEnabled` is on `WebSettings`, `MediaStore.Images.insertImage` returns a `String`, and a `\u` in a
Java *comment* is a compile error because unicode escapes are translated before comments are read. `d8` dexes it,
`zipalign` and `apksigner verify` pass, `aapt dump badging` reports `app.geomancy`, label Geomancy, minSdk 26,
target 33, and `assets/www/mobile.html` compares byte-identical to the file in `app/`. And 14 checks in
`app/check_render.py` drive the entire app through a scripted clone of the bridge contract in a real browser: the
same JSON back from the bridge as from `fetch`, non-ASCII surviving as characters rather than bytes, a cast
reaching the engine through `Android.request` rather than being computed locally, the screen lock following the
view, the shield arriving as a PNG rather than a download, no service-worker attempt, and the offline banner naming
the address it tried.

Not proved here: that Android's WebView paints it on a handset. There is no emulator in this environment and none
was installed, so the last step is a person with a phone. That gap is stated rather than glossed, and the checklist
below is what to look at when someone is.

## First-install checklist (for whoever has the device)

1. Open the app. If the engine is not at `127.0.0.1:8044`, a dialog should appear before any cast is attempted.
2. Point it at the laptop's LAN address. The Cast screen should fill; About should show the version *and* that address.
3. Cast in sand mode and watch the screen stay on until you leave the tab, then let it sleep on the Shields tab.
4. Tap a row: the motor should fire (Settings → haptics off should stop it, which is the page's rule, not the shell's).
5. Share the shield from the Cast screen — the Android share sheet, and a file under `Pictures/Geomancy`.
6. Kill the engine, tap Refresh. The banner must name the address it tried, and *History* and saved readings must
   still open. This is the app behaving correctly, not a bug.
7. Rotate the phone. It is locked to portrait in the manifest because the layout is; nothing should re-load.
8. Airplane mode with the engine in Termux on the device: a new cast must fail honestly, and the last saved chart
   must still read. Nothing here promises offline casting — see the offline-engine backlog in `notes/APP.md`, which
   is also what would let this shell drop the address dialog entirely.
