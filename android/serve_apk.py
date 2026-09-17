#!/usr/bin/env python3
"""Hand the built APK to a phone over the Wi-Fi, so `adb` is not a requirement for trying it.

    python3 android/serve_apk.py                  # prints a LAN URL and writes qr.svg next to it
    python3 android/serve_apk.py --port 9000      # if 8099 is taken
    python3 android/serve_apk.py --apk some/other.apk

Point a phone at the printed address, or scan the QR, and Android downloads a file whose sha256 the page also
prints - which is the whole reason this exists rather than "just send it on WhatsApp": a messenger recompresses
nothing but it does re-encode, rename and sometimes quarantine an .apk, and a download from a server you started
five seconds ago is at least a file you can check against the build.

Served read-only, from the directory holding the APK, and it stops when you stop it. If the app is being built on
the same laptop that runs the engine, that phone is already one network away from both.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent


def lan_addresses() -> list[str]:
    out = []
    try:
        host = socket.gethostbyname_ex(socket.gethostname())[2]
        out += [h for h in host if h and not h.startswith("127.")]
    except Exception:  # noqa: BLE001
        pass
    return out


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".apk": "application/vnd.android.package-archive",
                      ".html": "text/html; charset=utf-8",
                      ".svg": "image/svg+xml"}

    apk: pathlib.Path = HERE / "dist" / "D-Gem.apk"      # set by main(); a class attr so the handler can find it

    def end_headers(self) -> None:
        if self.path.lstrip("/").startswith(self.apk.name) and self.apk.exists():
            self.send_header("X-APK-SHA256", hashlib.sha256(self.apk.read_bytes()).hexdigest())
            self.send_header("Content-Length", str(self.apk.stat().st_size))
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        pass


def qr_svg(target: str, path: pathlib.Path) -> bool:
    try:
        import qrcode  # free, pip-installed, and only used to save a phone from typing a URL
    except Exception:  # noqa: BLE001
        return False
    from qrcode.image.svg import SvgPathImage

    img = qrcode.make(target, image_factory=SvgPathImage, box_size=10, border=2)
    path.write_bytes(img.to_string())
    return True


def page(public: str, apk: pathlib.Path) -> str:
    size, digest = apk.stat().st_size, hashlib.sha256(apk.read_bytes()).hexdigest()
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Geomancy - install the APK</title><style>
body{{background:#141110;color:#f0e9dd;font:16px/1.6 system-ui,sans-serif;margin:0;padding:28px 20px 60px}}
.wrap{{max-width:660px;margin:0 auto}}h1{{font-size:22px;letter-spacing:.02em;margin:0 0 4px}}
.mut{{color:#a99c90}}a.btn{{display:inline-block;background:#5d4a86;color:#fff;text-decoration:none;
padding:14px 22px;border-radius:12px;font-weight:600;margin:18px 0}}
code,pre{{background:#1e1a18;padding:2px 6px;border-radius:6px;font-size:13px}}ol{{padding-left:20px}}
li{{margin:7px 0}}.card{{border:1px solid #2c2622;border-radius:14px;padding:16px 18px;margin:18px 0}}
img{{display:block;max-width:210px;margin:0 auto}}small{{color:#a99c90}}
</style></head><body><div class="wrap">
<h1>Geomancy <span class="mut">- D-Gem.apk</span></h1>
<p class="mut">The phone app with an Android shell around it. {size:,} bytes, signed with a local debug key,
built from the same tree the tests run against.</p>
<a class="btn" href="/{apk.name}">Download D-Gem.apk</a>
<div class="card" style="text-align:center">
  <img src="qr.svg" alt="QR code for this page">
  <small>scan with the phone's camera</small>
</div>
<div class="card"><b>On the phone</b>
<ol>
<li>Open the file in Files, then allow <em>install unknown apps</em> for that app once.</li>
<li>Launch <em>Geomancy</em>. It will ask where the engine is, because it computes nothing itself.</li>
<li>Start the server somewhere reachable and type its address, e.g.
<code>python3 app/server.py --host 0.0.0.0 --port 8044</code> then <code>http://192.168.1.40:8044</code>.
On the phone itself, run it in Termux and use <code>http://127.0.0.1:8044</code>.</li>
</ol></div>
<div class="card"><b>With a cable instead</b><pre>adb install -r {apk.name}</pre>
<small>Or over Wi-Fi: <code>adb connect &lt;phone-ip&gt;:5555</code> once, with USB debugging on, then the same line.</small></div>
<div class="card"><small>sha256 <code>{digest}</code><br>
package <code>app.geomancy</code>, versionName 0.2.6 (code 206), minSdk 26, targetSdk 33.<br>
Reinstalling a newer build keeps working as long as it is signed with the same key - keep
<code>debug.keystore</code> from this folder.</small></div>
</div></body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8099")))
    ap.add_argument("--url", default="", help="public URL to encode in the QR code (default: the LAN address)")
    ap.add_argument("--apk", default=str(HERE / "dist" / "D-Gem.apk"))
    a = ap.parse_args()
    apk = pathlib.Path(a.apk).resolve()
    if not apk.exists():
        raise SystemExit(f"android/serve_apk.py: {apk} is not there - run python3 android/build.sh first")
    target = a.url or f"http://{(lan_addresses() or ['127.0.0.1'])[0]}:{a.port}"
    Handler.apk = apk
    out = apk.parent
    qr_svg(f"{target}/{apk.name}", out / "qr.svg")
    (out / "index.html").write_text(page(target, apk))
    os.chdir(out)                       # serve read-only, from the directory that holds the APK
    srv = ThreadingHTTPServer(("0.0.0.0", a.port), Handler)
    print(f"serving {out} on :{a.port}")
    print(f"  page   {target}/")
    print(f"  apk    {target}/{apk.name}")
    print(f"  sha256 {hashlib.sha256(apk.read_bytes()).hexdigest()}", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
