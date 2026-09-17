#!/usr/bin/env python3
"""Planetary-day / planetary-hour layer: is this cast legal, and when is the next good chance?

Source: Libro de los juysios de calatarama, ch.2 (ff.4v-5v) + the figure table on f.5, as translated
in Cameron Finan's thesis (pp.133-136). Rule: the casting is confirmed when a figure of the lord of
the day (or, at night, of the Moon) is present in the chart and sits in a strong house; if no figure of
the day or of the hour appears at all, "it is entirely useless" - i.e. re-cast.

The Calatarama's planet->figure table differs from the Golden Dawn one for Puer (Venus here, Mars
there) and for Populus/Via/Albus; both are kept, because that difference is itself information.
"""
import datetime

# Chaldean order, walking outward-in: hour 1 of Sunday = Sun, then Venus, Mercury, Moon, Saturn,
# Jupiter, Mars, repeat. The day's lord is the planet of its first hour.
CHALDEAN = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]
DAY_LORD = {"Monday": "Moon", "Tuesday": "Mars", "Wednesday": "Mercury", "Thursday": "Jupiter",
            "Friday": "Venus", "Saturday": "Saturn", "Sunday": "Sun"}

FIGURES_OF_PLANET = {          # Calatarama f.5 (via Finan pp.134-135)
 "Sun":     ["Fortuna Major", "Fortuna Minor"],
 "Moon":    ["Albus", "Via"],
 "Mars":    ["Rubeus", "Puella"],
 "Mercury": ["Conjunctio", "Populus"],
 "Jupiter": ["Acquisitio", "Laetitia", "Caput Draconis"],
 "Venus":   ["Puer", "Amissio"],
 "Saturn":  ["Tristitia", "Carcer", "Cauda Draconis"],
}
# validated line by line against the Calatarama's folio 5 table (thesis Table 6, pp.134-135):
#   Sun: Fortuna Mayor/Menor | Moon: Alua/Via | Mars: Rubea/Puela | Mercury: Congregacion/Populo
#   Jupiter: Itisicio/Liticia/Cabeça del Dragon | Venus: Puer/Emysio | Saturn: Carçel/Tristiçia/Cola
GOLDEN_DAWN = {                # the modern table, for contrast
 "Sun": ["Fortuna Major", "Fortuna Minor"], "Moon": ["Populus", "Via"],
 "Mars": ["Puer", "Rubeus"], "Mercury": ["Albus", "Conjunctio"],
 "Jupiter": ["Acquisitio", "Laetitia"], "Venus": ["Puella", "Amissio"],
 "Saturn": ["Carcer", "Tristitia"], "Node": ["Caput Draconis", "Cauda Draconis"],
}
STRONG_HOUSES = [1, 4, 7, 10, 13, 14, 15, 16]   # angular + the Court


def hour_lord(day_name, hour_from_sunrise, night=False):
    """Planet of the n-th planetary hour (n = 1..24, 1 = first hour after sunrise)."""
    start = CHALDEAN.index(DAY_LORD[day_name])
    return CHALDEAN[(start + hour_from_sunrise - 1) % 7]


def planetary_hour(sunrise_min, sunset_min, now_min):
    """The Astrological hour number 1-24 from clock minutes-since-midnight.

    The Calatarama is explicit that these are NOT sixty-minute hours: "the hours are only of sixty
    minutes in length twice a year, at the spring and autumn equinoxes" (thesis p.135, after
    Paul of Alexandria) - day and night are each cut into 12 equal parts, so a summer day-hour is
    longer than a winter one. Using clock hours instead silently shifts the lord of the hour,
    which is exactly the field the day/hour validity gate reads. So: compute it properly.
    Returns (hour_number 1..24, is_day_hour).
    """
    if not (0 <= sunrise_min < sunset_min <= 1440):
        raise ValueError("sunrise/sunset must be minutes since midnight with sunrise < sunset")
    if sunrise_min <= now_min < sunset_min:
        k = 12 * (now_min - sunrise_min) / (sunset_min - sunrise_min)
        return int(min(11, k)) + 1, True
    night_len = 1440 - (sunset_min - sunrise_min)
    past = (now_min - sunset_min) % 1440
    k = 12 * past / night_len
    return int(min(11, k)) + 13, False


def gate(houses, day_name=None, hour=None, night=False, table=FIGURES_OF_PLANET):
    """Return (verdict, detail). houses: list of 16 patterns, index 0 = house I."""
    names = []
    for p in houses:
        names.append(_figname(p))
    lords = []
    if day_name:
        lords.append(("day " + day_name, DAY_LORD[day_name]))
    if hour is not None:
        lords.append((f"hour {hour}", hour_lord(day_name or "Sunday", hour, night)))
    if not lords:
        return "UNKNOWN", ("no day/hour supplied - the medieval gate cannot be tested. Give the weekday "
                           "and the planetary hour, computed from that day's sunrise and sunset "
                           "(elections.planetary_hour), not from the clock")
    out, ok_any = [], False
    for label, planet in lords:
        figs = table.get(planet, [])
        if night and "day" in label:
            figs = table["Moon"]
            label += " (night: Moon's figures only)"
        where = {f: [i + 1 for i, n in enumerate(names) if n == f] for f in figs}
        present = {f: h for f, h in where.items() if h}
        strong = sorted({h for hs in present.values() for h in hs if h in STRONG_HOUSES})
        ok_any = ok_any or bool(present)
        out.append(f"{label}: lord {planet} -> {', '.join(figs)}; "
                   + (f"PRESENT in {present}" + (f", strong houses {strong}" if strong else " (no strong house)")
                      if present else "ABSENT -> casting void, re-cast"))
    verdict = ("PASS" if ok_any else "FAIL")
    return verdict, " | ".join(out)


import sys as _sys, pathlib as _p
_sys.path.insert(0, str(_p.Path(__file__).resolve().parent))
import deep_read as _dr        # reuse the one figure table; do not duplicate it


def _figname(p):
    return _dr.fig(list(p))


def best_alternatives(houses, table=FIGURES_OF_PLANET):
    """Which weekday would make THIS chart legal? (re-cast advice = the 'best alternative'.)"""
    res = []
    for d, planet in DAY_LORD.items():
        hits = []
        for f in table[planet]:
            for i, p in enumerate(houses):
                if _figname(p) == f:
                    hits.append((f, i + 1, i + 1 in STRONG_HOUSES))
        res.append((d, planet, hits))
    res.sort(key=lambda x: (-len(x[2]), -sum(1 for _, _, s in x[2] if s)))
    return res


if __name__ == "__main__":
    import sys, pathlib, json
    H = json.loads(pathlib.Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else {}
    seq = [H[k] for k in "I II III IV V VI VII VIII IX X XI XII XIII XIV XV".split() if k in H]
    if len(sys.argv) > 2:
        print(gate(seq, sys.argv[2]))
    else:
        print(gate(seq))
    for d, p, h in best_alternatives(seq):
        print(f"  {d:10s} lord {p:8s} {len(h)} figure(s){'  <== in a strong house' if any(s for _,_,s in h) else ''}")
