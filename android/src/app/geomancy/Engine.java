package app.geomancy;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.util.HashMap;
import java.util.Map;

/**
 * The only thing in this APK that touches a network.
 *
 * The page is loaded from a made-up origin, {@code https://geomancy.local}, so every relative URL it builds -
 * {@code /api/chart16}, {@code icon-192.png}, everything - arrives here first. Paths that name a file go to
 * the APK's own assets; paths under {@code /api/} are forwarded to the engine address the user chose and
 * re-tagged as if the answer had come from the same origin.
 *
 * That indirection is the whole design, and it buys three things at once: the page hard-codes no host (the
 * same bytes run in a browser on a laptop and inside this shell), there is no CORS to configure because the
 * page and its data share an origin, and no website the user happens to open can be tricked into talking to
 * their local engine, because nothing but this class can reach one.
 */
final class Engine {

    /** Where the answers come from. Saved on the device; the connection dialog is what sets it. */
    static final String PREF_ENGINE = "engine_base";
    static final String PREF_OK = "engine_confirmed";
    static final String DEFAULT_ENGINE = "http://127.0.0.1:8044";

    static final class Reply {
        final int status;
        final String reason;
        final String mime;
        final byte[] body;
        final Map<String, String> headers = new HashMap<>();

        Reply(int status, String reason, String mime, byte[] body) {
            this.status = status;
            this.reason = reason;
            this.mime = mime;
            this.body = body == null ? new byte[0] : body;
        }
    }

    private Engine() {
    }

