#!/usr/bin/env bash
# Build the Android shell around the phone app: no Gradle, no Android Studio, no account, nothing paid.
#
#   android/build.sh              produce build/D-Gem.apk (debug-signed, sideload it)
#   android/build.sh --check      validate the inputs and stop (this is what the repo gate runs)
#   android/build.sh --clean      remove generated output
#
# What has to exist first, and why none of it is in git:
#   a JDK (javac), the Android build-tools, and a platform's android.jar. Those are two free zips from Google
#   with no licence and no signup, so they are downloaded on demand rather than vendored into the repository:
#
#     https://dl.google.com/android/repository/build-tools_r33.0.2-linux.zip
#     https://dl.google.com/android/repository/platform-33_r02.zip
#
# Set ANDROID_HOME to a directory already holding build-tools/33.0.2 and platforms/android-33 to skip the
# download. The signing key is generated into build/ on every clean tree and never committed: a debug key is
# the right thing for an APK you install yourself, and the wrong thing for Play, where the upload key has to
# outlive this repository and would have to be kept somewhere that is not a build script.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
A="$ROOT/android"; B="$A/build"; D="$A/dist"
NAME="tellus-loquens"              # the file you send someone; the launcher label is in res/values/strings.xml
MIN_SDK=26 TARGET_SDK=33
BT_VER=33.0.2
BT_ZIP=build-tools_r33.0.2-linux.zip
PF_ZIP=platform-33_r02.zip

sdk="${ANDROID_HOME:-$ROOT/.android-sdk}"
# the JDK is wherever the machine keeps one: $JAVA_HOME, else whatever `javac` resolves to. Hard-coding
# /usr/lib/jvm/jdk-11 made this script work on one box and fail on every other one.
if [ -z "${JAVA_HOME:-}" ] && command -v javac >/dev/null 2>&1; then
  JAVA_HOME="$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")"
fi
export PATH="$PATH:${JAVA_HOME:-/usr/lib/jvm/jdk-11}/bin:$sdk/build-tools/$BT_VER"

die() { echo "android/build.sh: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1; }

# The version comes from the repo, not from this file: the top CHANGELOG heading is the same line the tagger
# reads and /api/health reports, so an APK cannot be stamped with a version of its own and quietly disagree with
# the engine it talks to. versionCode is that triple as a monotone integer (0.2.6 -> 206) - enough to tell one
# sideloaded build from another, and not a Play Store upload key, which would have to outlive this repository.
VER="$(python3 - "$ROOT" <<'PYV'
import pathlib, sys
for line in pathlib.Path(sys.argv[1], "CHANGELOG.md").read_text().splitlines():
    if line.startswith("## "):
        print(line[3:].split(" -")[0].strip())
        break
PYV
)"
[ -n "$VER" ] || die "no version found in the top heading of CHANGELOG.md"
VC="$(python3 - "$VER" <<'PYC'
import sys
v = sys.argv[1].split("+")[0].split(".")
n = [int(x) if x.isdigit() else 0 for x in v] + [0, 0, 0]
print(n[0] * 10000 + n[1] * 100 + n[2])
PYC
)"
have_tools() { need aapt2 && need d8 && need zipalign && need apksigner && [ -f "$sdk/platforms/android-33/android.jar" ]; }

if [ "${1:-}" = "--clean" ]; then rm -rf "$B" "$D"; echo "cleaned"; exit 0; fi

if [ "${1:-}" = "--check" ]; then
  python3 "$A/prepare.py" --check
  # every rule the shell is built on, asserted against the file that enforces it. This exists because a shell
  # with the interceptor removed still installs and still shows a page - it simply never shows a reading, and
  # nothing but these lines would say so.
  python3 - "$A" <<'PYCHK'
import json, pathlib, re, sys, xml.dom.minidom as m
a = pathlib.Path(sys.argv[1])
tree = [f for f in list(a.rglob("*.xml")) + list(a.rglob("*.java")) + list(a.rglob("*.py"))
        if "build" not in f.parts and "dist" not in f.parts]   # generated, and checked by the build itself
for f in (x for x in tree if x.suffix == ".xml"):
    m.parse(str(f))
java = "\n".join(f.read_text() for f in sorted(a.rglob("src/**/*.java")))
sh = (a / "build.sh").read_text()
for src, must, why in [
    (java, "geomancy.local", "the page needs one origin of its own, or its relative /api/ calls have nowhere to go"),
    (java, "https://", "the shell origin must be https, or clipboard access is refused as insecure"),
    (java, "setAllowFileAccess(false)", "assets come through the interceptor; a WebView that reads the "
                                        "filesystem can be read by anything else on the device too"),
    (java, "setInstanceFollowRedirects(false)", "a redirect would carry an answer from a host nobody approved"),
    (java, "www/", "the page sits under assets/www in the APK, and the interceptor must look there"),
    (java, "UTF-8", "the body comes back as text, so the encoding has to be stated, not guessed"),
    (sh, "CHANGELOG.md", "the APK version is derived from the repo's own version line, never typed in here"),
    (sh, "core-lambda-stubs.jar", "android.jar alone cannot compile the lambdas this source uses"),
    # the two needles are split across concatenation on purpose: written as one literal, each would appear in
    # this check's own source, and the check would pass by matching itself whatever the build did
    (sh, 'touch -d "@${SOURCE' '_DATE_EPOCH', "every entry needs a fixed mtime, or a published sha256 of the APK "
                                            "is worth nothing and nobody can verify a download"),
    (sh, 'zip -q -X -D' ' -j', "the dex is added without directory entries or extra fields, for the same reason"),
]:
    if must.lower() not in src.lower():
        sys.exit("FAIL: {} is gone - {}".format(must, why))

