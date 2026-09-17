#!/usr/bin/env python3
"""Exact odds for the perfection machinery, over all 65,536 casts.

Modern books say "Conjunction means yes-with-work". None of them say how often each mode occurs -
without that you cannot tell whether a mode is news or noise. This enumerates the whole finite
population and writes kb/perfection_priors.json.
"""
import json, pathlib, itertools, collections, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import deep_read as dr

add, FIG = dr.add, dr.FIG
PATS = [FIG[n]["pattern"] for n in FIG]
ROMAN = dr.ROMAN

def classify(M, qh):
    D = [[M[j][i] for j in range(4)] for i in range(4)]
    N = [add(M[0], M[1]), add(M[2], M[3]), add(D[0], D[1]), add(D[2], D[3])]
    W = [add(N[0], N[1]), add(N[2], N[3])]
    H = M + D + N + W
    quer, ques = H[0], H[qh - 1]
    adj_q = {h for h in (qh - 2, qh) if 0 <= h < 12 and h not in (0, qh - 1)}
    adj_k = {h for h in (1, 11) if h != qh - 1}
    if quer == ques:
        return "occupation"
    if any(H[i] == quer for i in adj_q):
        return "conjunction(needs work)"
    if any(H[i] == ques for i in adj_k):
        return "conjunction(no effort)"
    for i in range(11):
        if {i, i + 1} & {0, qh - 1}:
            continue
        if (tuple(H[i]), tuple(H[i+1])) in {(tuple(quer), tuple(ques)), (tuple(ques), tuple(quer))}:
            return "mutation"
    for i in adj_k:
        for j in adj_q:
            if i != j and tuple(H[i]) == tuple(H[j]) and tuple(H[i]) not in (tuple(quer), tuple(ques)):
                return "translation"
    return "no relation"

QS = list(range(2, 13))
tab = {q: collections.Counter() for q in QS}
mothers = [list(p) for p in PATS]
for combo in itertools.product(range(16), repeat=4):
    M = [mothers[k] for k in combo]
    for q in QS:
        tab[q][classify(M, q)] += 1
TOT = 65536
out = {f"question_in_house_{ROMAN[q-1]}":
       {mode: {"n": n, "pct": round(100*n/TOT, 3)} for mode, n in tab[q].most_common()} for q in QS}
pathlib.Path("kb/perfection_priors.json").write_text(json.dumps(
    {"_meta": {"population": "all 16^4 = 65,536 casts", "engine": "deep_read.classify conventions: "
      "querent = house I, quesited = the question's house, adjacency = the two flanking houses",
      "use": "a mode only means something if it is rarer than its prior share"},
     "priors": out}, indent=1))
for q in QS:
    print(ROMAN[q-1].ljust(4), {m: round(100*n/TOT,1) for m, n in tab[q].most_common()})
