# RESEARCH LEDGER — where to go next, and what each door asks of you

## 0. The short answer on registration and permission

**Nothing in this whole project has required payment so far, and almost nothing requires registration.**
The complete Internet Archive sweep is done and here are the numbers:

| what | how many | what it costs you |
|---|---:|---|
| relevant items found (259 of 1,604 unique) | 259 | — |
| **open, with a text layer** — fetch now, no account | **99** | nothing |
| of those, already pulled into this corpus | 14 | nothing |
| **borrow-only** items (the text is there but locked to a loan) | **16** | a **free archive.org account**; 1-hour browser read or 14-day loan; no payment |
| **scans with no text layer** — need an OCR pass | **45** | nothing but compute time (~25 s/page with tesseract) |

So for the IA: **register one free account** and you have every item on the list. No fee, no letter, no
institution. The `rstr` column in `corpus/ia/IA_CATALOG.md` marks exactly which rows need it.

Where permission actually bites is **manuscripts and reading rooms**, not printed books — and only in the
tier-2 institutions below. What each asks:

| door | registration / permission | what to say or bring |
|---|---|---|
| Internet Archive | free account, nothing else | email address |
| HathiTrust | none to search; **partner-institution login** for some in-copyright full view | your university credentials, if any |
| Gallica / BnF | site is open; **the SRU API refused anonymous use in my test (HTTP 403)** — request a key | key request is a short form; state purpose |
| Wellcome Collection | API is free; key requested by email | one-line research statement |
| British Library | **Reader Pass — free, online, needs ID + address proof**; some Oriental/India Office material needs a reading-room appointment | bring passport/ID; name the shelfmarks |
| Bodleian | **free reader card**, application with ID/ status; Weston Library stacks need the card only | photo ID; a sentence on the project |
| Warburg Institute | **reader registration**, often a reference; rare books supervised | academic reference or a credible project description |
| SOAS / IIS (London) | reader application with **project description + references** | name the specific collections you want |
| HMML reading room | free account; **some collections need the custodian library's permission too** (two keys) | state the collection and folio range |
| Dar al-Kutub (Cairo) | researcher registration; for foreigners, sometimes a **written permission** | institutional letter, passport, topic |
| Süleymaniye (Istanbul) | reading-room registration; **photography by request, sometimes a fee** | catalogue IDs of the *raml* collections you want |
| Ahmed Baba / Timbuktu | **written permission** via the institute or a partner project | letter stating the manuscripts and purpose |
| Ifá oral corpus (the *ewe* / *ebo* register) | **not a library question** — access runs through a teacher/lineage | a relationship, not a form |
| Encyclopaedia of Islam ("Raml"), Brepols, JSTOR articles | **paid** | university access, or a reading-room visit |

**Verified-from-here vs. to-check-before-you-travel:** every row I fetched this session (IA metadata,
40 text layers, Gallica's HTTP behaviour, HathiTrust, Europeana's key requirement, the four deleted
in-copyright uploads) is `[tested]`. Anything marked `[unverified]` below is a named door with a
described practice — confirm on the institution's own page before booking anything.

## 1. Confirmed by this session [tested]

