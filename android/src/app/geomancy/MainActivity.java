package app.geomancy;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.provider.MediaStore;
import android.util.Base64;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.Toast;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.Charset;

/**
 * The window: a WebView over the files in {@code assets/www}, which are the same bytes the browser is served.
 *
 * The page is loaded from the made-up origin {@code https://geomancy.local} so that (a) relative URLs like
 * {@code /api/prove} work untouched, (b) the page never contains a host name, and (c) the WebView treats it as a
 * secure context, which is what clipboard write and {@code navigator.share}-style behaviour need. Nothing is
 * actually fetched from {@code geomancy.local}: the interceptor answers with APK assets, and the JS bridge hands
 * API calls to {@link Engine}.
 *
 * The bridge exists because a WebView cannot do three things a phone can: vibrate for real, keep the screen
 * awake while you tap out sixteen rows, and put a PNG into the share sheet. Those three are exposed and nothing
 * else is.
 */
public class MainActivity extends Activity {

    private static final String HOST = "geomancy.local";
    private static final String START = "https://" + HOST + "/mobile.html";
    private static final String ASSET_ROOT = "www/";
    private static final String ASSET_FILE = "file:///android_asset/www/mobile.html";

    private WebView web;
    private SharedPreferences prefs;
    private volatile String documentMime = "(no document served yet)";
    private int bootTries = 0;
    private volatile boolean fileMode = false;
    private String sharedText = null;
    private volatile boolean dialogShowing = false;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(android.os.Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("geomancy", Context.MODE_PRIVATE);
        try {
            Intent in = getIntent();
            if (in != null && Intent.ACTION_SEND.equals(in.getAction())) {
                sharedText = in.getStringExtra(Intent.EXTRA_TEXT);
            }
        } catch (Exception ignore) {
            sharedText = null;                      // a shared text we cannot read is not a reason not to open
        }

        web = new WebView(this);
        WebSettings st = web.getSettings();
        st.setJavaScriptEnabled(true);
        st.setDomStorageEnabled(true);               // history and settings live in localStorage; without this the app forgets
        st.setAllowFileAccess(false);
        st.setAllowContentAccess(false);
        st.setMediaPlaybackRequiresUserGesture(false);
        st.setTextZoom(100);
        st.setSupportZoom(false);
        st.setBuiltInZoomControls(false);
        st.setDisplayZoomControls(false);
        st.setGeolocationEnabled(false);
        web.setBackgroundColor(Color.parseColor("#141110"));
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.setVerticalScrollBarEnabled(false);
        web.addJavascriptInterface(new Bridge(), "Android");
        web.setWebViewClient(new Client());
        web.setOnLongClickListener(v -> {
            openLinkOrIgnore();                      // a long press on the canvas is the share gesture; nothing else has one
            return true;
        });
        setContentView(web);

        web.loadUrl(START);
        probeEngine(false);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        if (intent != null && Intent.ACTION_SEND.equals(intent.getAction())) {
            sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
            web.loadUrl(START);
        }
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    // ---------------------------------------------------------------- the interceptor

    private final class Client extends WebViewClient {

        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            Uri u = request.getUrl();
            String path = u.getPath() == null ? "/" : u.getPath();
            if (!HOST.equals(u.getHost())) {
                // this app loads the files in the APK and whatever the engine answers, and nothing else
                return reply(403, "application/json; charset=utf-8",
                        "{\"error\":\"this app loads no external resources\"}".getBytes());
            }
            if (path.startsWith("/api/")) {
                // only GETs can be answered here: the WebView gives a client no access to a request body,
                // so POSTs go over the bridge and this path exists for a page loaded outside it
                Engine.Reply r = Engine.call(engineBase(), pathAndQuery(u), request.getMethod(), null);
                return reply(r.status, r.mime, r.body, true);
            }
            return asset(path);
        }

        @Override
        public void onPageFinished(WebView view, String url) {
            checkBooted(view);
            if (sharedText != null) {
                String t = sharedText.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ");
                view.evaluateJavascript("window.__sharedText='" + t + "';", null);
                sharedText = null;
            }
        }

        /**
         * Did the page actually run? A WebView handed its own document as text, or an asset list with a file
         * missing, produces a screen of markup and no error anywhere - the hardest kind of bug to report, because
         * the app looks broken and the log says nothing. So the shell asks the document whether its own app is in
         * it, and takes three steps: reload, then load the same file out of the package directly, then say on the
         * screen what it served and how.
         *
         * The middle step matters more than a retry. Everything about the first two steps is ours - the made-up
         * origin and the interceptor in front of it - and if one of them is the problem on somebody's build of
         * Chromium, the page still has to work. It does, from file://, because the API calls do not go through the
         * origin at all: they go through the bridge, which does not care where the page was loaded from. What that
         * costs is file access on this one window, which is why it is a fallback and not the normal path.
         */
        private void checkBooted(final WebView view) {
            final int attempt = bootTries++;
            view.evaluateJavascript("(function(){var t=document.getElementById('tabs');"
                    + "return (t && t.querySelectorAll('button').length >= 3 && typeof API === 'object')"
                    + " ? 'booted' : (document.body && document.body.childElementCount <= 1"
                    + " ? 'source-as-text' : 'not-booted');})()", value -> {
                if (value != null && value.contains("booted") && !value.contains("source-as-text")) {
                    bootTries = 0;
                    return;
                }
                if (attempt == 0) {
                    view.postDelayed(() -> view.reload(), 250);
                    return;
                }
                if (attempt == 1 && !fileMode) {
                    fileMode = true;
                    run(() -> {
                        Toast.makeText(MainActivity.this, "Rendering through the app's own origin failed, so this"
                                        + " window is reading the package's files instead. Nothing else changed.",
                                Toast.LENGTH_LONG).show();
                        view.getSettings().setAllowFileAccess(true);
                        view.loadUrl(ASSET_FILE);
                    });
                    return;
                }
                run(() -> new AlertDialog.Builder(MainActivity.this)
                        .setTitle("The page did not start")
                        .setMessage("served  " + START + "\n  as      " + documentMime
                                + "\n  engine  " + engineBase() + "\n  mode     "
                                + (fileMode ? "package files" : "virtual origin")
                                + "\n\nThe file arrived and did not run, so this is not the engine being"
                                + " unreachable. Those four lines are the bug report; reinstall from a build of the"
                                + " same version first.")
                        .setPositiveButton("Change engine address", (d2, w2) -> showConnectionDialog(engineBase()))
                        .setNeutralButton("Reload", (d2, w2) -> {
                            bootTries = 0;
                            view.loadUrl(fileMode ? ASSET_FILE : START);
                        })
                        .setNegativeButton("Close", null)
                        .show());
            });
        }

        @Override
        public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
            // a renderer killed by the OS comes back on its own reload; leaving it blank looks like a broken app
            setContentView(web = fresh());
            web.loadUrl(START);
            return true;
        }
    }

    private WebView fresh() {
        WebView w = new WebView(this);
        recreateSettings(w);
        return w;
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void recreateSettings(WebView w) {
        w.getSettings().setJavaScriptEnabled(true);
        w.getSettings().setDomStorageEnabled(true);
        w.setBackgroundColor(Color.parseColor("#141110"));
        w.getSettings().setGeolocationEnabled(false);
        w.addJavascriptInterface(new Bridge(), "Android");
        w.setWebViewClient(new Client());
        setContentView(w);
    }

    private static String pathAndQuery(Uri u) {
        String p = u.getPath() == null ? "/" : u.getPath();
        return u.getEncodedQuery() == null ? p : p + "?" + u.getEncodedQuery();
    }

    private WebResourceResponse asset(String path) {
        String rel = path.equals("/") ? "mobile.html" : path.substring(1);
        if (rel.contains("..") || rel.startsWith("/") || !rel.matches("[A-Za-z0-9._/-]+")) {
            return reply(400, "text/plain; charset=utf-8", "no such file".getBytes());
        }
        try (InputStream in = getAssets().open(ASSET_ROOT + rel)) {
            byte[] body = read(in);
            if (rel.endsWith(".html")) {
                documentMime = Engine.assetType(rel);      // what the next diagnostic line will quote back
            }
            return reply(200, Engine.assetType(rel), body, false);
        } catch (Exception e) {
            return reply(404, "text/html; charset=utf-8",
                    ("<html><body style=\"font:16px sans-serif;background:#141110;color:#f0e9dd;padding:2em\">"
                            + "This build is missing <code>" + rel + "</code>. Rebuild with "
                            + "<code>android/build.sh</code>.</body></html>").getBytes());
        }
    }

    /**
     * Build the response from a type and a charset that are kept apart until the last moment.
     *
     * WebResourceResponse appends its own "charset=" to whatever type it is given, so the type handed here is
     * always stripped first - see Engine.assetType for what happens otherwise. `api` marks the answers that came
     * from the engine: those get nosniff, because a JSON reply that a browser is willing to read as HTML is a
     * real hazard on a shared network. The files inside the package do not, and must not: nosniff on a document
     * whose type is even slightly off is what renders the app as a page of source code.
     */
    private static WebResourceResponse reply(int status, String mime, byte[] body, boolean api) {
        String type = Engine.bareType(mime);
        String charset = Engine.charsetOf(mime);
        WebResourceResponse r = new WebResourceResponse(type, charset, new ByteArrayInputStream(body));
        r.setStatusCodeAndReasonPhrase(status, status == 200 ? "OK" : (status == 503 ? "Service Unavailable" : "Error"));
        java.util.Map<String, String> h = new java.util.HashMap<>();
        h.put("Cache-Control", "no-cache");
        if (api) {
            h.put("X-Content-Type-Options", "nosniff");
        }
        r.setResponseHeaders(h);
        return r;
    }

    private static WebResourceResponse reply(int status, String mime, byte[] body) {
        return reply(status, mime, body, false);
    }

    // ---------------------------------------------------------------- the bridge

    private final class Bridge {

        @JavascriptInterface
        public String request(String method, String pathAndQuery, String body) {
            Engine.Reply r = Engine.call(engineBase(), pathAndQuery, method == null ? "GET" : method.toUpperCase(),
                    body == null || body.isEmpty() ? null : body.getBytes(Charset.forName("UTF-8")));
            // {status, body} as one string: the page decides whether the body is JSON or text, exactly as it
            // would for a fetch(), so nothing about the app's own error handling changes between the browser
            // and this shell
            return "{\"status\":" + r.status + ",\"type\":" + quote(
                    (r.mime == null ? "" : r.mime).getBytes(Charset.forName("UTF-8")))
                    + ",\"body\":" + quote(r.body) + "}";
        }

        @JavascriptInterface
        public String engine() {
            return engineBase();
        }

        @JavascriptInterface
        public boolean isShell() {
            return true;
        }

        @JavascriptInterface
        public void setEngine(String url) {
            String clean = Engine.sanitise(url);
            if (clean == null) {
                run(() -> Toast.makeText(MainActivity.this, "That is not an address I can use", Toast.LENGTH_LONG).show());
                return;
            }
            boolean priv = Engine.isPrivate(clean);
            prefs.edit().putString(Engine.PREF_ENGINE, clean).putBoolean(Engine.PREF_OK, priv).apply();
            run(() -> {
                if (!priv) {
                    Toast.makeText(MainActivity.this, "Public host: your question and your tap counts will leave this "
                            + "phone and go to that server", Toast.LENGTH_LONG).show();
                }
                web.loadUrl(START);
            });
        }

        @JavascriptInterface
        public void buzz(long ms) {
            try {
                Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                if (v != null && v.hasVibrator()) {
                    v.vibrate(VibrationEffect.createOneShot(Math.max(1, Math.min(ms, 400)),
                            VibrationEffect.DEFAULT_AMPLITUDE));
                }
            } catch (Exception ignore) {
                // a phone with no motor simply does not buzz; that is not an error worth showing
            }
        }

        @JavascriptInterface
        public void keepScreen(boolean on) {
            run(() -> {
                if (on) {
                    getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                } else {
                    getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                }
            });
        }

        /** The shield, as a PNG, offered to the share sheet - and saved where the user can find it again. */
        @JavascriptInterface
        public void sharePng(String base64, String name) {
            try {
                byte[] data = Base64.decode(base64, Base64.DEFAULT);
                Bitmap bmp = BitmapFactory.decodeByteArray(data, 0, data.length);
                Uri uri = null;
                if (Build.VERSION.SDK_INT >= 29) {
                    ContentValues cv = new ContentValues();
                    cv.put(MediaStore.Downloads.DISPLAY_NAME, name == null ? "geomancy.png" : name);
                    cv.put(MediaStore.Downloads.MIME_TYPE, "image/png");
                    cv.put(MediaStore.Downloads.RELATIVE_PATH, "Pictures/Geomancy");
                    uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv);
                    if (uri != null) {
                        try (java.io.OutputStream out = getContentResolver().openOutputStream(uri)) {
                            out.write(data);
                        }
                    }
                } else {
                    File dir = new File(getExternalFilesDir(android.os.Environment.DIRECTORY_PICTURES), "Geomancy");
                    dir.mkdirs();
                    File f = new File(dir, name == null ? "geomancy.png" : name);
                    try (FileOutputStream out = new FileOutputStream(f)) {
                        out.write(data);
                    }
                    // insertImage returns the content URI as a string and is deprecated rather than removed;
                    // it is the only way to hand a pre-Q gallery image to the share sheet without a FileProvider
                    String got = MediaStore.Images.Media.insertImage(getContentResolver(), f.getAbsolutePath(),
                            "Geomantic shield", null);
                    uri = got == null ? null : Uri.parse(got);
                }
                final Intent share = new Intent(Intent.ACTION_SEND);
                share.setType("image/png");
                if (uri != null) {
                    share.putExtra(Intent.EXTRA_STREAM, uri);
                }
                share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                final Uri saved = uri;
                run(() -> {
                    if (saved == null) {
                        Toast.makeText(MainActivity.this, "Could not save the image", Toast.LENGTH_LONG).show();
                        return;
                    }
                    try {
                        startActivity(Intent.createChooser(share, "Share the shield"));
                    } catch (Exception e) {
                        Toast.makeText(MainActivity.this, "Saved in Pictures/Geomancy", Toast.LENGTH_SHORT).show();
                    }
                });
                if (bmp == null) {
                    return;                          // decoding already gave us the bytes we needed; the bitmap was a check
                }
                bmp.recycle();
            } catch (Exception e) {
                run(() -> Toast.makeText(MainActivity.this, "The image could not be written: " + e.getMessage(),
                        Toast.LENGTH_LONG).show());
            }
        }

        @JavascriptInterface
        public void askEngine() {
            probeEngine(true);
        }
    }

    /**
     * Wrap bytes as a JSON string, decoding them as UTF-8 first.
     *
     * The engine's answers carry Arabic names for the figures, and a byte-at-a-time escape would turn each of
     * those UTF-8 bytes into its own character - valid JSON, unreadable words. So: decode first, then escape, and
     * write everything above U+007E as an escaped six-character sequence, which is the only form that survives the
     * Java-to-JavaScript hop intact. (A comment cannot show that sequence literally: javac translates unicode
     * escapes before it reads comments, which is the first thing this file ever failed on.)
     */
    private static String quote(byte[] body) {
        String text;
        try {
            text = new String(body, Charset.forName("UTF-8"));
        } catch (Exception e) {
            text = new String(body);
        }
        StringBuilder sb = new StringBuilder(text.length() + 16).append('"');
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20 || c >= 0x7F) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        return sb.append('"').toString();
    }

    // ---------------------------------------------------------------- connection

    private String engineBase() {
        String saved = prefs.getString(Engine.PREF_ENGINE, null);
        String clean = Engine.sanitise(saved);
        return clean == null ? Engine.DEFAULT_ENGINE : clean;
    }

    /** Ask the engine if it is there; if it is not, let the user point the app at it. */
    private void probeEngine(boolean force) {
        final String base = engineBase();
        new Thread(() -> {
            boolean up = Engine.reachable(base);
            if (up || force) {
                run(() -> {
                    if (!up) {
                        showConnectionDialog(base);
                    }
                });
            }
        }).start();
    }

    private void showConnectionDialog(String current) {
        if (dialogShowing) {
            return;
        }
        dialogShowing = true;
        EditText input = new EditText(this);
        input.setText(current);
        input.setSingleLine(true);
        input.selectAll();
        AlertDialog d = new AlertDialog.Builder(this)
                .setTitle("Where is the engine?")
                .setMessage("The app computes nothing on its own: it asks a geomancy-library server. On this "
                        + "phone, run it in Termux with `python3 app/server.py` and use the address below. On a "
                        + "laptop on the same network, use that machine's address and port.\n\nYour tap counts and "
                        + "your question are the only things sent. Charts are kept on this device.")
                .setView(input)
                .setPositiveButton("Connect", (dialog, which) -> {
                    dialogShowing = false;
                    new Bridge().setEngine(input.getText().toString());
                })
                .setNeutralButton("This device", (dialog, which) -> {
                    dialogShowing = false;
                    new Bridge().setEngine(Engine.DEFAULT_ENGINE);
                })
                .setNegativeButton("Not now", (dialog, which) -> dialogShowing = false)
                .setOnCancelListener(dialog -> dialogShowing = false)
                .create();
        d.show();
    }

    private void openLinkOrIgnore() {
        // reserved: the long-press gesture is handled inside the page, which knows what was pressed
    }

    private void run(Runnable r) {
        runOnUiThread(r);
    }

    private static byte[] read(InputStream in) throws java.io.IOException {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        byte[] buf = new byte[16384];
        int n;
        while ((n = in.read(buf)) > 0) {
            out.write(buf, 0, n);
        }
        return out.toByteArray();
    }
}
