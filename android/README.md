# The Android shell

One page, two ways to run it. The browser is served `app/mobile.html` by `app/server.py`; this directory builds the
same bytes into an installable package, and adds the four things a web page cannot do on a phone by itself.

```bash
python3 android/build.sh            # -> android/dist/D-Gem.apk  (fetches the toolchain if it is not in $ANDROID_HOME)
python3 android/build.sh --check    # gate the sources; needs no Android toolchain at all, so CI can always run it
python3 android/build.sh --clean    # remove build/ and dist/
adb install -r android/dist/D-Gem.apk
```

Nothing here is committed except source: `build/`, `dist/`, the debug keystore and the SDK are all gitignored. The
APK is a release asset (like `library/dataset/geomancy.sqlite`): reproducible from a clean tree, so the tree is the
thing under version control.

## What the shell is

* a WebView pointed at `https://geomancy.local/mobile.html`, a host that does not exist, answered locally
* the page's own files at `assets/www/` — `android/prepare.py` copies them out of `../app/` at build time, so
  there is no second copy of the app in here to rot; `--check` fails the repo if one ever appears
* `Engine.java`, the only thing in the package that can touch a network, which forwards `/api/*` to whatever
  address the user types into the connection dialog (`SharedPreferences`, default `http://127.0.0.1:8044`)
* a `Bridge` object (`window.Android`) for haptics, keeping the screen awake mid-cast, handing the drawn shield to
  the share sheet, and setting that address from the page's own offline banner

It contains no geomancy. No figure names, no house tables, no quotations, no arithmetic — `grep -i 'via\|populus'
src/` returns nothing but the word "WebView". If you want to know what the chart means, the answer is in the
Python, and if the Python is unreachable the app says so rather than inventing a reading.

## Why a made-up https origin

`http://192.168.1.40:8044/m` opens fine in Chrome on a phone and cannot be installed: Android counts only
`https://` and `http://localhost` as secure contexts, so the service worker, the install prompt and clipboard
access stay switched off on a plain LAN address. Serving the page from a *fake https* host inside the WebView fixes
that without lying about where the data comes from: the page thinks its origin is `https://geomancy.local`, so
relative `/api/` URLs work untouched (no CORS preflight, no host baked into the file) and the WebView grants what
an https origin grants; `shouldInterceptRequest` then answers from the APK, and a POST — which an interceptor
cannot even see the body of — goes through `Android.request()` instead.

## Building it from nothing

`build.sh` needs a JDK (`javac`) and the Android tools, and will fetch the tools itself:

```
https://dl.google.com/android/repository/build-tools_r33.0.2-linux.zip   # aapt2, d8, zipalign, apksigner
https://dl.google.com/android/repository/platform-33_r02.zip             # android.jar
```

Both are free, need no account, and land in `$ANDROID_HOME` (default: `<repo>/.android-sdk`). Then:
`aapt2 compile` + `link` (which also writes `R.java` and copies `assets/`), `javac` against `android.jar`
**plus** `build-tools/*/core-lambda-stubs.jar` (android.jar's `LambdaMetafactory` is an empty stub, so without the
stubs jar the first lambda in the source fails to compile), `d8`, `zip` the dex in, `zipalign`, `apksigner sign`
with a keystore generated on the spot.

Gradle and Android Studio are not required and were deliberately not used: they add a wrapper that downloads a
distribution, a daemon, and a licence prompt, in exchange for nothing this build needs — four files, one activity,
no dependencies.

## Signing, and what it is for

`debug.keystore` is created in `build/` on a clean tree (alias `geomancy`, both passwords `android`, 10 000 days)
and never committed. That is enough to sideload: Android requires a signature to install, not a trusted one, and
the APK is signed with the v2/v3 schemes so modern Android accepts it.

It is **not** enough for the Play Store, which needs an upload key whose loss is unrecoverable, an AAB, and a
44 € one-time fee. If a store listing is ever wanted, the sequence is: keep `build.sh`'s steps, swap `apksigner`'s
keystore for a real one held somewhere that outlives this repository, and split the dex/asset packaging into an
AAB. Nobody has chosen that yet, and nothing here pretends the debug key is a substitute for it.

## Troubleshooting

| Symptom | What it actually means |
| --- | --- |
| "Nothing is answering at …" in the Cast screen | The dialog's address is wrong or the server is not running. Start `python3 app/server.py --host 0.0.0.0 --port 8044`, and use the laptop's LAN address — not `localhost`, which is the phone itself. |
| Page opens but no reading appears, and no dialog | The engine answered with something that is not JSON. Check `curl http://<host>:8044/api/health` from another machine on that network. |
| Install blocked by the phone | "Install unknown apps" must be allowed for the app that opens the file (Files, or your messenger). Expected for a sideloaded debug build. |
| Casting stops when the screen sleeps | The lock is held only while the Cast view is open, on purpose; if the phone's own battery settings kill background apps, exempt this one. |
| Cleartext errors on some custom ROM | `res/xml/network.xml` permits cleartext — the engine is http by design. See `notes/ANDROID.md` for why the alternative was not chosen. |

## Licence

MIT, like all code in this repository, including the readings it displays — the licence attaches to the *page*,
not the wrapper. `LICENSING.md` has the layers.