| Door | What it holds for you | What it asks | How I know |
|---|---|---|---|
| **Internet Archive** (`/metadata`, `/download`) | Everything already in `corpus/`: Agrippa's 4th book + *Of Geomancy* (1655/1783), *Fasciculus geomanticus* (1704, with **Alfagini Quaestiones**), Italian *Geomantia* (1552), four German *Geomantia* books (1704-1747), Hartmann 1889 with **2,048 answers**, Persian *Kitāb-i Surkhāb fī ʿilm al-raml* (1528, via Leiden), *Nuskhah-i raml* (McGill), Arabic *Risāla Ramlīya*, Lal Kitab 1939/1941 (Urdu/Hindi), Prasna Marga / Shatpanchashika / Prashna Chandeshwara (horary question literature), Zulu *Izinyanga Zokubula* (1870), Thorndike vol. 1 | **Nothing to read or fetch public-domain items.** `access-restricted-item: true` in the metadata = borrow-only → **free archive.org account**, 1-hour in-browser or 14-day loan | `scripts/ia_harvest*.py`, `ia_fetch.py` all ran here; 33 + 13 text layers downloaded |
| **Beinecke (Yale) via IA** — `mscodex1918` | Arabic *Sirr al-asrār fī ʿilm al-āthār* + *Shamsīya*: talismanic/lot divination, the neighbouring literature to raml | nothing (public domain, mirrored) | fetched |
| **McGill (Ivanow coll.)** — `McGillLibrary-rbsc_ms-bw-ivanow-0133-18589` | Persian *Nuskhah-i raml* | nothing | fetched |
| **Leiden University** — `ldpd_13892500_000` | the Surkhāb raml text | nothing | fetched |
| **Bayerische Staatsbibliothek via IA** — `BSG_8V821INV2896FA` (Opus geomantiae, 1638), `BSG_8V819INV2894RES_P1` (1552 Italian), `BSG_MS2226` (occult-science ms misc.) | the Latin compendium + an early Italian print + a French occult anthology | nothing | fetched |
| **University of Toronto Scholaris** | Finan, *The Book of the Judgements of Calatarama* (2023, 400 pp, open thesis) — **the single best item found**: translation + tables of the Castilian-Arabic manual | nothing | fetched directly |
| **quest-journal.net mirror** | van Binsbergen, *The astrological origin of Islamic geomancy* (al-Zanātī translation; the 8-Judges theorem; the "16th from I and XV") | nothing | fetched (the publisher's own PDF 404'd, this copy worked) |

## 2. Uncommon doors worth knocking on — what they hold and what they ask

Ordered by likelihood of a real payoff for *hidden-detail* geomancy. `[unverified]` for the terms:
read them on the institution's own page before you plan around them.

**Arabic / Persian / Ottoman raml (the tradition itself)**
- **Dar al-Kutub al-Miṣrīya** (Cairo) [unverified] — national collection of the Cairene printed *raml*
  editions and manuscripts (al-Zanātī's *Kitāb al-faṣl* was printed in Cairo 1320H/1923; van
  Binsbergen reproduces its opening page). Ask: reading-room card for foreigners + written request
  for manuscripts; usually needs an ID, a stated research topic, sometimes an institutional letter.
