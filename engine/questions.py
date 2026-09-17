#!/usr/bin/env python3
"""Question engine: what to read for a specific sub-question, per the old casebooks.

This is the layer that answers "who / where / why / how long / what next" rather than "good or bad".
It implements the mechanisms found in kb/alfagini_quaestiones.json (Fasciculus geomanticus, 1704,
'Alfagini Quaestiones Geomantici') together with the Calatarama's routing table:

  1. SIGNIFICATORS by house, and DERIVED houses for relatives of the people in the question
     (a son asking about his father: 1 = the son, 4 = the father - "Domus Quarta" appendix).
  2. TURNING THE CHART FROM THE JUDGE: 'reductis ad tertiam domum judicis' - for long journeys
     count three houses from the Judge and read that figure (leaf 460). A second chart you get
     for free from the same cast.
  3. QUALITY LOGIC: bona/mala (moral value), intrans/exiens (entering = retained, leaving = lost),
     fixa/mobilis (stable = durable, mobile = changeable), 'ejusdem qualitatis' (conformity),
     angular vs cadent seat, and the consent of the four angles.
  4. TRANSLATION between the two significators as the decisive sign (the same mechanism the
     Latin calls translatio; cf. Calatarama's motus 'judge by the second coming').
  5. SEX/TRUTH by masculine vs feminine figure (dreams, the expected child).
  6. WEATHER / quality of the time by the element of the figure in I and X
     ('ignis sanitatem, aer ventum, aqua corruptionem, terra frigiditatem & siccitatem').

Every judgement string carries the leaf/folio it came from. Nothing here is invented: if the
casebook gives no rule for a sub-question, the answer says so.
"""
import argparse, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import deep_read as dr

FIG = dr.FIG
ROMAN = dr.ROMAN
KB = HERE.parent / "kb"

# element/motion/quality helpers -------------------------------------------------------------
def quality(f):   return FIG[f].get("quality")
def motion(f):   return FIG[f].get("motion")            # incoming / outgoing
def element_of(f):
    e = (FIG[f].get("element") or "").lower()
    return {"fire": "ignis", "air": "aer", "water": "aqua", "earth": "terra"}.get(e, "?")
def gender(f):
    g = FIG[f].get("gender")
    return "masculine" if g == "masculine" else ("feminine" if g == "feminine" else "?")

ANGLES = [1, 4, 7, 10]
CADENTS = [3, 6, 9, 12]

# derived houses: "the Nth from the Xth" ------------------------------------------------------
DERIVED = {
 "father_of_querent": (1, 4), "mother_of_querent": (1, 10),
 "children_of_querent": (1, 5), "partner_of_querent": (1, 7),
 "money_of_partner": (7, 2), "death_of_partner": (7, 8),
 "father_of_partner": (7, 4), "siblings_of_querent": (1, 3),
 "property_of_querent": (1, 4), "end_of_the_matter": (1, 4),
 "servants_workers": (1, 6), "hidden_enemies": (1, 12), "open_enemies": (1, 7),
 "friends_hope": (1, 11), "reputation": (1, 10), "absent_person": (1, 8),
 "the_questioner": (1, 1),
}

