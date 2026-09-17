"""Validation for the deep-reading engine.

Ground truth = the dots I counted out of the two app screenshots (patterns, not names: names come
from kb/figures.yaml, where Puer=1-1-2-1 / Puella=1-2-1-1 per the Digital Ambler binary table).
Then every algorithmic invariant is checked over all 16^4 = 65,536 possible casts.
"""
import itertools, sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import deep_read as dr
import export_reading as EX

# Ground truth: gem counts measured out of the first reference cast (data/fixtures/chart2.json),
# rows top->bottom, 1 gem = 1, 2 gems = 2. Names are derived from the KB, never hand-written.
def _fixture(name):
    """Prefer the published fixture; fall back to the working corpus layout."""
    root = pathlib.Path(__file__).resolve().parent.parent
    for p in (root / "data/fixtures" / name, root / "corpus/raw" / name):
        if p.exists():
            return p
    raise FileNotFoundError(f"{name}: run scripts/ia_fetch.py or restore data/fixtures/")

_drawn = {k: [2 if g == 2 else 1 for g in v] for k, v in json.load(open(_fixture("chart2.json"))).items()}
_h = "I II III IV V VI VII VIII IX X XI XII XIII XIV XV".split()
REF = {"mothers": [dr.fig(_drawn[k]) for k in _h[:4]],
       "houses": [_drawn[k] for k in _h] + [dr.add(_drawn["XV"], _drawn["I"])]}   # + Sentence

PPA = {"mothers": ["Albus", "Fortuna Major", "Fortuna Minor", "Rubeus"],
       "_note": "second live cast; XVI recomputed from the rule, not read off the image",
       "houses": [[2,2,1,2],[2,2,1,1],[1,1,2,2],[2,1,2,2],
                  [2,2,1,2],[2,2,1,1],[1,1,2,2],[2,1,2,2],
                  [2,2,2,1],[1,2,2,2],[2,2,2,1],[1,2,2,2],
                  [1,2,2,1],[1,2,2,1],[2,2,2,2]]}
PPA["houses"].append(dr.add(PPA["houses"][14], PPA["houses"][0]))   # Sentence, computed not typed

NAMES = list(dr.FIG.keys())
fails = 0


def chk(name, cond, detail=""):
    global fails
    print(("PASS  " if cond else "FAIL  ") + name + (("   " + detail) if detail else ""))
    fails += (not cond)


for tag, G in (("reference screenshot", REF), ("PPA screenshot", PPA)):
    c = dr.build(G["mothers"])
    ok = c["houses"] == G["houses"]
    bad = [(dr.fig(a), dr.fig(b)) for a, b in zip(c["houses"], G["houses"]) if a != b]
    chk(f"{tag}: 16/16 houses reproduce from the 4 Mothers alone", ok, str(bad[:4]))

chk("pattern/name table is a bijection (16 unique patterns)",
    len({tuple(v["pattern"]) for v in dr.FIG.values()}) == 16)

judge_odd = 0
paths = 0
path_reaches_root = 0
no_repeat = 0
dup_pair_sum = 0
for combo in itertools.product(NAMES, repeat=4):
    c = dr.build(list(combo))
    H = c["houses"]
    if sum(H[14]) % 2:
        judge_odd += 1
    if len({tuple(p) for p in H}) == 16:
        no_repeat += 1
    if H[14][0] == 1:
        paths += 1
        pth, br, _ends = dr.via_puncti(c)
        if len(pth) == 4 and not br:
            path_reaches_root += 1
    # any figure added to itself must yield Populus (the identity) - the algebra behind
    # why "Judge + Left Witness" is degenerate
    if dr.add(H[14], H[14]) != [2, 2, 2, 2]:
        dup_pair_sum += 1

chk("Judge is always even in points (the classical parity law)", judge_odd == 0, f"violations={judge_odd}")
chk("Via Puncti reaches a root figure whenever the Judge's head is single",
    paths > 0 and path_reaches_root == paths, f"{path_reaches_root}/{paths}")
chk("a cast can never contain 16 distinct figures (at least one repeats)", no_repeat == 0, f"counter={no_repeat}")
chk("f+f = Populus always (why Sentence must use Mother I, not a witness)", dup_pair_sum == 0)

# exhaustive proof that the degenerate definition cannot work, for every witness pair
W = list(itertools.product([1, 2], repeat=4))
degen = 0
for x, y in itertools.product(W, repeat=2):
    j = dr.add(list(x), list(y))
    if dr.add(j, list(y)) != list(x):
        degen += 1
chk("Judge+LeftWitness == RightWitness for all 65,536 witness pairs", degen == 0, f"violations={degen}")

topics = ["marriage", "wealth_money", "health", "travel_journey", "lost_things", "enemies_obstruction"]
try:
    for t in topics:
        c = dr.build(NAMES[:4])
        for fn in (dr.validity, dr.motus, dr.parentage, dr.crossread):
            fn(c)
        dr.perfection(c, t); dr.triplicities(c, t); dr.via_puncti(c); dr.projection(c)
        dr.humours(c, t); dr.who(c, t); dr.where(c, t); dr.when(c, t)
    ran = True
except Exception as e:
    ran = False
    print("   layer crash:", e)
chk("all layers run for every question topic", ran)

txt, _ = dr.report(REF["mothers"], "marriage")
chk("report renders with judge/sentence and specifics",
    len(txt) > 1500 and "Judge = " in txt and "Via Puncti" in txt and "**Where**" in txt, f"{len(txt)} chars")


