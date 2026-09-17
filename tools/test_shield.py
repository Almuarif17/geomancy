"""Validate shield.py against both real app screenshots (houses V..XV regenerated)."""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from shield import FIGURES, shield, add, name

def regenerate(mothers):
    _M, D, N, W, J, S = shield(mothers)
    return {h: f for h, f in zip(
        "V VI VII VIII IX X XI XII XIII XIV XV XVI".split(), D + N + W + [J, S])}

CH2 = {k: [2 if g == 2 else 1 for g in v] for k, v in json.load(open(str(pathlib.Path(__file__).resolve().parent.parent / "data/fixtures/chart2.json"))).items()}
CH1 = {"I":[2,2,1,2],"II":[2,2,1,1],"III":[1,1,2,2],"IV":[2,1,2,2],"V":[2,2,1,2],"VI":[2,2,1,1],
       "VII":[1,1,2,2],"VIII":[2,1,2,2],"IX":[2,2,2,1],"X":[1,2,2,2],"XI":[2,2,2,1],"XII":[1,2,2,2],
       "XIII":[1,2,2,1],"XIV":[1,2,2,1],"XV":[2,2,2,2]}

fails = 0
for tag, CH in (("chart2 (reference screenshot)", CH2), ("cast 2 (the square cast)", CH1)):
    got = regenerate([CH[h] for h in "I II III IV".split()])
    for h in "V VI VII VIII IX X XI XII XIII XIV XV".split():
        ok = got[h] == CH[h]
        fails += not ok
        if not ok:
            print(f"  FAIL {tag} {h}: drawn {CH[h]} vs computed {got[h]}")
    print(f"{tag}: houses V-XV regenerated from the 4 Mothers -> "
          f"{'11/11 correct' if not fails else 'errors'}; 16th = {name(got['XVI'])}")

assert len(FIGURES) == 16 and len({tuple(v) for v in FIGURES.values()}) == 16, "figure table must be 16 unique"
assert add([1,1,2,2],[2,2,1,2]) == [1,1,1,2], "addition rule changed"
print("figure table: 16 unique patterns OK | addition rule OK | failures:", fails)
sys.exit(1 if fails else 0)