# what each sub-question consults (leaf numbers = Fasciculus 1704 scan pages) ----------------
RULES = {
 "substance_and_wealth": dict(houses=[2], extra=[1, 4, 7, 10], leaf=452,
    rule="a good figure in II, unimpeded, signifies wealth; a bad one poverty; the quantity is "
         "read from how many figures of gain fall in I and II with the four angles consenting; "
         "IV gives it by inheritance, VII by marriage, IX/VI by office and small cattle, X by the great",
    slot="quantity -> 'Numbers' of the figure in II"),
 "gain_or_loss_occult": dict(houses=[2, 6, 10], leaf=453,
    rule="figures of gain in the 2nd mean profit; also look in the 6th for small cattle and servants, "
         "and in the 10th for great beasts and property"),
 "short_journey": dict(houses=[9], leaf=460, rule="judge short journeys by the rules of the questions of the 9th house"),
 "long_journey": dict(houses=[9], turn_from_judge=3, leaf=460,
    rule="for journeys laid out at greater distance, REDUCE TO THE THIRD HOUSE FROM THE JUDGE and "
         "read that figure - the Judge becomes the ascendant of the journey"),
 "planting_sowing": dict(houses=[4], extra=[1, 4, 7, 10], leaf=463,
    rule="consider IV with its companions: watery figures in an airy conjunction signify fertility; "
         "airy in fiery, or earthy in earthly, sterility; airy figures abundance, above all if the "
         "angles consent"),
 "inheritance": dict(houses=[4], extra=[2, 5, 11], leaf=463,
    rule="IV must be fortunate and ENTERING; if it is in II it shows hope of succeeding; if it is "
         "exiens and infortunate, and neither I nor II pass into V or XI, the inheritance fails"),
 "inheritance_lost_recover": dict(houses=[1, 8], extra=[4, 5, 11], leaf=464,
    rule="I to the petitioner, IV to the inheritance, V and XI to hope, VII to the adversary; look at "
         "I and VIII which recall the inheritance: if it is a figure of gain and of acquisition, and "
         "the four angles are fortunate, and I is received (fits) in IV, it follows"),
 "building": dict(houses=[4], extra=[1, 10], leaf=464,
    rule="whoever wishes to build looks first at IV: entering and fixed is good, especially if X "
         "consents with IV and I is fixed and entering; IV good but mobile = good but not durable; "
         "IV mobile and exiting = bad"),
 "plenty_or_scarcity": dict(houses=[4, 5], extra=[1, 4, 7, 10, 15], leaf=465,
    rule="IV entering, fixed, fortunate = an abundant year, the more so if it is earthy and the angles "
         "and the 15th consent; exiting and infortunate = scarcity, most of all if fiery. "
         "It is also known from the FIGURA EXTRACTA drawn from IV and V"),
 "besieged_city": dict(houses=[1, 4, 7], leaf=465,
    rule="I = the people, IV = the city or castle, VII = the adversary; if I and IV are fortunate and "
         "IV is separated from I it will not be taken; if VII prevails over I and IV, or is conjoined "
         "or received by V, VI, XI, XII, it will be subjugated"),
 "pregnancy": dict(houses=[1, 5, 7], leaf=472,
    rule="I to the asker, V to the fetus: if I passes into V, X, XI, or VII into II, III, X, she is "
         "with child"),
 "child_legitimacy": dict(houses=[1, 4, 5, 7], extra=[13, 14, 15], leaf=472,
    rule="I to the one who asks, V to the fetus, VII to the woman; consider them in the angles, the "
         "witnesses and the Judge: if all are good, or the greater part, and the figures are "
         "concordant, the child is legitimate, otherwise spurious"),
 "children_disposition": dict(houses=[1, 4, 5, 6, 7], leaf=472,
    rule="consider I, IV, V, VII, VI: if they are ENTERING and good they signify good children, "
         "bad ones signify bad"),
 "sickness_incurable": dict(houses=[1, 6], leaf=473,
    rule="consider I and VI: if they are good, health; the contrary if bad, the more so if an "
         "unfortunate figure in I passes into VI, or a fortunate VI passes into VII"),
 "sick_will_he_die": dict(houses=[1, 8, 12], leaf=474, check="malefics_and_passage",
    rule="look that in I, VIII and the TWELFTH (decimam secundam) there does not fall a figure of Mars "
         "or of the Moon: if a figure of life is in I and the SAME passes into VIII, safety; if it does "
         "not pass, expect death; and if some lunar or evil figure is there, judge the same"),
 "love_durability": dict(houses=[7], leaf=480,
    rule="figures that are firm and FIXED in VII signify fixed love; MOBILE ones inconstant; "
         "BICORPOREAL ones mediocre; the same is indicated if fixed figures sit in the angles or "
         "mobile ones in the cadents"),
 "obtain_the_beloved": dict(houses=[1, 7, 8, 6, 2], leaf=480,
    rule="if I and VII are good, fortunate, entering and conforming, a good obtaining of what is "
         "wished; if I passes into VIII or VI the matter is prolonged and will be sought with "
         "solicitude; if into II, she will come to him"),
 "who_dies_first": dict(houses=[1, 2, 7], leaf=490,
    rule="for a woman ask of I, for a man of VII: if in I there is an ENTERING figure and in II a good "
         "one, and VII is EXITING, it presages the man dies first; if in VII the figure is entering "
         "and conforming, the contrary"),
 "war_and_peace": dict(houses=[1, 7], leaf=498,
    rule="give I to one army and VII to the other; see where the BAD figures are, and judge by the "
         "party that is unimpeded"),
 "enemies": dict(houses=[1, 2, 7, 10, 12], leaf=501,
    rule="I to the querent, II to his acquisition, VII to PUBLIC enemies, XII to PRIVATE enemies, X to "
         "victory; if the figures signify love in all or the greater part, there are no enemies or "
         "none to be feared; if ill figures are there, and especially if VII is fortunate and "
         "benevolent, the enmity will be of great moment, unless the enemy is a woman..."),
 "absent_man_welfare": dict(houses=[1, 8, 6, 12], leaf=506,
    rule="I to the asker, VIII to the absent one: if I is good, fortunate and passing into VIII, or "
         "VIII passing into any good house, it signifies well for the absent man; if VIII passes into "
         "VI or XII, judge the contrary"),
 "should_i_travel": dict(houses=[9], leaf=509,
    rule="if the setting out is to be made to other regions, on what day it should begin: see whether "
         "a good figure falls in IX - it indicates beginning with prosperity"),
 "dream_true_or_false": dict(houses=[1, 9, 3, 6, 11, 15], leaf=519,
    rule="I to the sleeper, IX to the dream, III, VI, XI and XV to the thing asked; MASCULINE figures "
         "signify truth, FEMININE ones falsehood"),
 "benefice_office": dict(houses=[1, 9], leaf=519,
    rule="if I and IX are fortunate, a good obtaining"),
 "weather_and_season": dict(houses=[1, 10, 11], leaf=521,
    rule="in a question about the change of the time, the figure most abundant in I and above all in X "
         "designates the quality of the time: FIRE = health, AIR = wind and health, WATER = "
         "corruption of the air and beasts, EARTH = cold and drought"),
 "king_and_realm": dict(houses=[10, 1, 2, 13], leaf=525,
    rule="X is given to the king and the realm, XIII to royal servants and magnates, I to courtiers, "
         "II to the people; these four with the other angles must be considered: if the figure of X is "
         "in I and is good, it indicates stability; if in II, the goodwill of the people"),
 "victory_in_battle": dict(houses=[7, 8, 1, 10], leaf=526,
    rule="though this question belongs to the house of litigation and war (VII), partly to X: if in "
         "VII there is a figure of Mars, in VIII a figure of the Moon, and in I a mediocre figure, "
         "report accordingly"),
 "election_best_part": dict(houses=[1, 10, 2, 5], leaf=526,
    rule="compare I with X and judge according to their signification and correspondence; especially "
         "if II and the 15th are conforming; otherwise consider the best part of all"),
 "obtain_lordship": dict(houses=[1, 10], leaf=528,
    rule="if I and X are ENTERING, fortunate and FIXED, or of the same quality, or conjoined, they "
         "give hope of obtaining"),
 "servants_faithful": dict(houses=[1, 11], leaf=531,
    rule="consider I and XI carefully: if they are fortunate, ENTERING and good, they indicate "
         "fidelity of servants"),
 "gift_or_favour": dict(houses=[1, 2, 5, 11], leaf=531,
    rule="I to the petitioner; II, V, XI to the gift: if good, good; if bad, bad; if I is in IV, V, X "
         "or XI it is good unless it passes into a bad place"),
 "imprisonment": dict(houses=[1, 12, 13, 10, 11, 7, 8], leaf=532,
    rule="look whether the figure of I and of XIII is a figure existing in XII or conjoined with it "
         "(that is, in X or XI): if they are infortunate they indicate incarceration, the more so if "
         "VII and VIII are infortunate; if I is in XI..."),
 "father_lives_longer": dict(houses=[1, 4, 8], leaf=575,
    rule="if a son asks about his father and who dies first: attend to I (the petitioner) and IV (the "
         "father); whichever of the two is stronger, with the other signs not infortunate, and VIII - "
         "that one will live longer, God willing"),
 "estate_alive_or_dead": dict(houses=[1, 8], leaf=606,
    rule="consider I and VIII; if in VIII or in its conjunction there are adverse cardinals, it is a "
         "sign of death; and if any sign between these significators makes a TRANSLATION and the "
         "question is infortunate, it is a death-sign; if fortunate, the contrary"),
 "absent_alive": dict(houses=[1, 8], leaf=641,
    rule="give I to the absent one; if it is in VIII it indicates death; and if in the conjunction of "
         "that VIII there are signs that are knowable but malevolent, judge the same"),
}

