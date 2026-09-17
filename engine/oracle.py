#!/usr/bin/env python3
"""A second, independent implementation of the geomantic rules - the engine's opponent.

Nothing here imports engine/deep_read.py. The figure table is read from `kb/figures.yaml` (data,
with its citations), and every procedure is re-coded from the sources in the most literal way:
build Mothers -> Daughters -> Nephews -> Witnesses -> Judge -> Sentence; trace the head row;
count single dots; test perfection by figure identity. `evaluate.py` runs this against the engine
over all 65,536 casts, so agreement is evidence about the code, not a restatement of it.

Rule sources (as implemented here):
  chart:   Calatarama f.22v parentage; Britannica; al-Zanati via van Binsbergen (1996)
  sentence:XV + Mother I - "from the first and the fifteenth" (al-Zanati)
  via puncti: head-row tracing with branching (Finan thesis p.146, f.12v-13; Greer, Caduceus 2.2)
  projection: single dots in I..XII, mod 12, 0 -> XII (Serena Powers; Calatarama f.12)
  pars fortunae: total points in I..XII, mod 12 (Serena Powers; Cattan)
  motus:  a figure repeating across the chart is judged at its second coming (Cattan)
  perfection: occupation = same figure in I and the quesited house (Alfagini, via Calatarama)
"""
from __future__ import annotations

import itertools, pathlib

import yaml

KB = pathlib.Path(__file__).resolve().parents[1] / "kb"


def figure_table():
    d = yaml.safe_load((KB / "figures.yaml").read_text())
    out = {}
    for name, v in d["figures"].items():
        rows = v.get("pattern") or v.get("rows")
        if rows:
            out[name] = tuple(int(x) for x in rows)
    return out


FIG, BYP = (lambda t: (t, {v: k for k, v in t.items()}))(figure_table())
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI"]


def add(a, b):
    """Row-wise geomantic addition: even number of pips -> 2, odd -> 1."""
    return tuple(2 if (a[i] + b[i]) % 2 == 0 else 1 for i in range(4))


def cast(mothers):
    """Full shield. Returns the 16 patterns, house by house."""
    M = [FIG[m] for m in mothers]
    D = tuple(tuple(M[k][r] for k in range(4)) for r in range(4))       # V..VIII = rows 1..4
    N = (add(M[0], M[1]), add(M[2], M[3]), add(D[0], D[1]), add(D[2], D[3]))   # IX..XII
    W = (add(N[0], N[1]), add(N[2], N[3]))                                # XIII, XIV
    J = add(W[0], W[1])                                                   # XV
    S = add(J, M[0])                                                      # XVI = Judge + first Mother
    return list(M) + list(D) + list(N) + list(W) + [J, S]


def name(pat):
    return BYP.get(tuple(pat), "??")


def via_puncti(h):
    """Same rule, deliberately different code: explicit stack, DFS, first-parent-first."""
    par = {14: [12, 13], 12: [8, 9], 13: [10, 11], 8: [0, 1], 9: [2, 3], 10: [4, 5], 11: [6, 7]}
    ends, branches, stack = [], [], [(14, [14])]
    while stack:
        cur, path = stack.pop(0)
        ps = par.get(cur)
        if ps is None:
            ends.append((cur + 1, name(h[cur]), "root")); continue
        val = h[cur][0]
        hits = [q for q in ps if h[q][0] == val]
        if not hits:
            ends.append((cur + 1, name(h[cur]), "died")); continue
        if len(hits) > 1:
            for q in hits[1:]:
                nm = name(h[q])
                if nm not in branches:
                    branches.append(nm)
        for q in reversed(hits):
            stack.insert(0, (q, path + [q]))
    seen, uniq = set(), []
    for e in ends:
        if e not in seen:
            seen.add(e); uniq.append(e)
    node, primary = 14, []
    while True:
        primary.append(node)
        up = par.get(node)
        if not up:
            break
        hit = [q for q in up if h[q][0] == h[node][0]]
        if not hit:
            break
        node = hit[0]
    return primary, branches, uniq


def projection(h):
    """Count SINGLE dots in the first twelve houses; remainder mod 12 names the house."""
    s = sum(1 for i in range(12) for v in h[i] if v == 1)
    return s, (s % 12 or 12)


def part_of_fortune(h):
    t = sum(sum(h[i]) for i in range(12))
    return t, (t % 12 or 12)


def motus(h):
    """Every figure that appears more than once, with its house numbers (1-based)."""
    seen = {}
    for i, p in enumerate(h):
        seen.setdefault(name(p), []).append(i + 1)
    return {f: hs for f, hs in seen.items() if len(hs) > 1}


def perfection_mode(h, qhouse):
    """Occupation: the quesited figure sits in house I too."""
    if qhouse == 1:
        return "self-query"
    if h[0] == h[qhouse - 1]:
        return "occupation"
    return "none"


def all_casts():
    names = list(FIG)
    for combo in itertools.product(names, repeat=4):
        yield combo, cast(combo)