# The rule this directory exists to obey: the shell carries no geomancy of its own. Prose is not evidence and a
# figure name in a comment is not a second implementation, so both checks are against the data a copy *would*
# need: the sixteen bit patterns, and any figure name in a string literal.
try:
    facts = json.loads(pathlib.Path(a.parent / "library/dataset/core_facts.json").read_text())
    figs = facts.get("figures") or {}
    patterns = {",".join(str(x) for x in v.get("pattern", [])) for v in figs.values() if v.get("pattern")}
    names = set(figs)
    hits = sorted(n for n in names if re.search(r'"\s*' + re.escape(n) + r'\s*"', java))
    pats = sorted(pt for pt in patterns if pt and pt in java)
    if hits or pats:
        sys.exit("FAIL: the shell has started to hold the rules it is meant to display: "
                 + ", ".join(hits + pats)[:200])
    print(f"  no figure name and none of the {len(patterns)} patterns appear in the Java - "
          f"the rules stay in the engine")
except FileNotFoundError:
    print("  (library/dataset/core_facts.json not built, so the no-rules check had nothing to compare against)")

# The header bug that put source code on a phone instead of a chart: a media type that already carries a charset,
# joined to the one WebResourceResponse appends, arrives as "text/html; charset=utf-8; charset=UTF-8", which is
# not a parseable document type - and with nosniff in the way the WebView shows the file as text rather than
# guessing. Both halves are asserted against the source, because nothing short of a handset shows the symptom.
eng = (a / "src/app/geomancy/Engine.java").read_text()
body = eng.split("static String assetType", 1)[1].split("\n    }", 1)[0]
if "charset" in body:
    sys.exit("FAIL: Engine.assetType is naming a charset again - the WebView appends its own and the page renders "
             "as source text")
for must, why in [
    ("new WebResourceResponse(type,", "the type handed to the WebView has to be the stripped one, not the raw header"),
    ('"X-Content-Type-Options", "nosniff"', "the hardening has to be there for engine answers at all"),
    ("if (api) {", "and only for them: nosniff on the app's own document is what turns a slightly-off type into "
                   "a screen of markup"),
]:
    if must not in java:
        sys.exit(f"FAIL: {must} is gone from MainActivity - {why}")
print("android/build.sh --check: PASS - manifest and resources parse, and the shell's own rules are in place")
PYCHK
  if ! have_tools; then
    echo "  (no Android toolchain here, so this stopped at the sources; install build-tools/$BT_VER and"
    echo "   platforms/android-33, or run without --check and the two free zips will be fetched)"
    exit 0
  fi
  echo "  toolchain present: $(command -v aapt2) - run android/build.sh without --check to build the APK"
  exit 0
fi

