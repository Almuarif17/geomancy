#!/usr/bin/env python3
"""Deep-reading engine: everything that can be extracted from ONE geomantic cast.

Layer 1  chart        shield, house map, court (validated against the reference screenshots)
Layer 2  validity     is this cast fit to judge at all (medieval gates)
Layer 3  relations    motus, parentage, perfection, company, triplicities
Layer 4  trace        Via Puncti, Projection of the Points, Part of Fortune
Layer 5  specifics    who / where / when / of what humours / with what remedy
Layer 6  cross-read   the same cast in Arabic `ilm al-raml names (+ Ifa odu where attested)

Every finding carries a provenance tag so you can see which rule produced it.
"""
import argparse, itertools, json, pathlib, sys
import yaml

HERE = pathlib.Path(__file__).resolve().parent
KB = yaml.safe_load((HERE.parent / "kb" / "figures.yaml").read_text())
HS = yaml.safe_load((HERE.parent / "kb" / "houses.yaml").read_text())
_BANK = HERE.parent / "kb" / "cattan_motus_bank.json"
GRID = {}
_g = HERE.parent / "kb" / "calatarama_grid.json"
if _g.exists():
    _j = json.loads(_g.read_text())
    GRID = {h: v["entries"] for h, v in _j["grid"].items()}
    FOLIO = {h: v.get("folio", "") for h, v in _j["grid"].items()}
else:
    FOLIO = {}
MOTUS_BANK = {}
if _BANK.exists():
    for r in json.loads(_BANK.read_text())["records"]:
        MOTUS_BANK.setdefault((r["figure"], r["to_house"]), r["ocr_text"])
FIG = KB["figures"]
BY_PATTERN = {tuple(v["pattern"]): k for k, v in FIG.items()}
NAME_ALIAS = {"Fortuna Major": "Fortuna Major", "Fortuna Maior": "Fortuna Major",
              "Conjunctio": "Conjunctio", "Coniunctio": "Conjunctio", "Congregacion": "Conjunctio",
              "Carcer": "Carcer", "Carcel": "Carcer", "Carçel": "Carcer"}


def norm(n):
    n = n.strip()
    return NAME_ALIAS.get(n, n if n in FIG else n.title())


def add(a, b):
    return [1 if (x + y) % 2 else 2 for x, y in zip(a, b)]


def pat(name):
    return list(FIG[name]["pattern"])


# ---------------------------------------------------------------- layer 1: the chart
def build(mothers):
    M = [pat(m) for m in mothers]
    D = [[M[j][i] for j in range(4)] for i in range(4)]          # read DOWN the Mothers' rows
    N = [add(M[0], M[1]), add(M[2], M[3]), add(D[0], D[1]), add(D[2], D[3])]
    W = [add(N[0], N[1]), add(N[2], N[3])]
    J = add(W[0], W[1])
    S = add(J, M[0])                                             # Sentence = Judge + 1st Mother
    houses = M + D + N + W + [J, S]                              # index 0 => house I
    # parents[house_index] = the two houses that sum to it. Daughters (4-7) are NOT sums:
    # they are the Mothers' rows re-read as figures, so they get a transposition marker.
    return {"mothers": M, "daughters": D, "nephews": N, "witnesses": W, "judge": J,
            "sentence": S, "houses": houses,
            "transposed": {4: 0, 5: 1, 6: 2, 7: 3},              # house -> which Mothers' row
            "parents": {8: (0, 1), 9: (2, 3), 10: (4, 5), 11: (6, 7),      # Nieces
                        12: (8, 9), 13: (10, 11),                            # Witnesses
                        14: (12, 13), 15: (14, 0)}}                          # Judge, Sentence


def fig(p):
    return BY_PATTERN.get(tuple(p), "??")


# ---------------------------------------------------------------- layer 2: validity
def validity(c):
    out, H = [], c["houses"]
    f1, fj = fig(H[0]), fig(H[14])
    if f1 == "Cauda Draconis":
        out.append(("RECAST", "Cauda Draconis in house I: 'the figure should not be judged, but it "
                    "must be broken and an other made one houre after that'. [Cattan 1591/1608]"))
    if f1 == "Rubeus":
        out.append(("DISTRUST", "Rubeus as first mother / in house I: the querent is not telling the "
                    "truth about the matter. [stopping-figure rule]"))
    if fj == "Populus":
        out.append(("SUSPEND", "Populus as Judge: too much is moving at once; the verdict is crowd-voice, "
                    "not decision. [stopping-figure rule]"))
    if sum(H[14]) % 2:
        out.append(("ERROR", "Judge has an odd point total - impossible; the arithmetic is wrong."))
    else:
        out.append(("OK", f"Judge is even in points ({sum(H[14])}) - arithmetically admissible."))
    dup = len({tuple(p) for p in H})
    out.append(("OK", f"{dup} distinct figures among the 16 (a full cast must repeat at least one)."))
    return out


