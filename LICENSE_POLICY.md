# LICENCE POLICY — the rule that lets a free library be shipped in a paid app

*This file governs what may enter the dataset at all (buckets A/B/C, source rights). It is stricter than,
and does not replace, the outbound licence: see `LICENSING.md` and `LICENSE_DATA.md`.*

Three buckets. Every row in the dataset carries one of them, and `tools/validate.py` enforces the split.

## Bucket A — **full text may be bundled**
Public-domain works and openly licensed material. In practice: anything printed before ~1900 in the
Latin/German/French/Italian/English geomancy line, plus items explicitly CC-licensed.
Record, per work: `title`, `year`, `ia_identifier` (or URL), `licence`, and the text-layer source.
Current A-list in this repo: the *Calatarama* thesis (open deposit), van Binsbergen 1996,
*Fasciculus geomanticus* 1704 (Alfagini's Quaestiones), Cattan 1591 + 1608, Heydon 1663, Agrippa
(the 1655/1783 English "Fourth Book **and Geomancy**"), Hartmann 1889, Jean de la Taille, the Lal Kitab
1939/1941 printings, the Zulu 1870 corpus, and the Persian/Arabic raml items (Leiden, McGill, Beinecke).

**Attribution string to ship in the app's "sources" screen:**
`<author>, <title> (<year>), <repository> <identifier>, public domain; rulings extracted and
translated by <you>, <date>.`

## Bucket B — **cite only; no text, no paraphrase-for-profit**
In-copyright scholarship: Skinner, Greer, Regardie, Pennick, Demulder, the *Terrestrial Astrology*
material, Charmasson's edition, Tannery's texts, Encyclopaedia of Islam. Allowed in the dataset:
title, author, year, publisher, and **your own** note about which technique you took from it, phrased in
your words, with a page pointer so a reader can look it up themselves.
Quotations: keep to a single short sentence, only where you are *criticising or verifying* it, and never
in the paid product's answer text. If in doubt: no quote.

> Practically: Bucket B is what tells you *where to dig*. Bucket A is what your app *says*.

## Bucket C — **never use**
Unofficial uploads of in-copyright books, however accessible. This repo hit four:
`stephen-skinner-terrestrial-astrology-divina`, `john-michael-greer-earth-divin`,
`israel-regardie-a-practical-gu`, `vol-3-comprehensive-enochian-d`. They were downloaded for inspection,
read, and **deleted**; `corpus/raw/ia3/_REMOVED_because_in_copyright.txt` records them, and
`validate.py` fails the build if a Bucket-C source appears as a text origin. Also excluded on principle:
any Ifá verse or taboo list obtained from a living lineage without their consent — see below.

## Special case: Ifá, àṣẹ, and living traditions
The odu corpus is not "public domain folklore". Published printings are copyrighted; the oral corpus is
held by lineage and, for much of it, restricted to the initiated. So:
1. Cite scholarship (Bascom, Abímọ̀lá) — never paste verses.
2. Use the **structural** correspondence only, and say so out loud in the UI, the way `kb/figures.yaml`
   does with its warning that sharing sixteen figures does not make the two oracles behave alike.
3. If you want the danger/taboo register ("beware a knife", "a visitor comes") as a *feature*, either
   (a) build it from geomancy's own attested particulars — the Calatarama attribute table, la Taille's
   guarded-treasure rule, Cattan's per-house motions — or (b) sit down with a practitioner, agree terms,
   and credit them as a collaborator with a share. Option (b) is not a legal formality; it is how you get
   something no scraped book contains.

## The mechanics that keep it clean
- One line per work in `works()` with `shippable_text: 1|0`; passages INSERT is asserted against it —
  a row from an unlicensed work **cannot** enter the build (`assert r["work"] in PD_WORKS`).
- `manifest.json` publishes `full_text_sources`, `cite_only_sources`, `never_used` — auditable in one file.
- Keep the raw OCR strings, not "improved" prose. Silently tidied quotations become misquotations.
- Store a `sha256` per file: if a source changes upstream, you know which passages to re-verify.
- Licence your own output as **CC BY 4.0** (your extracts, notes, tables, rules) and your code as
  **MIT/Apache-2.0**. That gives others permission to fix your errors, which is the only way a corpus of
  this kind survives, and costs you nothing.