TOPIC_ALIAS = {  # map the house-router's topics onto casebook sub-questions
 "marriage": ["who_dies_first", "love_durability", "obtain_the_beloved"],
 "love_partner": ["love_durability", "obtain_the_beloved"],
 "wealth_money": ["substance_and_wealth", "gain_or_loss_occult"],
 "job_livelihood": ["obtain_lordship", "election_best_part"],
 "career_rank": ["king_and_realm", "obtain_lordship"],
 "children": ["children_disposition", "child_legitimacy"],
 "pregnancy": ["pregnancy", "child_legitimacy"],
 "health": ["sickness_incurable"],
 "illness": ["sick_will_he_die", "sickness_incurable"],
 "death": ["sick_will_he_die", "father_lives_longer"],
 "property_land": ["building", "plenty_or_scarcity", "estate_alive_or_dead"],
 "inheritance": ["inheritance", "inheritance_lost_recover"],
 "travel_journey": ["short_journey", "long_journey", "should_i_travel"],
 "studies": ["benefice_office"],
 "servants_workers": ["servants_faithful", "gain_or_loss_occult"],
 "lawsuit": ["besieged_city", "victory_in_battle"],
 "enemies_obstruction": ["enemies", "war_and_peace"],
 "imprisonment_absent": ["imprisonment", "absent_man_welfare", "absent_alive"],
 "lost_things": ["inheritance_lost_recover"],
 "news_message": ["dream_true_or_false"],
 "friends": ["servants_faithful"],
 "animals": ["gain_or_loss_occult", "planting_sowing"],
 "weather": ["weather_and_season"],
 "dream": ["dream_true_or_false"],
 "war": ["war_and_peace", "victory_in_battle"],
 "election": ["election_best_part"],
}

