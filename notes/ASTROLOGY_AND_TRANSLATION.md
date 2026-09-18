# Astrology, signs, and translation

**Question asked:** is there information in this GitHub about how calculations
and astrology signs help *translation*? If not, source it.

**Answer:** the engine already knew *that* translation exists
(`kb/techniques.yaml` → `perfection.modes.translation`). It did not know
*how a sign or a planet describes the translator*. That is now
`kb/astrology.yaml`.

## The calculation (no astrology yet)

Querent significator = figure of house I (usually).
Quesited significator = figure of the house of the question (VII marriage,
IX travel, II money, …).

| Mode | Test | Reading |
|---|---|---|
| Occupation | same figure in both houses | yes, by their own nature |
| Conjunction | one significator sits next door to the other | yes, they meet; who moved did the work |
| Mutation | both significators sit next to each other *elsewhere* | yes, by an unexpected route |
| **Translation** | a *third* figure sits next to *both* houses | yes, **through a third party** |
| None | — | no completion; then look at aspects |

That table is HIGH: d'Abano / Cattan / the public restatement of the house-chart
grammar. Base rates for a VII question are already in FINDINGS
(translation ~18.8% — common, not rare).

## Where astrology enters

1. **Planet of the translator** — `kb/figures.yaml`. Names the helper
   (Mercury a message, Venus a woman, Jupiter a patron…). Two planet tables
   disagree; both print.
2. **Sign of the translator** — Agrippa, *Of Geomancy*, Turner 1655
   (public domain): Fortunes → Leo, Via/Populus → Cancer, Acquisitio → Pisces,
   Laetitia → Sagittarius, Puella → Taurus, Amissio → Libra, Conjunctio → Virgo,
   Albus → Gemini (scan gap on the last word, pairing is Mercury's houses).
   The Calatarama does **not** print signs; only planets. Do not back-fill.
3. **House aspect** when there is no perfection — Cattan: trine/sextile lean
   yes; square/opposition lean no. Angular houses weigh more than cadent.
4. **Company demi-simple** — neighbour of a different figure but the **same
   planet**. Teaching-book (Greer/Powers), MED. This is the astrological
   cousin of translation, not translation itself.

## What we did not invent

- Dexter vs sinister (counting direction) — named in modern books, no folio yet.
- Agrippa's solar-order house chart as the default — recorded, not used.
- Gerard of Cremona's astronomical geomancy — still NAMED_ONLY.

## New techniques stumbled on while sourcing

| id | status | why it showed up |
|---|---|---|
| `house_aspects` | HIGH | Cattan already in the corpus; we had not wired the distance test |
| `company_kinds` | MED | four kinds; only the house *pairs* were HIGH before |
| `agrippa_house_chart` | NAMED_NOT_DEFAULT | Agrippa 1655; Digital Ambler 2020-05-04 |
| `astronomical_geomancy` | NAMED_ONLY | same bucket as suffrages |

Grouped in `kb/astrology.yaml` so a later extract (Gerard, Estimaverunt Indi)
has a home.