# ---------------------------------------------------------------- layer 3: relations
def motus(c):
    """Every figure that appears in more than one house 'passes'; judge it by its 2nd coming."""
    H = c["houses"]; res = {}
    for i, p in enumerate(H):
        f = fig(p)
        homes = [j + 1 for j, q in enumerate(H) if q == p]
        if len(homes) > 1:
            res[f] = homes
    return res


def parentage(c):
    """Read a generated figure through the two that made it (Calatarama f.22v):
    bad+bad = evil from two parts, good+good = good from two parts, else mixed."""
    H = c["houses"]
    out = []
    for h in range(5, 17):
        i = h - 1
        if i in c["transposed"]:
            row = c["transposed"][i] + 1
            out.append((h, None, [fig(H[j]) for j in range(4)],
                        f"Daughter: row {row} of the four Mothers, read as a figure of its own"))
            continue
        ps = c["parents"].get(i)
        if not ps:
            continue
        a, b = ps
        fa, fb = fig(H[a]), fig(H[b])
        qa, qb = FIG[fa].get("quality"), FIG[fb].get("quality")
        if qa == "bad" and qb == "bad":
            tone = "evil from two parts"
        elif qa == "good" and qb == "good":
            tone = "good from two parts"
        elif "communal" in (qa, qb) or None in (qa, qb):
            tone = "mixed with a communal parent: takes the side of the question"
        else:
            tone = "mixed: judge by the stronger parent for this question"
        note = " (both parents identical - the figure doubles its own tone)" if a != b and H[a] == H[b] else ""
        out.append((h, (a + 1, b + 1), (fa, fb), tone + note))
    return out


def perfection(c, topic):
    """Querent = house I; quesited = the house governing the topic. Returns the medieval
    relation type. Note the geometry: when the two houses are neighbours (topic house 2 or 12),
    'next to the quesited' includes the querent's own house, which makes Conjunction trivial -
    the sources do not discuss this, so we flag it instead of pretending the mode means something."""
    H = c["houses"]
    qh = HS["question_to_house"].get(topic, 7)
    if qh == 1:
        return {"mode": "self-query", "verdict": "the question is about the querent, so the houses coincide",
                "houses": (1, 1), "degenerate": True}
    quer, ques = H[0], H[qh - 1]
    # flanking houses, never the two significator houses themselves
    adj_q = {h for h in (qh - 2, qh) if 0 <= h < 12 and h not in (0, qh - 1)}
    adj_k = {h for h in (1, 11) if h != qh - 1}
    degenerate = (qh in (2, 12))
    res = {"houses": (1, qh), "degenerate": degenerate}
    if quer == ques:
        res["mode"] = "Occupation"
        res["verdict"] = ("YES - the thing already sits with you" if FIG[fig(quer)].get("quality") != "bad"
                          else "YES but it will not satisfy you (occupation by an ill figure)")
    elif any(H[i] == quer for i in adj_q):
        res["mode"] = "Conjunction"
        res["verdict"] = "YES with work - the querent's own figure has moved next to the quesited"
    elif any(H[i] == ques for i in adj_k):
        res["mode"] = "Conjunction"
        res["verdict"] = "YES with no effort - the quesited's figure has come to the querent"
    else:
        mut = None
        for i in range(11):
            if {i, i + 1} & {0, qh - 1}:
                continue
            if (fig(H[i]), fig(H[i + 1])) in {(fig(quer), fig(ques)), (fig(ques), fig(quer))}:
                mut = (i + 1, i + 2)
                break
        tra = None
        for i in adj_k:
            for j in adj_q:
                if i != j and H[i] == H[j] and fig(H[i]) not in (fig(quer), fig(ques)):
                    tra = fig(H[i])
                    break
            if tra:
                break
        if mut:
            res["mode"] = "Mutation"
            res["verdict"] = (f"YES by an unexpected route - the two figures stand together in houses "
                              f"{ROMAN[mut[0]-1]} and {ROMAN[mut[1]-1]}; those houses name the route")
        elif tra:
            good = FIG[tra].get("quality")
            res["mode"] = "Translation"
            res["verdict"] = (f"YES, but only through outside help (by {tra})"
                              + (" - and the helper is ill-dignified, so expect an unpleasant passage"
                                 if good == "bad" else ""))
        else:
            res["mode"] = "no relation"
            res["verdict"] = "NO - nothing binds the two houses; with unfavourable witnesses this is a plain refusal"
    if degenerate and res["mode"] != "Occupation":
        res["verdict"] += "  [caution: the question's house adjoins the querent's, so this mode is close to trivial - see priors]"
    return res