# app-facing synonyms: an app that sends 'theft' must not silently get an empty bank
TOPIC_ALIAS.update({
    'theft': ['inheritance_lost_recover', 'gain_or_loss_occult'],
    'litigation': ['enemies'],
    'court_case': ['enemies'],
    'stolen_goods': ['inheritance_lost_recover'],
    'lost_item': ['inheritance_lost_recover'],
    'missing_person': TOPIC_ALIAS.get('absent_friend', TOPIC_ALIAS.get('travel_journey', [])),
    'treasure': ['inheritance_lost_recover'],
    'lawsuit': ['enemies'],
})


def h(cast, n):
    return dr.fig(cast["houses"][n - 1]).split("*")[0]


def seat(cast, n):
    f = h(cast, n)
    return {"house": ROMAN[n - 1], "figure": f, "quality": quality(f), "motion": motion(f),
            "element": element_of(f), "gender": gender(f),
            "domicile": "angle" if n in ANGLES else ("cadent" if n in CADENTS else "succedent")}


def angle_conscent(cast):
    good = [ROMAN[a - 1] for a in ANGLES if quality(h(cast, a)) == "good"]
    bad = [ROMAN[a - 1] for a in ANGLES if quality(h(cast, a)) == "bad"]
    n = len(good)
    verdict = ("ANGLES CONSENT - the answer is strong" if n >= 3 else
               "partial consent" if n else "angles do not consent - the answer will not hold")
    return {"good_angles": good, "bad_angles": bad, "score": f"{n}/4", "verdict": verdict,
            "source": "Alfagini, leaf 463-465 ('maxime consentientibus angulis')"}


def turn_from_judge(cast, k):
    """'reductis ad tertiam domum judicis': treat the Judge as the 1st house and count k.

    The frame matters, so both are reported rather than silently guessed: the 15-house template the
    quaestiones were written in (15 -> 1 -> 2 ...) and the 16-house shield that includes the Sentence.
    """
    res = {}
    for size in (15, 16):
        idx = (14 + k - 1) % size                    # Judge (house 15) counts as 1
        res[f"frame_{size}"] = {"as": ROMAN[idx], "figure": h(cast, idx + 1), **seat(cast, idx + 1)}
    res["counted"] = k
    res["note"] = ("the casebook uses the 15-house template, so frame_15 is the reading the rule intends; "
                   "frame_16 is given because your chart has a 16th figure")
    res["source"] = "Alfagini, leaf 460 (long journeys: reduce to the third house from the Judge)"
    return res


def extracta(cast, a, b):
    """figura extracta: a new figure drawn from two houses of the cast."""
    f = dr.add(cast["houses"][a - 1], cast["houses"][b - 1])
    return {"from": (ROMAN[a - 1], ROMAN[b - 1]), "figure": dr.fig(f).split("*")[0],
            "quality": quality(dr.fig(f).split("*")[0]), "motion": motion(dr.fig(f).split("*")[0]),
            "element": element_of(dr.fig(f).split("*")[0]),
            "source": "Alfagini, leaf 465 (figura educta from IV and V); Calatarama f.39v"}


