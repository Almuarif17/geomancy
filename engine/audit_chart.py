#!/usr/bin/env python3
"""Audit a chart that someone else produced (app, book, your own hand) against the generation rules.

Input = the 15 (or 16) house patterns as 1/2 lists, top row first. It tells you, per house,
which rule should have produced it, whether the drawing agrees, and which nephew convention a
given app is using. This is how you find out what a source actually does instead of assuming.
"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import deep_read as dr

RULES = {  # house -> (rule name, parents) ; daughters are the row-transposition
 "V":  ("Daughter = row 1 of I,II,III,IV", None), "VI": ("Daughter = row 2 of I..IV", None),
 "VII":("Daughter = row 3 of I..IV", None), "VIII":("Daughter = row 4 of I..IV", None),
 "IX": ("Nephew = I + II", (0,1)), "X": ("Nephew = III + IV", (2,3)),
 "XI": ("Nephew = V + VI  (classical) / I + II (repeat convention)", (4,5)),
 "XII":("Nephew = VII + VIII (classical) / III + IV (repeat convention)", (6,7)),
 "XIII":("Right witness = IX + X", (8,9)), "XIV":("Left witness = XI + XII", (10,11)),
 "XV": ("Judge = XIII + XIV", (12,13)), "XVI":("Sentence = XV + I", (14,0)),
}
NAMES = "I II III IV V VI VII VIII IX X XI XII XIII XIV XV XVI".split()


def audit(houses, convention="classical"):
    """houses: dict or list of patterns for the houses present (1-based order I..)."""
    H = [list(x) for x in houses]
    M = H[:4]
    D = [[M[j][i] for j in range(4)] for i in range(4)]
    if convention == "classical":
        N = [dr.add(M[0],M[1]), dr.add(M[2],M[3]), dr.add(D[0],D[1]), dr.add(D[2],D[3])]
    else:                                    # "repeat": both pairs from the Mothers
        N = [dr.add(M[0],M[1]), dr.add(M[2],M[3]), dr.add(M[0],M[1]), dr.add(M[2],M[3])]
    W = [dr.add(N[0],N[1]), dr.add(N[2],N[3])]
    J = [dr.add(W[0],W[1])]
    S = [dr.add(J[0], M[0])]
    expect = M + D + N + W + J + S
    rows, bad = [], 0
    for i, h in enumerate(NAMES):
        if i >= len(H): break
        got, exp = H[i], expect[i]
        ok = got == exp
        bad += not ok
        rows.append((h, dr.fig(got), dr.fig(exp), "ok" if ok else "DIFFERS", RULES.get(h, ("given (Mother)",""))[0]))
    return rows, bad, expect


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else str(
        pathlib.Path(__file__).resolve().parent.parent / "data/fixtures/chart2.json")
    data = json.loads(pathlib.Path(src).read_text())
    if isinstance(data, dict):
        seq = [data[k] for k in NAMES if k in data]
    else:
        seq = data
    for conv in ("classical", "repeat"):
        rows, bad, _ = audit(seq, conv)
        print(f"\n=== convention: {conv}  ({'matches everywhere' if bad==0 else str(bad)+' house(s) differ'})")
        for h, g, e, st, rule in rows:
            if st != "ok":
                print(f"   {h:4s} drawn {g:16s} vs computed {e:16s} [{rule}]")