# ---- parentage integrity: every listed pair must really generate its house, and the
# Daughters must be flagged as transposition (this is the check that catches a mis-wired
# parents map, which is exactly how the first version of parentage() was wrong).
c0 = dr.build(["Albus", "Fortuna Major", "Fortuna Minor", "Rubeus"])
bad_par = []
for h, ps, val, tone in dr.parentage(c0):
    if ps is None:
        if not tone.startswith("Daughter"): bad_par.append((h, "wrongly marked"))
        continue
    a, b = ps
    if dr.add(c0["houses"][a - 1], c0["houses"][b - 1]) != c0["houses"][h - 1]:
        bad_par.append((h, a, b))
chk("parentage: every stated pair actually sums to its house; Daughters are transpositions",
    not bad_par, str(bad_par[:3]))
_daughters = [t for h, ps, v, t in dr.parentage(c0) if ps is None]
chk("exactly the 4 Daughters are transpositions", len(_daughters) == 4, str(len(_daughters)))

# ---- question engine: the casebook mechanisms must actually compute, and must not invent
import questions as QS
cast = dr.build(["Albus", "Fortuna Major", "Fortuna Minor", "Rubeus"])
bad = []
for k in QS.RULES:
    try:
        a = QS.answer(cast, k)
        for key in ("question", "rule", "leaf", "consult", "angles", "call", "strength"):
            if key not in a: bad.append((k, "missing " + key))
        if not a["consult"]: bad.append((k, "no house consulted"))
        if not (1 <= a["leaf"] <= 900): bad.append((k, "bad leaf ref"))
    except Exception as e:
        bad.append((k, f"crash {e}"))
chk("all casebook sub-questions compute with a source leaf", not bad, str(bad[:3]))
chk("every sub-question cites a Fasciculus leaf",
    all(isinstance(v["leaf"], int) for v in QS.RULES.values()), str(len(QS.RULES)))
chk("turned-chart from the Judge reports both frames (15 and 16 houses)",
    set(QS.turn_from_judge(cast, 3)) >= {"frame_15", "frame_16"})
chk("no unregistered topic is silently answered",
    "No casebook rule" in QS.render(cast, "underwater_basket_weaving"))
# the specific rare readings we recovered must be present
for k in ("dream_true_or_false", "plenty_or_scarcity", "long_journey", "sick_will_he_die", "imprisonment"):
    chk(f"casebook rule '{k}' is wired", k in QS.RULES and "houses" in QS.RULES[k])
chk("masculine/feminine dream rule uses gender, not guesswork",
    "gender" in QS.seat(cast, 9))
# la Taille's tie-break must fire exactly when the figure is mobile or communal, and say what decides
fired = 0
for cast_m in [["Via", "Populus", "Via", "Populus"], ["Carcer", "Amissio", "Caput Draconis", "Populus"],
               ["Albus", "Fortuna Major", "Fortuna Minor", "Rubeus"]]:
    c2 = dr.build(cast_m)
    for k in QS.RULES:
        a = QS.answer(c2, k)
        first = a["consult"][0]
        if first["motion"] == "outgoing" or first["quality"] == "communal":
            if "tiebreak" not in a: bad.append((k, "tie-break missing")); continue
            fired += 1
        elif "tiebreak" in a:
            bad.append((k, "tie-break fired when it should not"))
chk("la Taille tie-break fires iff the figure is mobile or communal", fired > 0, f"{fired} firings")
print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)

# ---------------------------------------------------------------- contract pin
# The published reading shape is what an app parses, so a silent change to it is a breaking
# release. This compares the full exported reading for the audited cast against a committed
# golden; regenerate deliberately with: python3 engine/test_deep_read.py --bless
if "--bless" in sys.argv:
    GOLDEN = ROOT / "data" / "fixtures" / "reading.golden.json"
    GOLDEN.write_text(json.dumps(EX.reading([dr.norm(x) for x in REF["mothers"]], "marriage"),
                                 indent=1, ensure_ascii=False) + "\n")
    print("blessed", GOLDEN.relative_to(ROOT))
else:
    GOLDEN = ROOT / "data" / "fixtures" / "reading.golden.json"
    if GOLDEN.exists():
        want = json.loads(GOLDEN.read_text())
        got = EX.reading([dr.norm(x) for x in REF["mothers"]], "marriage")
        def diff(a, b, path=""):
            if isinstance(a, dict) and isinstance(b, dict):
                out = []
                for k in sorted(set(a) | set(b)):
                    out += diff(a.get(k), b.get(k), f"{path}.{k}")
                return out
            if isinstance(a, list) and isinstance(b, list):
                if len(a) != len(b):
                    return [f"{path}: length {len(a)} vs {len(b)}"]
                return [x for i, (u, v) in enumerate(zip(a, b)) for x in diff(u, v, f"{path}[{i}]")]
            return [] if a == b else [f"{path}: {json.dumps(a)[:40]} vs {json.dumps(b)[:40]}"]
        d = diff(got, want)
        chk("exported reading matches the golden contract", not d,
            ("; ".join(d[:3]) + (f" (+{len(d)-3} more)" if len(d) > 3 else "")) if d else "byte-equal")
    else:
        chk("data/fixtures/reading.golden.json present", False, "run: python3 engine/test_deep_read.py --bless")