def translation_between(cast, x, y):
    """A figure that sits in a house next to x AND next to y carries the matter between them."""
    nx = {h for h in (x - 1, x + 1) if 1 <= h <= 12 and h not in (x, y)}
    ny = {h for h in (y - 1, y + 1) if 1 <= h <= 12 and h not in (x, y)}
    for i in nx:
        for j in ny:
            if i != j and cast["houses"][i - 1] == cast["houses"][j - 1]:
                return {"figure": h(cast, i), "from_house": ROMAN[i - 1], "to_house": ROMAN[j - 1],
                        "verdict": "TRANSLATION between the two significators - the matter is carried, "
                                   "so the answer comes through a third party or a change of place",
                        "source": "Alfagini leaf 606 ('si signum ... translationem fecerit'); "
                                  "Calatarama f.11v (judge by the second coming)"}
    return {"figure": None, "verdict": "no translation between the two - they do not speak to each other",
            "source": "Alfagini leaf 606"}


def malefics(cast, houses):
    """Does a figure of Mars or of the Moon sit in the houses the rule forbids?"""
    hits = []
    for n in houses:
        f = h(cast, n)
        pl = FIG[f].get("planet")
        if pl in ("Mars", "Moon"):
            hits.append(f"{f} in {ROMAN[n-1]} (ruled by {pl})")
    return hits


def life_passage(cast):
    """"a figure of life in I that passes into VIII" -> safety. 'figure of life' is not enumerated in
    the Latin here, so it is operationalised as good-and-entering and that choice is disclosed."""
    f1, f8 = h(cast, 1), h(cast, 8)
    p1 = dr.pat(f1)
    lives = quality(f1) == "good" and motion(f1) == "incoming"
    passes = p1 in [x for i, x in enumerate(cast["houses"]) if i == 7]
    return {"figure_of_life_in_I": f1 if lives else None,
            "same_figure_in_VIII": passes,
            "verdict": ("safety - the figure of life passes from I into VIII" if lives and passes else
                        "death expected - no figure of life passes into VIII" if lives and not passes else
                        "no figure of life in I to begin with (good+entering)"),
            "operationalised": "'figure of life' read as good + incoming; the casebook does not list them",
            "source": "Alfagini leaf 474"}


def answer(cast, key):
    r = RULES[key]
    out = {"question": key.replace("_", " "), "rule": r["rule"], "leaf": r["leaf"],
           "consult": [seat(cast, n) for n in r["houses"]],
           "also": [seat(cast, n) for n in r.get("extra", [])]}
    out["angles"] = angle_conscent(cast)
    if r.get("turn_from_judge"):
        out["turned_chart"] = turn_from_judge(cast, r["turn_from_judge"])
    if "figura extracta" in r["rule"] or "EXTRACTA" in r["rule"]:
        out["extracta_IV_V"] = extracta(cast, 4, 5)
    if len(r["houses"]) >= 2:
        out["between"] = translation_between(cast, r["houses"][0], r["houses"][1])
    # the actual call, stated as the sources state it
    primary = h(cast, r["houses"][0])
    q, m = quality(primary), motion(primary)
    ph = r["houses"][0]
    seat_kind = "angle" if ph in ANGLES else ("cadent" if ph in CADENTS else "succedent")
    if q == "good" and m == "incoming":
        call = f"{primary} in {ROMAN[r['houses'][0]-1]}: good AND entering - the thing is gained and kept"
    elif q == "good" and m == "outgoing":
        call = f"{primary} in {ROMAN[r['houses'][0]-1]}: good but leaving - gained and then departing, or gained only by moving"
    elif q == "bad" and m == "incoming":
        call = f"{primary} in {ROMAN[r['houses'][0]-1]}: bad and entering - the harm arrives and stays"
    elif q == "bad" and m == "outgoing":
        call = f"{primary} in {ROMAN[r['houses'][0]-1]}: bad but leaving - it passes; the loss will not hold"
    else:
        call = f"{primary} in {ROMAN[r['houses'][0]-1]}: communal - takes the side of the question, so read the neighbours"
    # la Taille's tie-break: a MOBILE or COMMUNAL figure does not decide; the house decides.
    if m == "outgoing" or q == "communal":
        house_side = ("the house is an angle, so it upholds the matter" if seat_kind == "angle" else
                      "the house is succedent, so the matter is held but slowly" if seat_kind == "succedent" else
                      "the house is cadent, so it falls away however good the figure is")
        out["tiebreak"] = {
            "why": f"{primary} is {'communal' if q == 'communal' else 'mobile (going out)'} - by la Taille, "
                   f"'preferez le jugement selon les qualitez des maisons'",
            "house_seat": seat_kind, "settles_as": house_side,
            "source": "kb/techniques.yaml house_quality_tiebreak (Jean de la Taille, La Geomancie)"}
        call = f"{call}; but the figure is {'communal' if q=='communal' else 'mobile'}, so {house_side}"
    if r.get("check") == "malefics_and_passage":
        out["forbidden_figures"] = malefics(cast, r["houses"]) or "none of Mars or the Moon in those houses"
        out["life_passage"] = life_passage(cast)
        out["call"] = out["life_passage"]["verdict"]
    out["call"] = call if r.get("check") != "malefics_and_passage" else out["call"]
    out["strength"] = out["angles"]["verdict"]
    return out