def triplicities(c, topic=None):
    H = c["houses"]
    gd = {"t1 self/health/outlook": [fig(H[0]), fig(H[1]), fig(H[8])],
          "t2 present events": [fig(H[2]), fig(H[3]), fig(H[9])],
          "t3 home/workplace": [fig(H[4]), fig(H[5]), fig(H[10])],
          "t4 friends/authority": [fig(H[6]), fig(H[7]), fig(H[11])]}
    cal = None
    if topic:
        qh = HS["question_to_house"].get(topic, 7)
        cal = HS["houses"][qh]
    return gd, cal


# ---------------------------------------------------------------- layer 4: trace
def via_puncti(c):
    """Head-line trace. From the Judge upward, follow the parent(s) sharing the Judge's head row.

    Returns (path, branch_names, endpoints):
      path        the primary line, [(house, figure), ...] from XV upward
      branch_names  every figure that was a *second* head at a split, in level order
      endpoints   every terminal the whole trace reaches: (house, figure, kind) with kind
                  "root" (a Mother/Daughter - the usual answer), "died" (no parent shared the
                  head: the matter is exactly as it appears) or "one_headed_root".
    Sources agree that a split must be followed, not discarded: "if both parents agree, the way
    is two-headed" (Finan thesis p.146 on the Libro de los juysios f.12v-13; the French
    voie du point bicéphale; Greer, Caduceus 2.2). An earlier build kept only the last split,
    which silently dropped the witness-level branch - engine/oracle.py catches that class of bug.
    """
    H = c["houses"]
    parents = {14: [12, 13], 12: [8, 9], 13: [10, 11], 8: [0, 1], 9: [2, 3], 10: [4, 5], 11: [6, 7]}
    branch_names, endpoints, seen = [], [], set()

    def walk(cur, path):
        path = path + [cur]
        ps = parents.get(cur)
        if not ps:
            endpoints.append((cur + 1, fig(H[cur]), "root"))
            return
        val = H[cur][0]
        nxt = [q for q in ps if H[q][0] == val]
        if not nxt:
            endpoints.append((cur + 1, fig(H[cur]), "died"))
            return
        if len(nxt) > 1:                      # two-headed: follow each branch, record the extra
            for q in nxt[1:]:
                nm = fig(H[q])
                if nm not in branch_names:
                    branch_names.append(nm)
            for q in nxt:
                walk(q, path)
            return
        walk(nxt[0], path)

    walk(14, [])
    uniq = []
    for e in endpoints:
        if e not in seen:
            seen.add(e); uniq.append(e)
    primary = []
    for cur, ps in [(14, parents.get(14))]:
        node, path = 14, []
        while True:
            path.append((node + 1, fig(H[node])))
            up = parents.get(node)
            if not up:
                break
            val = H[node][0]
            hits = [q for q in up if H[q][0] == val]
            if not hits:
                break
            node = hits[0]
        primary = path
    return primary, branch_names, uniq


def projection(c):
    """Count single dots in the 12 houses; mod 12 -> the hidden-factor house."""
    H = c["houses"]
    singles = sum(1 for p in H[:12] for v in p if v == 1)
    rem = singles % 12 or 12
    allpts = sum(sum(p) for p in H[:12])
    rem2 = allpts % 12 or 12
    return singles, rem, fig(H[rem - 1]), allpts, rem2, fig(H[rem2 - 1])


