#!/usr/bin/env python3
"""Noise-tolerant passage miner for OCR'd early-print corpus.

Old scans never OCR clean, so exact grep fails. We canonicalise BOTH the corpus and the
search pattern into a "visual fingerprint" (letters OCR confuses collapse together), then
fuzzy-match. That lets us find e.g. 'Cauda Draconis ... first house ... new casting' even when
the text reads 'cauda draconu befotbefirttboufe'.
"""
import re, pathlib, difflib, sys, unicodedata

TRANS = str.maketrans({"f":"s","v":"u","j":"i","y":"i","w":"vv","q":"g","0":"o","1":"i","|":"i",
                       "{":"o","}":"o","[":"i","]":"l","€":"e","©":"o","î":"i","ï":"i","ö":"o",
                       "ä":"a","é":"e","è":"e","á":"a","ñ":"n","ù":"u","û":"u","â":"a","ô":"o",
                       "ß":"b","þ":"th","ð":"d","æ":"ae","œ":"oe","–":" ","—":" "})
def canon(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.translate(TRANS)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def chunks(text, size=260, step=120):
    flat = re.sub(r"\s+"," ", text)
    for i in range(0, max(1,len(flat)-size), step):
        yield flat[i:i+size]

def mine(patterns, root, min_ratio=0.62, max_hits=8):
    """patterns: list of keyword-phrasings; returns best passages per file."""
    pc = [canon(p) for p in patterns]
    results = {}
    for f in sorted(pathlib.Path(root).glob("*.txt")):
        text = f.read_text(errors="replace")
        scored = []
        for ch in chunks(text):
            cc = canon(ch)
            if len(cc) < 40: continue
            # quick reject
            if not any(w in cc for w in pc[0].split()[:2]): continue
            toks = re.findall(r"\w{3,}", cc)
            joined = " ".join(toks)
            r = max(difflib.SequenceMatcher(None, joined, p).ratio() for p in pc)
            # also count keyword presence
            hits = sum(1 for kw in pc[0].split() if kw in cc)
            score = 0.7*r + 0.3*(hits/max(1,len(pc[0].split())))
            if score >= min_ratio: scored.append((round(score,3), ch))
        scored.sort(reverse=True)
        if scored: results[f.name] = scored[:max_hits]
    return results

if __name__ == "__main__":
    QUERIES = {
      "cauda_reject_recaster": ["cauda draconis in the first house the judgment must be broken and a new one made an hour after"],
      "reconciler_superjudge":  ["the reconciler or super judge is made of the judge and the first mother"],
      "way_of_points":          ["the way of the points runneth from the judge to the witness to the niece to the mother"],
      "judge_even_only":        ["only eight figures can be judge because the judge must be even in points"],
      "thief_direction":        ["to know the thief look what figure is in the seventh house and it sheweth the quarter and the condition of the person"],
      "servant_runaway":        ["if the servant hath stolen and fled the figure of the sixth house sheweth whether he shall be taken"],
      "pregnancy_sex":          ["whether the wife shall be delivered of a man child or a woman child"],
      "sickness_death_day":     ["the sickness shall turn to death if the figure of the sixth pass into the eighth"],
      "buyer_seller_price":     ["of buying and selling and the price thereof"],
      "messenger_arrival_hour": ["when the messenger shall come cast a figure and take one figure from the fourth and the fifth"],
      "travellers_return":      ["whether they that travel shall return the ninth house and the lord thereof"],
      "loose_bonds_prisoner":   ["whether the prisoner shall be delivered"],
      "war_victory":            ["of war and the victory which part shall have the advantage"],
      "hidden_treasure":        ["of treasure hid in the earth and whether it shall be found"],
      "evil_eye_enemy":         ["of enemies seen and unseen the twelfth house"],
    }
    root = sys.argv[1] if len(sys.argv)>1 else "corpus/raw"
    for name, pat in QUERIES.items():
        res = mine(pat, root, min_ratio=0.55, max_hits=2)
        print("\n" + "="*100); print("QUERY:", name, "|", pat[0][:80])
        if not res: print("   (no confident hit)"); continue
        for fn, hits in list(res.items())[:3]:
            for sc, txt in hits[:1]:
                print(f"   [{sc}] {fn}\n        {txt[:300]}")