- **Süleymaniye Yazma Eser Kütüphanesi** (Istanbul) [unverified] — the largest Ottoman *raml*/*kum hesabı*
  holding. Ask: their catalogue is online; manuscripts need a reading-room request; photography often
  needs permission and a fee.
- **Institute of Ismaili Studies Library** (London) [unverified] — strong Arabic scientific/manuscript
  collection (astrology, lots, divination). Ask: reader access typically by application with a project
  description and references.
- **HMML (Hill Museum & Manuscript Library)** [unverified] — digitised manuscript reading room,
  including Islamic and Ethiopian collections. Ask: free registration for the reading room; some
  collections need the mother library's permission.
- **Bibliothèque nationale de France — Gallica / Manuscrits arabe** [partly tested] — Arabic and Latin
  geomancy MSS (the *Estimaverunt Indi* and Hugo of Santalla line live here). The **SRU API answered
  403 anonymously** in my run: it exists but is rate-limited/keyed, so register a key or use the site.
- **Shamela / al-Maktaba al-Shāmila** [unverified] — the big searchable Arabic corpus where *ilm al-raml*
  titles circulate in text form; account needed for full access.
- **Astan Quds Razavi (Iran)** and **Majlis Library** [unverified] — Persian raml and *jafr* texts.
- **Ahmed Baba Institute (Timbuktu)** — West African *raml* in Arabic script; access is by written
  permission through the institute or through projects that have digitised there (HMML,
  Timbuktu Manuscripts Project). For you in Nigeria this is the most *culturally contiguous*
  collection and also the hardest; plan it as a letter + a named supervisor, not a click.

**Latin / European geomancy**
- **Warburg Institute Library** (London) [unverified] — the natural home for magic-and-figures studies;
  needs a reader card (application, sometimes a reference), and rare material is supervised.
- **Bodleian** (Oxford) [tested-ish: their library-cards page exists] — Card readers are free-to-cheap;
  Western MSS require a reader card plus a purpose statement. Broxbourne 84 (1469, astrological
  miscellany) is *their* shelfmark — worth a request for the reading-room images.
- **British Library Reader Pass** [tested: page live] — free pass gets you reading rooms; some
  Oriental/India Office material needs higher approval. Ask for: Royal MSS and the Sloane collections
  (Sloane is where English occult geomancy survives in quantity).
- **Bayerische Staatsbibliothek Digital** [tested via IA] — already gave us four German prints; their own
  portal has more 16th-18th c. *Geomantia* and pamphlet wars (the 1704-1715 defence pamphlets we found
  show how contested the art was - useful for the *theory* of why figures answer).
- **Morgan Library** (NY) [403 to my probe, so treat as application-based] — Latin astrological MSS.
- **Beinecke** (Yale) — already reachable via IA mirrors.

**Horary question-and-answer literature (the "casebook" model, for structure only)**
- **Adyar Theosophical Publishing House** (Chennai) — printed the horary question classics
  (*Prasna Marga*, *Shatpanchashika*), many now sitting openly on IA. [tested for IA copies]
- **Chowkhamba Sanskrit Series Office** (Varanasi) — critical editions of *praśna*/*pratyak* texts.
- **KeralaOriental / Government Oriental Manuscripts** (Trivandrum, Chennai) — *prasna* granthas with
  the "answer the sub-question" machinery; ask for catalogue + reading permission.

## 3. Communities, and the works they keep pointing at

What each person or group actually gives you, and the trail they themselves cite:

- **David Conant (The Digital Ambler)** — the only modern writer publishing the *Arabic* figure names
  and the Ifá correspondence table side by side (that table is now in `kb/figures.yaml`). He also
  states plainly that sharing 16 figures does **not** make geomancy and Ifá behave alike — keep that
  warning attached to the column. His school charges for courses; the blog is free and citation-rich:
  he leads back to Agrippa, to the *picatrix*-adjacent literature, and to Arabic sources by name.
- **John Michael Greer** — *Medieval Methods of Geomancy* (Caduceus 2.2 and 2.3, free at hermetic.com)
  is where the "Way of the Points", "Reconciling the Judge and the Houses", and the *Modo iudicandi
  questiones secundum Petrum de Abano* translation live; he explicitly says his sources are the
  **manuscript** literature — chase his bibliography (Charmasson, Tannery) rather than re-reading him.
- **Stephen Skinner** — the modern standard (*The Oracle of Geomancy*, *Terrestrial Astrology*); his
  own lineage of citation runs to **Charmasson's 1980 study** and the *Estimaverunt Indi*. Buy if you
  can; his books are the map, the manuscripts are the territory. Note: the copy on IA
  (`stephen-skinner-terrestrial-astrology-divina`) is an unofficial upload — do not build on it.
- **Franz Hartmann (1889)** — now *in your corpus*: *The Principles of Astrological Geomancy*, with an
  appendix of **2,048 answers to questions**, and a casting rule that is NOT the shield (points mod 12
  gives the Judge). Read it as a casebook, not as doctrine; it shows how a 19th-c. Theosophist
  reconciled Agrippa with a question-lookup table.