# ---------------------------------------------------------------- layer 5: specifics
def humours(c, topic=None):
    H = c["houses"]
    idx = list(range(12)) if topic is None else [0, HS["question_to_house"].get(topic, 7) - 1, 12, 13, 14]
    tally = {}
    for i in idx:
        f = fig(H[i]); nature = FIG[f].get("nature") or ""
        for q in ["hot", "cold", "wet", "dry", "moist"]:
            if q in nature:
                tally[q] = tally.get(q, 0) + 1
    if tally.get("wet") and not tally.get("moist"):
        tally["moist"] = tally["wet"]
    excess = sorted(tally.items(), key=lambda kv: -kv[1])
    cure = {"hot": "what cools (water, rest, delay, Albus-type counsel)",
            "cold": "what warms (motion, heat, a forward move, Puer-type push)",
            "dry": "what moistens (negotiation, softening, a letter)",
            "moist": "what dries (cutting to the point, a firm decision)",
            "wet": "what dries (cutting to the point, a firm decision)"}
    return tally, (excess[0][0] if excess else None), (cure.get(excess[0][0]) if excess else None)


def who(c, topic):
    H = c["houses"]; qh = HS["question_to_house"].get(topic, 7)
    roles = {"you (querent)": 1, "the person/thing asked about": qh,
             "helper or friend": 11, "opponent or hidden obstacle": 12, "partner": 7}
    out = {}
    for r, h in roles.items():
        f = fig(H[h - 1]); d = FIG[f]
        det = d.get("cal_details") or {}
        got = {"figure": f, "age": det.get("age_of_man"), "build": det.get("bodies"),
               "trade_or_disposition": det.get("meaning"), "peoples": det.get("peoples"),
               "science": det.get("sciences"),
               "element/planet (GD table)": f"{d.get('element')}/{d.get('planet')}"}
        missing = [k for k in ("age", "build", "trade_or_disposition") if not got[k]]
        if missing:
            got["_gap"] = ("no Calatarama f.7v-9 entry extracted for this figure ("
                           + ", ".join(missing) + ") - fill from thesis Table 4 columns, do not invent")
        out[r] = got
    return out


def where(c, topic):
    H = c["houses"]; qh = HS["question_to_house"].get(topic, 7)
    f = fig(H[qh - 1]); d = FIG[f]; det = d.get("cal_details") or {}
    return {"figure": f, "place": det.get("place"), "direction": det.get("direction"),
            "colour": det.get("colour"), "metal": det.get("metal"), "number": det.get("numbers")}


def when(c, topic):
    H = c["houses"]; qh = HS["question_to_house"].get(topic, 7)
    f = fig(H[qh - 1]); unit = FIG[f].get("time_unit")
    total = sum(sum(p) for p in H[:12])
    digits = sum(int(d) for d in str(total))
    pts = sum(H[qh - 1])
    speed = FIG[f].get("planet")
    slow = {"Saturn": "prolonged", "Jupiter": "prolonged", "Venus": "middling",
            "Mercury": "short", "Moon": "very short", "Sun": "middling", "Mars": "short"}
    return {"figure_in_question_house": f, "unit": unit or "unassigned in this source",
            "count_A_digitsum_of_all_points": f"{total} -> {digits}",
            "count_B_points_of_that_figure": str(pts),
            "pace": slow.get(speed, ""),
            "note": "unit and count are read together: e.g. count 12 + unit 'days' = twelve days"}


# ---------------------------------------------------------------- layer 6: cross-read
def crossread(c):
    H = c["houses"]
    return {f"house {i+1}": {"figure": fig(H[i]),
                            "arabic": (FIG[fig(H[i])].get("arabic") or {}).get("name"),
                            "arabic_gloss": (FIG[fig(H[i])].get("arabic") or {}).get("gloss"),
                            "ifa_odu_attested": FIG[fig(H[i])].get("ifa_odu")}
            for i in range(16) if fig(H[i]) in FIG}


# ---------------------------------------------------------------- report
ROMAN = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV","XVI"]


