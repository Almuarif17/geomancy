#!/usr/bin/env python3
"""Legacy single-file shield generator (kept for teaching and diffing against the app).

The maintained engine is engine/deep_read.py; this file is the minimal version, useful when you want
to read the rule set off one screen.

From the 4 Mothers -> all 16 figures.

Notation: 4 rows per figure, read top->bottom; 1 = one dot (odd), 2 = a pair (even).
Addition: 1+1=2, 1+2=1, 2+2=2  (even sum -> pair, odd sum -> single).

Rules (validated against the reference castings in data/fixtures/):
  Mothers I..IV  : thrown figures, placed right -> left
  Daughters V..VIII : transpose of the Mothers -
                      V   = 1st row of I,II,III,IV
                      VI  = 2nd row of I,II,III,IV   (etc.)
  Nephews  IX..XII  : IX  = I   + II      XI  = V + VI
                      X   = III + IV      XII = VII + VIII
  Witnesses XIII,XIV: XIII(right) = IX + X     XIV(left) = XI + XII
  Judge XV          : XV = XIII + XIV   (must have an even number of points)
  16th (Sentence/Reconciler) XVI = XV + MOTHER I      <- not Judge + Left Witness
"""

FIGURES = {
    "Via":            [1,1,1,1],  "Populus":        [2,2,2,2],
    "Conjunctio":     [2,1,1,2],  "Carcer":         [1,2,2,1],
    "Puella":         [1,2,1,1],  "Puer":           [1,1,2,1],
    "Caput Draconis": [2,1,1,1],  "Cauda Draconis": [1,1,1,2],
    "Fortuna Major":  [2,2,1,1],  "Fortuna Minor":  [1,1,2,2],
    "Rubeus":         [2,1,2,2],  "Albus":          [2,2,1,2],
    "Acquisitio":     [2,1,2,1],  "Amissio":        [1,2,1,2],
    "Tristitia":      [2,2,2,1],  "Laetitia":       [1,2,2,2],
}
BY_NAME = {k: list(v) for k, v in FIGURES.items()}
_LOOKUP = {tuple(v): k for k, v in FIGURES.items()}
assert len(_LOOKUP) == 16, "the 16 patterns must be unique"


def add(a, b):
    return [1 if (x + y) % 2 else 2 for x, y in zip(a, b)]


def name(v):
    return _LOOKUP.get(tuple(v), "??")


def shield(mothers):
    M = [list(m) for m in mothers]
    D = [[M[j][i] for j in range(4)] for i in range(4)]          # transpose
    N = [add(M[0], M[1]), add(M[2], M[3]), add(D[0], D[1]), add(D[2], D[3])]
    W = [add(N[0], N[1]), add(N[2], N[3])]                        # XIII right, XIV left
    J = add(W[0], W[1])                                           # XV Judge
    S = add(J, M[0])                                              # XVI Sentence/Reconciler
    return M, D, N, W, J, S


def report(mothers):
    M, D, N, W, J, S = shield(mothers)
    houses = (list(zip("I II III IV".split(), M)) + list(zip("V VI VII VIII".split(), D))
              + list(zip("IX X XI XII".split(), N)) + list(zip(["XIII (R witness)", "XIV (L witness)"], W))
              + [("XV (JUDGE)", J), ("XVI (Sentence)", S)])
    out = []
    for h, f in houses:
        art = " ".join("●●" if r == 2 else " ● " for r in f)
        out.append(f"{h:<16} {art}   {'-'.join(map(str,f))}   {name(f)}")
    return "\n".join(out)


def check(mothers):
    """Independent integrity checks on a finished chart."""
    M, D, N, W, J, S = shield(mothers)
    ok = [
        ("Judge has even number of points", sum(J) % 2 == 0),
        ("N1+Judge == M2+Sentence == N2+LeftWitness",
         add(N[0], J) == add(M[1], S) == add(N[1], W[1])),
        ("16 figures contain at least one duplicate",
         len({tuple(x) for x in M + D + N + W + [J, S]}) < 16),
    ]
    return ok


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 5:
        mo = [BY_NAME[a] for a in sys.argv[1:5]]
    else:
        mo = [BY_NAME[n] for n in ["Carcer", "Amissio", "Caput Draconis", "Populus"]]
    print(report(mo))
    print()
    for label, passed in check(mo):
        print(("  PASS  " if passed else "  FAIL  ") + label)