- **Theosophical Publishing Company / Adyar circle** — they printed the "answer-a-question" literature
  (Hartmann, Lal Kitab's Hindi-English line, *Prasna Marga* at B.V. Raman). Their catalogues are the
  fastest way to find more of the genre.
- **B.V. Raman / Indian horary line** — *Prasna Marga*, *Shatpanchashika*, *Prasna Tantra*: not
  geomancy, but the most systematic "sub-question inventory" available (who stole it, which direction,
  which caste/class, which body part, when recovered). `kb/question_inventory.json` borrows their
  *question shapes* and states so explicitly; their answers come from lunar and planetary
  combinations, so **do not** paste their rules onto a figure.
- **Ifá studies** — Wande Abimbola's published corpora (the standard route to *ewe* (taboo) and *ebo*
  (prescription) material), Bascom's *Ifa Divination* (on IA as borrow-only, free account). The
  register you want — "a visitor is coming", "beware of the knife" — is Ifá's *own* genre, not
  geomancy's, and access to the full corpus traditionally runs through an Odu Ifá teacher, not a
  library. Treat that as a relationship to build, not a database to scrape.
- **Zulu / Southern African divination** — Colenso & Bryant, *The Religious System of the Amazulu*
  (1870, in `corpus/raw/ia2`) is a full **bones-divination reading corpus** where each thrown lot has a
  *named* meaning that states a particular ("an informant", "a lurking enemy", "a sickness in the
  house"). It is the closest published analogue to what you described, and it is open. Study its
  *format*, not its cosmology.

## 4. Paywalls — don't pretend these are free

| Item | Why you want it | Cost / route |
|---|---|---|
| M. Charmasson, *Recherches sur une technique divinatoire: la géomancie dans l'Occident médiéval* (2 vol., 1980) | the scholarly edition of the medieval geomancies; Greer, Skinner and Finan all cite it constantly | library interloan; it is not legally online |
| P. Tannery, *Mémoires scientifiques* II (contains *Estimaverunt Indi*, Gerard of Cremona) | the actual Latin texts behind the technique list | old print; some volumes surface on IA/ Gallica — check per volume |
| *Corpus Christianorum / CCSA* editions of astrological texts | critical Latin editions | institutional subscription |
| Encyclopaedia of Islam, art. "Raml" | the standard scholarly summary with manuscript pointers | Brill subscription; a 30-min reading-room visit at a university library works |
| Skinner, *The Oracle of Geomancy* / *Terrestrial Astrology* | the working modern system | buy |
| *Izinyanga Zokubula* reprints / ethnographic series | the bones readings in fuller form | often out of print |

## 5. What I would do next, in this order (cheap to expensive)

1. **Finish the *Fasciculus* Quaestiones.** I pulled 42 rules from 32 pages; the book carries far more
   (leaf range ~440-680). Run `scripts/ocr_pages.py` over the remaining leaves — each page is ~25 s, so
   ~2 hours unattended, and it resumes from cache. That single job more than doubles the casebook.
2. **Translate the 42** (rule text → one-line operational statement, hand-checked against the leaf) and
   grow `engine/questions.py` from 35 sub-questions to whatever the book actually has.
3. **Persian/Arabic raml**: *Kitāb-i Surkhāb* and the *Risāla Ramlīya* are in the corpus as text layers
   that are Arabic/Persian-script; they need `tesseract -l fas/ara` re-OCR of the pages plus a proper
   bidirectional cleanup before any rule can be extracted. Budget a real session, not a side job.
4. **Hindi raml**: *Ramal Pradīpikā*, *Rāmal Prashnottarī* (both in `corpus/raw/ia2`) — same story:
   Devanagari text layers exist but need careful reading; they are *praśna*-shaped, so expect question
   lists more than figure-shields.
5. **Ifá / Zulu register**: build a "named-particulars" layer honestly — each position gets a *named*
   reading that states a fact (the Amazulu model), and mark it as comparative method, not geomancy.
6. **Write to two people** (cheap, high yield): the Finan author (thesis correspondence) about folio-level
   readings of the *Calatarama*; and Conant, about the Arabic-name table's sources. Both have every
   reason to answer a precise question.
