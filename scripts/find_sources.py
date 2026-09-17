"""Probe Internet Archive for the rare primary texts, report which have a text layer."""
import json, urllib.parse, requests

def search(q, rows=6):
    url = ("https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) +
           "&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=year&fl%5B%5D=downloads"
           f"&sort%5B%5D=downloads+desc&rows={rows}&page=1&output=json")
    r = requests.get(url, timeout=40)
    r.raise_for_status()
    return r.json()["response"]["docs"]

QUERIES = {
 "heydon_theomagia":  "title:(theomagia)",
 "cattan_geomancie":  "geomancie AND year:[1500 TO 1700]",
 "agrippa_ocp":       "title:(three books of occult philosophy)",
 "english_geomancy":  "title:(geomancy) AND year:[1480 TO 1750]",
 "arabic_raml":       "raml AND mediatype:texts",
}
out = {}
for k, q in QUERIES.items():
    try:
        out[k] = search(q)
    except Exception as e:
        out[k] = f"ERR {e}"
print(json.dumps(out, indent=1)[:4000])