def report(mothers, topic, day=None, hour=None, night=False):
    c = build(mothers)
    L = []
    A = L.append
    A("# Deep cast — " + " · ".join(mothers) + f"\n_topic: {topic}_\n")
    A("## 1 The chart\n")
    A("| house | figure | 1/2 |")
    A("|---|---|---|")
    for i, p in enumerate(c["houses"]):
        A(f"| {ROMAN[i]} | {fig(p)} | {'-'.join(map(str,p))} |")
    A(f"\n**Judge = {fig(c['houses'][14])}** · **Sentence/Reconciler = {fig(c['houses'][15])}**\n")
    A("## 2 Validity — may this be judged at all?\n")
    for k, v in validity(c):
        A(f"- **{k}** — {v}")
    try:
        import elections as EL
        verdict, detail = EL.gate(c["houses"], day, hour, night)
        A(f"- **Planetary gate** ({verdict}) — {detail}")
        if verdict != "UNKNOWN":
            rank = [(d, pn, hs) for d, pn, hs in EL.best_alternatives(c["houses"])]
            good = [f"{d} ({pn}, {len(hs)} lord-figure(s){', in a strong house' if any(x for _, _, x in hs) else ''})"
                    for d, pn, hs in rank if hs]
            A("  · re-cast options if this one is void: " + ("; ".join(good) if good else
              "no weekday's lord-figure occurs in this chart"))
    except Exception as e:
        A(f"- **Planetary gate** — could not be evaluated ({e})")
    A("\n## 3 Relations inside the cast\n")
    mo = motus(c)
    A("**Motus (figures that pass)** — judge each by its SECOND coming:\n")
    if mo:
        for f, hs in mo.items():
            A(f"- {f}: houses {', '.join(ROMAN[h-1] for h in hs)}")
    else:
        A("- no figure repeats: the matter stays where it was put")
    A("\n**Parentage** (a generated figure inherits its parents — Calatarama f.22v):\n")
    for h, ps, val, tone in parentage(c):
        if ps is None:
            A(f"- house {ROMAN[h-1]} — {val}: {tone}")
        else:
            A(f"- house {ROMAN[h-1]} = houses {ROMAN[ps[0]-1]}+{ROMAN[ps[1]-1]} "
              f"({val[0]} + {val[1]}) → {tone}")
    p = perfection(c, topic)
    A(f"\n**Perfection of the matter** (querent I vs quesited {ROMAN[p['houses'][1]-1]}):\n")
    A(f"- mode: **{p['mode']}** — {p['verdict']}")
    try:
        pr = json.loads((HERE.parent / "kb" / "perfection_priors.json").read_text())["priors"]
        key = f"question_in_house_{ROMAN[p['houses'][1]-1]}"
        m = pr.get(key, {})
        share = m.get(p["mode"].lower().split("(")[0].strip()) or m.get(p["mode"].lower())
        if share is None:
            for kk, vv in m.items():
                if kk.lower().startswith(p["mode"].lower()[:6]):
                    share = vv["pct"]; break
        if share is not None:
            verdict = ("NEWSWORTHY (under-represented)" if share < 8 else
                       "ordinary for this house" if share < 40 else "NOISE - this mode occurs by default here")
            A(f"- how rare is that? **{share}%** of all 65,536 casts show this mode for house "
              f"{ROMAN[p['houses'][1]-1]} -> {verdict}")
    except Exception:
        pass
    A("\n**Triplicities (Golden Dawn grouping)**:\n")
    gd, cal = triplicities(c, topic)
    for k, v in gd.items():
        A(f"- {k}: {', '.join(v)}")
    if cal:
        A(f"\n**Calatarama house-groups for this topic** — triplicities {cal['triplicities']}, "
          f"also read houses {', '.join(ROMAN[h-1] for h in cal['extra_houses']) if cal['extra_houses'] else 'none beyond the triplicity'}")
    A("\n## 4 The trace — where the hidden thing sits\n")
    path, br, ends = via_puncti(c)
    A(f"- **Via Puncti** (head-line): {' → '.join(f'{r} {f}' for r, f in path)}"
      + (f"  · BRANCHES at {len(br)} extra head(s): {', '.join(br)} — the root is two-headed; "
         f"read every line below" if br
         else ("  · path cannot form (no witness shares the Judge's head) — the matter is exactly "
               "as it appears" if len(path) == 1 else "  · clean single line, no branch")))
    if len(ends) > 1 or br:
        A("  · the trace terminates at: " + "; ".join(
            f"house {ROMAN[h-1]} = {f} ({'a root figure' if k=='root' else 'path dies — as it appears'})"
            for h, f, k in ends))
    A(f"  → root of the question: the figure above is the driving force; if the path died at the "
      f"Judges' head it means the situation is exactly as it appears.")
    s, r, rf, t, r2, rf2 = projection(c)
    A(f"- **Projection of the Points**: {s} single dots → house {ROMAN[r-1]} holds the hidden factor "
      f"({rf}).")
    A(f"- **Part of Fortune**: {t} total points → house {ROMAN[r2-1]} ({rf2}) names where the gain stands.")
    A("\n## 5 Specifics\n")
    w = when(c, topic)
    A(f"**When** — unit: {w['unit']}; count A: {w['count_A_digitsum_of_all_points']}; "
      f"count B: {w['count_B_points_of_that_figure']}; pace: {w['pace']}. {w['note']}.")
    hum, ex, cure = humours(c, topic)
    A(f"\n**Constitution of the matter** — humours {hum}; excess: **{ex}**; remedy reads as: {cure}.")
    A("\n**Who** —\n")
    for role, d in who(c, topic).items():
        A(f"- *{role}*: **{d['figure']}** ({d['element/planet (GD table)']}) — age {d['age'] or '—'}, "
          f"build: {d['build'] or '—'}, trade/disposition: {d['trade_or_disposition'] or '—'}")
        if d.get("_gap"):
            A(f"  · {d['_gap']}")
    A("\n**Cattan's motion rulings** (book III, 1608; MED confidence - raw OCR, verify before quoting):\n")
    Hs = c["houses"]
    qh = HS["question_to_house"].get(topic, 7)
    hits = 0
    for h in (qh, 1, 12):
        txt = MOTUS_BANK.get((fig(Hs[h - 1]), h))
        if txt:
            hits += 1
            A(f"- *{fig(Hs[h - 1])}* in house {ROMAN[h-1]}: {txt}")
    if not hits:
        A("- the extracted bank has nothing for these houses (coverage 11/16 figures; the rest "
          "need the 1591 scan or a collated edition)")
    A("\n**Medieval ruling for the figures that matter** (Libro de los juysios, universal-chapter tables; "
      "typed translation, so this is the least lossy layer in the whole stack):\n")
    shown = 0
    for h in dict.fromkeys([1, qh, 11, 12, 13, 14, 15, 16]):
        key = ROMAN[h - 1]
        f = fig(c["houses"][h - 1])
        base = f.split("*")[0]
        row = GRID.get(key, {}).get(base)
        if row:
            shown += 1
            A(f"- house {key} ({base}) f.{FOLIO.get(key,'?')}: **{row}**")
    if not shown:
        A("- no table for these houses in this manuscript (VIII and X have none; I is partly legible)")
    A("\n**Where** (the place/direction/number row of the Calatarama's figure table) —\n")
    d = where(c, topic)
    A(f"- {d['figure']}: place {d['place'] or '—'}; direction {d['direction'] or '—'}; "
      f"colour {d['colour'] or '—'}; metal {d['metal'] or '—'}; number {d.get('numbers') or d.get('number') or '—'}")
    if d.get("gap"):
        A(f"  · {d['gap']}")
    A("\n## 6 The same cast in `ilm al-raml\n")
    A("| house | figure | Arabic name | gloss | Ifa odu (comparative only) |")
    A("|---|---|---|---|---|")
    for k, v in list(crossread(c).items())[:16]:
        A(f"| {k.replace('house ','')} | {v['figure']} | {v['arabic']} | {v['arabic_gloss']} | {v['ifa_odu_attested']} |")
    try:
        import questions as QS
        A(QS.render(c, topic))
    except Exception as e:
        A(f"\n## 7 Sub-question engine\n\n- not available ({e})")
    A("\n## Reading notes / honesty flags\n")
    A("- The Ifa column is a structural comparison from one modern author's table, and that author "
      "warns that sharing 16 figures does not make the two oracles behave alike. Use it as a lead to "
      "check in an Ifa source, never as an interpretation.")
    A("- Figure×house 'meanings' are not tabulated here on purpose: the engine composes them from "
      "attribute tables instead of inventing sentences.")
    A("- Where a source did not state a rule, the engine says so rather than guessing "
      "(hidden-figure, suffrages).")
    return "\n".join(L), c


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mothers", default="Carcer,Amissio,Caput Draconis,Populus")
    ap.add_argument("--topic", default="marriage")
    ap.add_argument("--out", default="-")
    ap.add_argument("--day", default=None, help="weekday the cast was made, e.g. Tuesday")
    ap.add_argument("--hour", type=int, default=None, help="planetary hour 1-12 from sunrise")
    ap.add_argument("--night", action="store_true")
    a = ap.parse_args()
    ms = [norm(x) for x in a.mothers.split(",")]
    txt, _ = report(ms, a.topic, a.day, a.hour, a.night)
    if a.out == "-":
        print(txt)
    else:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(txt)
        print("wrote", a.out)