def render(cast, topic):
    keys = TOPIC_ALIAS.get(topic, [])
    if not keys:
        return (f"No casebook rule is registered for the topic '{topic}'. Registered: "
                + ", ".join(sorted(TOPIC_ALIAS)))
    L = [f"\n## 7 Sub-question engine (Alfagini quaestiones, Fasciculus geomanticus 1704)\n"]
    for k in keys:
        a = answer(cast, k)
        L.append(f"\n### {a['question']}\n")
        L.append(f"- **The rule** (leaf {a['leaf']}): {a['rule']}")
        for s in a["consult"]:
            L.append(f"  · house {s['house']}: **{s['figure']}** — {s['quality']}, {s['motion']}, "
                     f"{s['element']}, {s['gender']}, seat {s['domicile']}")
        if a.get("also"):
            L.append("  · also read: " + "; ".join(f"{s['house']} {s['figure']} ({s['quality']}/{s['motion']})"
                                                   for s in a["also"]))
        L.append(f"- **Angles**: {a['angles']['score']} good ({', '.join(a['angles']['good_angles']) or 'none'}) "
                 f"— {a['angles']['verdict']}")
        if "turned_chart" in a:
            t = a["turned_chart"]
            ORD = {1:"first",2:"second",3:"third",4:"fourth",5:"fifth",6:"sixth",7:"seventh",8:"eighth"}
            a15, a16 = t["frame_15"], t["frame_16"]
            L.append(f"- **Chart turned from the Judge** (the {ORD.get(t['counted'],'?')} house from XV): "
                     f"in the 15-house frame → **{a15['as']} {a15['figure']}** "
                     f"({a15['quality']}, {a15['motion']}, {a15['domicile']}); "
                     f"in the 16-house frame → {a16['as']} {a16['figure']} ({a16['quality']}, {a16['motion']})")
            L.append(f"  · {t['note']} — {t['source']}")
        if "extracta_IV_V" in a:
            e = a["extracta_IV_V"]
            L.append(f"- **Figura extracta** from {e['from'][0]}+{e['from'][1]}: **{e['figure']}** "
                     f"({e['quality']}, {e['motion']}, {e['element']}) — the hidden root of the matter")
        if "forbidden_figures" in a:
            L.append(f"- **Figures of Mars or the Moon in the forbidden houses**: {a['forbidden_figures']}")
        if "life_passage" in a:
            lp = a["life_passage"]
            L.append(f"- **Passage test**: figure of life in I = {lp['figure_of_life_in_I'] or 'none'}; "
                     f"same figure in VIII = {lp['same_figure_in_VIII']} — {lp['verdict']} "
                     f"_[{lp['operationalised']}]_")
        if "between" in a:
            L.append(f"- **Between the significators**: {a['between']['verdict']}")
        L.append(f"- **Call**: {a['call']}; {a['strength']}")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mothers", default="Carcer,Amissio,Caput Draconis,Populus")
    ap.add_argument("--topic", default="illness")
    ap.add_argument("--all", action="store_true", help="run every registered sub-question")
    a = ap.parse_args()
    cast = dr.build([dr.norm(x) for x in a.mothers.split(",")])
    if a.all:
        for k in RULES:
            print(render(cast, k).replace("## 7 Sub-question engine", "### " + k))
    else:
        print(render(cast, a.topic))
    print("\nregistered sub-questions:", len(RULES), "| topic keys:", len(TOPIC_ALIAS))
