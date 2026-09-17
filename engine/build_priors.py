#!/usr/bin/env python3
"""Exact finite population of geomancy: every one of the 16^4 = 65,536 possible casts,
enumerated. Produces kb/priors.json = P(figure | house) and its surprisal, so a reading can say
how *informative* a placement is instead of treating every figure as equally meaningful.

Why this matters: because the Daughters/Nephews/Witnesses/Judge are derived, the 16 figures are NOT
equally likely in every house. Only 8 figures can ever be Judge, some houses can never hold certain
figures, and the same "favourable" figure is ordinary in one house and rare in another. Rare = news.
"""
import json, math, pathlib, sys, itertools
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import deep_read as dr

NAMES = list(dr.FIG.keys())
IDX = {tuple(dr.pat(n)): n for n in NAMES}
H = 16
counts = [[0]*len(NAMES) for _ in range(H)]
judge_counts = {}
name_i = {n: k for k, n in enumerate(NAMES)}
add = dr.add
for combo in itertools.product(NAMES, repeat=4):
    M = [dr.pat(m) for m in combo]
    D = [[M[j][i] for j in range(4)] for i in range(4)]
    N = [add(M[0], M[1]), add(M[2], M[3]), add(D[0], D[1]), add(D[2], D[3])]
    W = [add(N[0], N[1]), add(N[2], N[3])]
    J = add(W[0], W[1]); S = add(J, M[0])
    seq = M + D + N + W + [J, S]
    for h, p in enumerate(seq):
        counts[h][name_i[IDX[tuple(p)]]] += 1
    judge_counts[IDX[tuple(J)]] = judge_counts.get(IDX[tuple(J)], 0) + 1
TOT = 65536
out = {"total_casts": TOT,
       "per_house": {dr.ROMAN[h]: {NAMES[i]: {"n": counts[h][i],
                                              "p": round(counts[h][i]/TOT, 6),
                                              "surprisal_bits": (round(-math.log2(counts[h][i]/TOT), 3)
                                                                 if counts[h][i] else float("inf"))}
                                   for i in range(len(NAMES)) if counts[h][i] > 0}
                     for h in range(H)},
       "possible_judges": {k: v for k, v in sorted(judge_counts.items(), key=lambda kv: -kv[1])}}
pathlib.Path("kb/priors.json").write_text(json.dumps(out, indent=1))
print("possible judges:", len(out["possible_judges"]), "->", out["possible_judges"])
print("houses with <16 attainable figures:",
      {dr.ROMAN[h]: 16-len(out["per_house"][dr.ROMAN[h]]) for h in range(H) if 16-len(out["per_house"][dr.ROMAN[h]])>0})
print("Judge surprisal uniform?", len({round(v/TOT,6) for v in out["possible_judges"].values()})==1)
