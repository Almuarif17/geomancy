# Reading your shield — figures as 1s and 2s

Extracted from `[redacted].png` by counting the gems in each cell (1 gem = **1**,
2 gems = **2**), rows read **top → bottom**, and cross-checked by eye on enlarged crops of all 16 cells.

## The figures, House I (top right) → Judge

| House | Pattern | Figure | How it got there |
|---|---|---|---|
| I | 2-2-1-2 | **Albus** | Mother (thrown) |
| II | 2-2-1-1 | **Fortuna Major** | Mother (thrown) |
| III | 1-1-2-2 | **Fortuna Minor** | Mother (thrown) |
| IV | 2-1-2-2 | **Rubeus** | Mother (thrown) |
| V | 2-2-1-2 | **Albus** | Daughter = row 1 of I,II,III,IV |
| VI | 2-2-1-1 | **Fortuna Major** | Daughter = row 2 |
| VII | 1-1-2-2 | **Fortuna Minor** | Daughter = row 3 |
| VIII | 2-1-2-2 | **Rubeus** | Daughter = row 4 |
| IX | 2-2-2-1 | **Tristitia** | Nephew = I + II |
| X | 1-2-2-2 | **Laetitia** | Nephew = III + IV |
| XI | 2-2-2-1 | **Tristitia** | drawn as I + II again |
| XII | 1-2-2-2 | **Laetitia** | drawn as III + IV again |
| XIII | 1-2-2-1 | **Puella** | Right witness = IX + X |
| XIV | 1-2-2-1 | **Puella** | Left witness = XI + XII |
| XV | 2-2-2-2 | **Populus** | Judge = XIII + XIV ✔ |

Question (as printed): "What will be the outcome or if my request for my dad to work on
moving my PPA to rivers state of Nigeria?" — PPA presumably = Police Pay Allowance / pay office
attachment; treat that as read.

## The addition rule ("how adding gives rise to the others")

Take two figures, add them row by row, and **an even total becomes 2, an odd total becomes 1**:

```
1 + 1 = 2 (even)      1 + 2 = 1 (odd)      2 + 2 = 2 (even)
```

Worked with your own Mothers:

```
  I      Albus         2 2 1 2
  II     Fortuna Major 2 2 1 1
  --------------------------- +
  IX     Tristitia     2 2 2 1     (2+2=4 even→2, 2+2→2, 1+1=2 even→2, 2+1=3 odd→1)

  III    F. Minor      1 1 2 2
  IV     Rubeus        2 1 2 2
  --------------------------- +
  X      Laetitia      1 2 2 2     (1+2=3 odd→1, 1+1→2, 2+2→2, 2+2→2)

  IX     Tristitia     2 2 2 1
  X      Laetitia      1 2 2 2
  --------------------------- +
  XIII   Puella        1 2 2 1     ← the witnesses are just nephews added in pairs

  XIII   Puella        1 2 2 1
  XIV    Puella        1 2 2 1
  --------------------------- +
  XV     Populus       2 2 2 2     ← the Judge; matches your screenshot exactly ✔
```

## The chain in one picture

```
Mothers (I–IV, right→left)
   │  read straight down each row ──────────────► Daughters (V–VIII)
   │  add pairwise (I+II, III+IV, I+III, II+IV) ► Nephews (IX–XII)
Nephews  add in pairs (IX+X, XI+XII) ───────────► Witnesses (XIII right, XIV left)
Witnesses add (XIII+XIV) ──────────────────────► JUDGE (XV)  [+ Judge+XIV = Reconciler in full charts]
```

Daughter rule in detail: the 1st row of I,II,III,IV becomes the four rows of V, the 2nd row
becomes VI, the 3rd VII, the 4th VIII. Because your four Mothers happen to be "square"
(Albus, Fortuna Major, Fortuna Minor, Rubeus), the Daughters came out **identical** to the
Mothers, which makes the rule easy to verify on this chart.

## Correction (this section previously said the app deviated — it does not)

Earlier I wrote that this chart's Nephews XI/XII were a "repeat" of IX/X and that the classical
rule would cross the Mothers instead (I+III, II+IV). That was my error, and your chart was right.

Verified now against a second cast ([redacted].png) where the Daughters differ
from the Mothers, plus al-Zanatī's own formulation as translated by van Binsbergen:

```
IX  = M1 + M2      XI  = D1 + D2      (not I+III)
X   = M3 + M4      XII = D3 + D4      (not II+IV)
```

In this particular chart D1+D2 happens to equal I+II and D3+D4 equals III+IV, because its Mothers
are "square" (their Daughters came out identical to them) - so the correct rule and my invented
"repeat" rule coincide here. The app was computing the real thing all along.

Everything downstream (XIII = IX+X, XIV = XI+XII, XV = XIII+XIV) matches the rule set.