if ! have_tools; then
  mkdir -p "$sdk/build-tools" "$sdk/platforms" "$sdk/dl"
  for z in "$BT_ZIP" "$PF_ZIP"; do
    [ -f "$sdk/dl/$z" ] || { echo "fetching $z"; curl -sSfL -o "$sdk/dl/$z.part" "https://dl.google.com/android/repository/$z" && mv "$sdk/dl/$z.part" "$sdk/dl/$z"; }
  done
  [ -d "$sdk/build-tools/$BT_VER" ] || { rm -rf "$sdk/tmp"; mkdir -p "$sdk/tmp"; unzip -q "$sdk/dl/$BT_ZIP" -d "$sdk/tmp"; mv "$sdk/tmp"/*"$BT_VER"* "$sdk/build-tools/$BT_VER" 2>/dev/null || mv "$sdk/tmp"/* "$sdk/build-tools/$BT_VER"; }
  [ -f "$sdk/platforms/android-33/android.jar" ] || { rm -rf "$sdk/tmp"; mkdir -p "$sdk/tmp"; unzip -q "$sdk/dl/$PF_ZIP" -d "$sdk/tmp"; mkdir -p "$sdk/platforms/android-33"; cp -r "$sdk/tmp"/*/* "$sdk/platforms/android-33/" 2>/dev/null || cp -r "$sdk/tmp"/* "$sdk/platforms/android-33/"; }
  need aapt2 || die "aapt2 still missing under $sdk/build-tools/$BT_VER"
fi
JAR="$sdk/platforms/android-33/android.jar"
need javac || die "javac not found - install a JDK (openjdk-17-jdk-headless on Debian/Ubuntu)"

rm -rf "$B"; mkdir -p "$B/gen" "$B/classes" "$B/dex" "$D"
python3 "$A/prepare.py" "$B"

echo "resources"
aapt2 compile --dir "$A/res" -o "$B/res-app.zip"
aapt2 compile --dir "$B/res" -o "$B/res-gen.zip"
aapt2 link -o "$B/shell.apk" -I "$JAR" --manifest "$A/AndroidManifest.xml" \
  --java "$B/gen" -A "$B/pkg" "$B/res-app.zip" "$B/res-gen.zip" \
  --min-sdk-version "$MIN_SDK" --target-sdk-version "$TARGET_SDK" \
  --version-code "$VC" --version-name "$VER" \
  --auto-add-overlay

echo "java"
find "$B/gen" -name 'R.java' > "$B/sources.txt"
find "$A/src" -name '*.java' >> "$B/sources.txt"
# android.jar as the boot classpath, plus core-lambda-stubs.jar next to it: the platform jar carries stubs for
# java.lang.invoke.LambdaMetafactory with no method on them, so without the stubs jar this javac dies on the
# first lambda in the source. This is what the Android plugin does; a build-tools old enough not to ship it
# cannot compile this source either way, so say so instead of failing inside javac.
LAMBDA="$(dirname "$(dirname "$JAR")")/build-tools/$BT_VER/core-lambda-stubs.jar"
[ -f "$LAMBDA" ] || LAMBDA="$sdk/build-tools/$BT_VER/core-lambda-stubs.jar"
[ -f "$LAMBDA" ] || die "core-lambda-stubs.jar not found in build-tools/$BT_VER - the source uses lambdas, which need it"
javac -nowarn -source 1.8 -target 1.8 -Xlint:-options -encoding UTF-8 \
  -bootclasspath "$JAR:$LAMBDA" -classpath "$B/gen" -d "$B/classes" @"$B/sources.txt"

echo "dex"
d8 --lib "$JAR" --release --min-api "$MIN_SDK" --output "$B/dex" \
  $(find "$B/classes" -name '*.class')

echo "package"
# Fixed mtime on the one entry the Android tools do not normalise (aapt2 writes 1980-01-01 for everything it
# touches; d8's output keeps the wall clock). Without this, the same tree hashes differently on every build, and
# then a published sha256 - the thing you would check a downloaded APK against - is worth nothing.
find "$B/dex" -exec touch -d "@${SOURCE_DATE_EPOCH:-315532800}" {} +
cd "$B/dex" && zip -q -X -D -j "$B/shell.apk" classes.dex && cd "$B"
zipalign -f 4 "$B/shell.apk" "$B/aligned.apk"

# The signing identity, not a secret. Any self-signed key installs fine; what matters is that the *same* one is
# used next time, because Android refuses to upgrade a package signed by a different key and the user then has to
# uninstall, losing the charts in the app's storage. So the key lives wherever you point $DEBUG_KEYSTORE, and a
# clean tree without one generates a fresh key rather than shipping a committed one.
KS="${DEBUG_KEYSTORE:-$B/debug.keystore}"
if [ ! -f "$KS" ]; then
  need keytool || die "keytool not found - it ships with the JDK, so put \$JAVA_HOME/bin on PATH"
  mkdir -p "$(dirname "$KS")"
  keytool -genkeypair -v -keystore "$KS" -storepass android -keypass android \
    -alias geomancy -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Geomancy debug, OU=none, O=none, L=none, S=none, C=US" >/dev/null 2>&1
fi
apksigner sign --ks "$KS" --ks-pass pass:android --key-pass pass:android \
  --out "$D/$NAME.apk" "$B/aligned.apk"
apksigner verify --print-certs "$D/$NAME.apk" | sed 's/^/  /'

sha256sum "$D/$NAME.apk" | awk '{print $1}' > "$D/$NAME.apk.sha256"
echo "  sha256 $(cat "$D/$NAME.apk.sha256")"
echo "  publish this line with the file: it is what a downloaded APK gets checked against, and it is only"
echo "  worth publishing because the build above is byte-reproducible"

echo
aapt dump badging "$D/$NAME.apk" 2>/dev/null | grep -E '^(package|application-label|sdkVersion|targetSdkVersion|launchable-activity|uses-permission|application-icon-480)' | sed 's/^/  /'
python3 - "$D/$NAME.apk" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
have = set(z.namelist())
want = {"assets/www/mobile.html": "the app itself", "classes.dex": "the shell",
        "AndroidManifest.xml": "the manifest", "resources.arsc": "the resource table"}
for name, why in want.items():
    if name not in have:
        sys.exit(f"the APK is missing {name} ({why})")
# aapt2 tags density buckets with their minimum API (mipmap-xxxhdpi-v4), so match on shape, not on name
if not [n for n in have if n.startswith("res/mipmap-") and n.endswith("/ic_launcher.png")]:
    sys.exit("the APK carries no launcher icon")
print("  carries: " + ", ".join(sorted(n for n in have if n.startswith("assets/"))))
z.close()
import os
print("  size: {:,} bytes".format(os.path.getsize(sys.argv[1])))
PY
echo
echo "installed with:  adb install -r $D/$NAME.apk"
echo "or sent to a phone and opened from Files (allow 'install unknown apps' for that app once)."
