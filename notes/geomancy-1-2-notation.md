# Geomancy — the 16 figures written in 1s and 2s

**Key (the chart's own rule):** one dot = **1** (odd, "active"), a pair of dots = **2** (even, "passive").
Rows are read **top → bottom**. In the drawings below `•` = single dot, `: :` = pair.

## Row 1 — the four Mothers

```
Via            Populus         Conjunctio         Carcer
  •              : :              : :               •
  •              : :               •                : :
  •              : :               •                : :
  •              : :              : :                •
1-1-1-1        2-2-2-2          2-1-1-2           1-2-2-1
```

## Row 2 — the four Daughters

```
Caput Draconis  Cauda Draconis   Puella             Puer
  : :              •                •                 •
   •                •                •                 •
   •                •               : :               : :
   •               : :               •                 •
2-1-1-1         1-1-1-2          1-1-2-1           1-2-1-1
```

(Puella as drawn here is 1-1-2-1; the traditional figure is 1-2-2-1 — see "notes" below.)

## Row 3 — the four Nephews

```
Fortuna Major   Fortuna Minor    Rubeus             Albus
  : :              •                : :               : :
  : :              •                 •                : :
   •               : :              : :                •
   •               : :              : :               : :
2-2-1-1         1-1-2-2          2-1-2-2           2-2-1-2
```

## Row 4 — Witnesses (and the two Judges are Via / Populus)

```
Acquisitio      Amissio          Tristitia          Laetitia
  : :              •                : :               •
   •               : :               : :              : :
  : :              •                : :               : :
   •               : :                •               : :
2-1-2-1         1-2-1-2          2-2-2-1           1-2-2-2
```

## Flat list

| # | Figure | 1/2 | dots | # | Figure | 1/2 | dots |
|---|--------|-----|------|---|--------|-----|------|
| 1 | Via | 1-1-1-1 | 4 | 9 | Fortuna Major | 2-2-1-1 | 6 |
| 2 | Populus | 2-2-2-2 | 8 | 10 | Fortuna Minor | 1-1-2-2 | 6 |
| 3 | Conjunctio | 2-1-1-2 | 6 | 11 | Rubeus | 2-1-2-2 | 7 |
| 4 | Carcer | 1-2-2-1 | 6 | 12 | Albus | 2-2-1-2 | 7 |
| 5 | Caput Draconis | 2-1-1-1 | 5 | 13 | Acquisitio | 2-1-2-1 | 6 |
| 6 | Cauda Draconis | 1-1-1-2 | 5 | 14 | Amissio | 1-2-1-2 | 6 |
| 7 | Puella | 1-1-2-1 | 5 | 15 | Tristitia | 2-2-2-1 | 7 |
| 8 | Puer | 1-2-1-1 | 5 | 16 | Laetitia | 1-2-2-2 | 7 |

## The worked example at the top of the image

Those four long dot-lines are not house figures; they only demonstrate the generating rule: take a
number, lay it out in rows of dots, an **odd** row is one dot and an **even** row is a pair. In the
image every line is drawn as evenly spaced adjacent pairs, so what they actually pin down is the
**total** (15, 19, 18, 12) — and those totals are the dot-counts of the four Mothers under them:

```
Via          1-1-1-1   all odd      -> line labelled 15
Populus      2-2-2-2   all even     -> line labelled 19
Conjunctio   2-1-1-2                 -> line labelled 18
Carcer       1-2-2-1                 -> line labelled 12
```

Counting the dots actually printed gives 16 / 20 / 20 / 14, i.e. one more than each label — a
drawing artifact, not a different rule.

## Self-consistency checks (all pass on the digits above)

- **Nieces = Mothers with 1↔2 swapped:** Via 1-1-1-1 ↔ Populus 2-2-2-2; Conjunctio 2-1-1-2 ↔ Carcer 1-2-2-1.
- **Daughters are mirror pairs (read top row downward vs bottom row upward):** Caput ↔ Cauda Draconis, Puella ↔ Puer, Rubeus ↔ Albus, Tristitia ↔ Laetitia.
- **Fortuna Major ↔ Fortuna Minor** are likewise 1↔2 flips of each other.
- **Via** (1-1-1-1) and **Populus** (2-2-2-2) are the all-odd and all-even figures — the two Judges of the tradition.

## Notes on the source image

1. **Puella** is drawn with 5 dots (1-1-2-1). Standard geomancy gives Puella 1-2-2-1 (6 dots),
   which would make it the exact mirror of Puer. Everything else in the chart is standard, so this
   looks like an error in the diagram rather than a variant tradition.
2. Because 14 of the 16 figures are palindromes, "top → bottom" vs "bottom → top" only matters for
   Fortuna Major/Minor and Puella/Puer.
