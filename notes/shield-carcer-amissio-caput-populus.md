# Shield from four Mothers: Carcer · Amissio · Caput Draconis · Populus

Notation: 4 rows per figure, read **top to bottom**; 1 = single dot (odd), 2 = a pair (even).
Addition: **1+1=2, 1+2=1, 2+2=2** (even total -> pair, odd total -> single).

Rule set verified against the reference chart ([redacted].png): all 11
derived houses regenerate exactly. `python3 test_shield.py` runs that check.

## The complete chart

| House | Figure | Pattern | Rows | How it is made |
|---|---|---|---|---|
| I | Carcer | 1-2-2-1 | ● / ●● / ●● / ● | Mother (given) |
| II | Amissio | 1-2-1-2 | ● / ●● / ● / ●● | Mother |
| III | Caput Draconis | 2-1-1-1 | ●● / ● / ● / ● | Mother |
| IV | Populus | 2-2-2-2 | ●● / ●● / ●● / ●● | Mother |
| V | Fortuna Minor | 1-1-2-2 | | 1st row of I,II,III,IV |
| VI | Albus | 2-2-1-2 | | 2nd row of I,II,III,IV |
| VII | Conjunctio | 2-1-1-2 | | 3rd row of I,II,III,IV |
| VIII | Amissio | 1-2-1-2 | | 4th row of I,II,III,IV |
| IX | Fortuna Major | 2-2-1-1 | | I + II |
| X | Caput Draconis | 2-1-1-1 | | III + IV |
| XI | Cauda Draconis | 1-1-1-2 | | V + VI |
| XII | Fortuna Minor | 1-1-2-2 | | VII + VIII |
| XIII (right witness) | Rubeus | 2-1-2-2 | | IX + X |
| XIV (left witness) | Albus | 2-2-1-2 | | XI + XII |
| **XV (Judge)** | **Conjunctio** | **2-1-1-2** | | XIII + XIV |
| **XVI (the C-figure)** | **Via** | **1-1-1-1** | | **Judge + Mother I** |

## Step 1 — Daughters: read the Mothers *downward*, not across

The first Daughter takes the **top** row of all four Mothers, the second Daughter the
**second** row, and so on:

```
        I  II III  IV
row 1:  1   1   2   2   ->  V    1-1-2-2  Fortuna Minor
row 2:  2   2   1   2   ->  VI   2-2-1-2  Albus
row 3:  2   1   1   2   ->  VII  2-1-1-2  Conjunctio
row 4:  1   2   1   2   ->  VIII 1-2-1-2  Amissio
```

## Step 2 — Nephews: add pairs of Mothers, then add pairs of *Daughters*

This is the step I had wrong. The first two Nephews come from the Mothers; the **third and
fourth come from the Daughters** — they are not a repeat of the first two sums.

```
 IX  = I  + II   : 1-2-2-1 + 1-2-1-2 = 2-2-1-1  Fortuna Major
 X   = III + IV  : 2-1-1-1 + 2-2-2-2 = 2-1-1-1  Caput Draconis
 XI  = V  + VI   : 1-1-2-2 + 2-2-1-2 = 1-1-1-2  Cauda Draconis
 XII = VII + VIII: 2-1-1-2 + 1-2-1-2 = 1-1-2-2  Fortuna Minor
```

Row by row for XI (V + VI): 1+2=3 odd -> **1**; 1+2 -> **1**; 2+1 -> **1**; 2+2=4 even -> **2**
which reads 1-1-1-2 = Cauda Draconis.

## Step 3 — Court: witnesses, Judge, and the 16th

```
XIII = IX + X    : 2-2-1-1 + 2-1-1-1 = 2-1-2-2  Rubeus      (right witness)
XIV  = XI + XII  : 1-1-1-2 + 1-1-2-2 = 2-2-1-2  Albus       (left witness)
XV   = XIII+XIV  : 2-1-2-2 + 2-2-1-2 = 2-1-1-2  Conjunctio  (Judge)
XVI  = XV + I    : 2-1-1-2 + 1-2-2-1 = 1-1-1-1  Via         (Reconciler)
```

## The 16th figure: its name and how it is built

It has no single agreed name — the same figure is called the **Reconciler**, the
**Sentence**, the **Superjudge** (*superiudex* / *subiudex*), the **Subjudge**, or the
"Fate", and in some manuals the **Judge of the Judge**. Whichever label a book uses, the
construction is the same: **Judge + the figure in House I (the First Mother)**.

- It answers "how does this outcome land on me?", not "what is the answer" — the Judge keeps that role.
- Because it is an extra sum, it is optional: European charts often stop at 15 and omit it.
- A rarer variant adds the Judge to the **first witness** instead, and some reconcilers are made from
  the Judge plus the house figure matching the question (e.g. House VII for a partner).

Cross-checks that this chart is arithmetically clean:

1. Judge = Conjunctio, 6 points, **even** — required: only even-pointed figures can be Judge.
2. Identity `Nephew I + Judge == Mother II + Sentence == Nephew II + Left witness` holds: all three come out 2-1-2-1 Acquisitio.
3. Among the 16 figures at least one must repeat — here Amissio (II and VIII), Caput (III and X)
   and Fortuna Minor (V and XII) each appear twice.

## Diff vs. my previous (wrong) answer

| House | Wrong before | Correct |
|---|---|---|
| XI | Cauda Draconis (by luck, from I+III) | Cauda Draconis ✓ same |
| XII | Amissio | **Fortuna Minor** |
| XIV | Rubeus | **Albus** |
| XV | Populus | **Conjunctio** |
| XVI | Rubeus | **Via** |

My earlier claim that "the Judge and the 16th are unchanged" was false — that claim came from
comparing my invented "crossed Mothers" rule against the repeat rule, neither of which is right.