    /**
     * Forward one /api/ call. Never throws: an unreachable engine is the normal case for a phone that just
     * woke up somewhere else, so it comes back as a JSON 503 the page already knows how to show.
     */
    static Reply call(String base, String pathAndQuery, String method, byte[] requestBody) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(join(base, pathAndQuery));
            String host = url.getHost();
            if (!"http".equals(url.getProtocol()) && !"https".equals(url.getProtocol())) {
                return json(400, "the engine address must start with http:// or https://");
            }
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(4000);
            conn.setReadTimeout(30000);
            conn.setInstanceFollowRedirects(false);       // a redirect would move the request to a host nobody approved
            conn.setRequestMethod("POST".equals(method) ? "POST" : "GET");
            conn.setRequestProperty("Accept", "application/json, text/plain, */*");
            if (requestBody != null && requestBody.length > 0) {
                conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type", "application/json");
                OutputStream out = conn.getOutputStream();
                out.write(requestBody);
                out.close();
            }
            int code = conn.getResponseCode();
            if (code >= 300 && code < 400) {
                return json(502, "the engine answered with a redirect, which this app will not follow");
            }
            InputStream src = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
            byte[] body = src == null ? new byte[0] : read(src);
            String mime = guessType(conn.getContentType(), pathAndQuery);
            Reply r = new Reply(code, conn.getResponseMessage(), mime, body);
            // the page reads these, so carry them across; nothing else about the upstream response is forwarded
            for (String h : new String[]{"Cache-Control"}) {
                String v = conn.getHeaderField(h);
                if (v != null) {
                    r.headers.put(h, v);
                }
            }
            return r;
        } catch (IOException e) {
            String m = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
            return json(503, "no engine at " + base + " (" + firstLine(m) + "). Start it with "
                    + "`python3 app/server.py`, or change the address in the connection dialog. "
                    + "Saved charts stay readable.");
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    /** A health probe on a background thread: decides whether to open with the connection dialog. */
    static boolean reachable(String base) {
        Reply r = call(base, "/api/health", "GET", null);
        return r.status == 200;
    }

    /**
     * Whether an address is one the user can point at without a second thought. Used only to decide whether to
     * ask - a public host is allowed, it simply has to be confirmed, because on a public host the question and
     * the tap counts leave this device and land on somebody else's server.
     */
    static boolean isPrivate(String base) {
        try {
            String host = new URL(base).getHost();
            if (host == null) {
                return false;
            }
            host = host.toLowerCase();
            if (host.equals("localhost") || host.endsWith(".local") || host.startsWith("127.")
                    || host.startsWith("10.") || host.startsWith("192.168.") || host.equals("::1")
                    || host.equals("10.0.2.2")) {
                return true;
            }
            if (host.startsWith("172.")) {
                int second = Integer.parseInt(host.split("\\.")[1]);
                return second >= 16 && second <= 31;
            }
            // a hostname on the LAN that resolves to a private address counts as private
            if (host.matches("[0-9a-fA-F:.\\-]+")) {
                return false;
            }
            InetAddress[] all = InetAddress.getAllByName(host);
            for (InetAddress a : all) {
                if (!a.isLoopbackAddress() && !a.isSiteLocalAddress()) {
                    return false;
                }
            }
            return all.length > 0;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * Reduce whatever the user typed to scheme://host:port, or refuse it.
     *
     * Rebuilding from the parsed parts rather than trimming the string is the point: it drops a path, a query or
     * a fragment that would otherwise turn this class into a general proxy, and it rejects a userinfo component
     * (`http://user:pass@host`) that would be a credential stored on the device for no reason. Typing
     * "192.168.1.40:8044" is the common case and gets the http:// it means.
     */
    static String sanitise(String raw) {
        String s = raw == null ? "" : raw.trim();
        if (s.isEmpty()) {
            return DEFAULT_ENGINE;
        }
        if (!s.contains("://")) {
            s = "http://" + s;
        }
        try {
            URL u = new URL(s);
            String proto = u.getProtocol() == null ? "" : u.getProtocol().toLowerCase();
            if (!proto.equals("http") && !proto.equals("https")) {
                return null;
            }
            if (u.getUserInfo() != null || u.getHost() == null || u.getHost().isEmpty()) {
                return null;
            }
            StringBuilder out = new StringBuilder(proto).append("://").append(u.getHost());
            if (u.getPort() > 0) {
                out.append(':').append(u.getPort());
            }
            return out.toString();
        } catch (Exception e) {
            return null;
        }
    }

    static String join(String base, String pathAndQuery) {
        String b = base == null || base.isEmpty() ? DEFAULT_ENGINE : base;
        return b.endsWith("/") ? b.substring(0, b.length() - 1) + pathAndQuery : b + pathAndQuery;
    }

    private static Reply json(int status, String message) {
        try {
            JSONObject o = new JSONObject();
            o.put("error", message);
            o.put("offline", status == 503);
            return new Reply(status, status == 503 ? "Service Unavailable" : "Error", "application/json; charset=utf-8",
                    o.toString(1).getBytes("UTF-8"));
        } catch (Exception e) {
            return new Reply(status, "Error", "application/json", "{\"error\":\"unreachable\"}".getBytes());
        }
    }

    private static String guessType(String upstream, String path) {
        if (upstream != null && !upstream.isEmpty()) {
            return upstream;
        }
        if (path.endsWith(".json") || path.contains("/api/")) {
            return "application/json; charset=utf-8";
        }
        return "text/plain; charset=utf-8";
    }

    /**
     * The media type for a file inside the package, with NO charset parameter on it.
     *
     * This matters more than it looks. WebResourceResponse takes a type and an encoding and joins them with its
     * own "charset=", so a type that already carries one is sent as "text/html; charset=utf-8; charset=UTF-8",
     * Chromium finds no parseable document type, and - with X-Content-Type-Options: nosniff in the way - it
     * refuses to render and shows the page's source as text. That is precisely what a first install on a TECNO
     * displayed: sixteen hills of sand, as HTML.
     */
    static String assetType(String path) {
        if (path.endsWith(".html")) {
            return "text/html";
        }
        if (path.endsWith(".js")) {
            return "application/javascript";
        }
        if (path.endsWith(".css")) {
            return "text/css";
        }
        if (path.endsWith(".png")) {
            return "image/png";
        }
        if (path.endsWith(".json") || path.endsWith(".webmanifest")) {
            return "application/json";
        }
        if (path.endsWith(".svg")) {
            return "image/svg+xml";
        }
        return "application/octet-stream";
    }

    /** The type alone: "text/html; charset=utf-8" and "text/html" must not reach the WebView as two headers. */
    static String bareType(String mime) {
        if (mime == null) {
            return "application/octet-stream";
        }
        int i = mime.indexOf(';');
        String t = (i < 0 ? mime : mime.substring(0, i)).trim();
        return t.isEmpty() ? "application/octet-stream" : t;
    }

    /** The charset the other half of that header was carrying, or null for a type that has no business having one. */
    static String charsetOf(String mime) {
        if (mime == null) {
            return null;
        }
        int i = mime.indexOf("charset=");
        if (i < 0) {
            return bareType(mime).startsWith("text/") || bareType(mime).contains("json")
                    || bareType(mime).endsWith("javascript") || bareType(mime).contains("svg") ? "utf-8" : null;
        }
        String cs = mime.substring(i + "charset=".length()).trim();
        int j = cs.indexOf(';');
        if (j > 0) {
            cs = cs.substring(0, j);
        }
        cs = cs.replace("\"", "").replace("'", "").trim();
        return cs.isEmpty() ? null : cs.toLowerCase();
    }

    private static byte[] read(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[16384];
        int n;
        while ((n = in.read(buf)) > 0) {
            out.write(buf, 0, n);
        }
        in.close();
        return out.toByteArray();
    }

    private static String firstLine(String s) {
        int i = s.indexOf('\n');
        return (i > 0 ? s.substring(0, i) : s).trim();
    }
}
