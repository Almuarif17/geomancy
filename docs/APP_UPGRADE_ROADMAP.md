# Tellus Loquens — app upgrade and “make it magical” plan

**Status:** living product plan, written against the Android/mobile app and reader in this repository.  
**Current baseline:** mobile app source is `app/mobile.html`; the Android shell packages that same source. The GitHub Actions APK is a sideload/test build, not a store release.  
**Current branch work:** `94f998d` adds research discovery and optional AI study notes; the follow-up chart-weave implementation is recorded in the next commit.  
**Not a claim:** this document is not a promise that all proposed features are already implemented, nor that every source is licensed for commercial redistribution.

## The product in plain terms

Tellus Loquens should feel like an instrument for exploring a geomantic chart, not a random fortune-text generator with occult decoration. A user brings a question, casts or enters four Mothers, watches the complete shield emerge, and can follow how each later figure is derived. The reading should then connect the chart to the question and to named historical authorities, while making the boundary between arithmetic, an author's statement, editorial interpretation, and uncertainty unmistakable. The magical feeling should come from attention, ceremony, pattern, sound and meaningful discovery; it must not come from concealing how a result was produced.

There are three product promises to hold together. **Wonder:** the interaction feels memorable and alive. **Intellectual honesty:** every historical claim can be traced to a source, edition and locator, and missing evidence remains visible. **Practical usefulness:** the app works on an ordinary phone, is understandable to newcomers, and remains useful offline for the chart operations it actually carries. If one promise is traded away, the product becomes either dry scholarship, beautiful misinformation, or a fragile demo.

## What is there now, and what “upgraded” means

The starting repository already had a substantial geomancy dataset and reading engine, a mobile casting interface, chart/shield views, reading and proof surfaces, saved charts, and an Android WebView shell. The engine's source and tests are the authority for the geomantic calculations; the mobile JavaScript chart code is used for offline chart arithmetic and is tested against the reference implementation. The app already had substantial detail, so the recent upgrade did not create geomancy from nothing.

The `0.3.1` branch work adds a **Research desk** to the web reader and mobile app: catalogue discovery for Internet Archive, public GitHub repository search, GitHub README previews, and a device-local shelf of candidate leads. It also adds an **opt-in AI study note** that is separate from the audited reading, plus the Android bridge's longer wait for that request. These features help users discover and reflect; they do not automatically import books, verify sources, perform OCR, or make the corpus commercially distributable. GitHub Actions built and checked a sideload APK, but the product still needs its release, rights, and quality work before it is responsibly called sellable.

The current implementation adds a visual chart-weave in the shield: an animated, tappable map of how the four Mothers feed the Daughters, Nieces, Witnesses, Judge and Reconciler. It makes the derivation legible as an object the user can explore, and it explicitly labels itself as arithmetic rather than an interpretation. This is a first concrete “more magical” improvement, not the completion of the larger experience described below.

## Internet Archive: the important limitation and the honest path

The present app does **not read the contents of Internet Archive books**. Its Archive search calls Internet Archive's public advanced-search catalogue and asks for fields such as identifier, title, creator, date, description and licence URL. The result card is metadata about an item—a discovery lead—not the book's OCR text, searchable pages, verified edition, or a licence decision. The app currently does not fetch the book's files or display its pages. Your concern is correct: seeing a title in search results is not the same as reading what is inside it.

An Archive item can have several different file/access situations. It may offer an OCR or text layer (often a DjVu-derived `.txt` file), page images or a PDF from which text must be recognized, a borrow-only scan, or a mixture. A useful research workflow first obtains the item's metadata and file list, identifies which exact file is the text layer and whether the item is actually accessible, then reads or extracts a small relevant range. If a usable text layer exists, it can be searched immediately, but old OCR can mistake letters, split columns, lose tables, or assign the wrong page. If only images are available, OCR software must be run on those scans. Our repository already has acquisition/OCR tooling under `scripts/` (including `scripts/acquire.py`, `scripts/ocr_ingest.py`, `scripts/ocr_pages.py` and `scripts/ocr_pipeline.py`) and work-specific extractors. That is **research tooling in the source repository**, not an OCR feature wired into the current mobile Research tab.

The correct workflow is therefore not “search, trust the snippet, and add it to the app.” It is: (1) identify the exact edition and item identifier; (2) inspect metadata, files, date, creator, access status and rights statements; (3) obtain only files allowed by their access terms; (4) use an existing text layer where useful, or OCR page images when necessary; (5) record OCR engine, language, page/folio mapping and confidence; (6) compare every passage or table used in a reading against the page image, especially early-print blackletter, Latin/French long-s, columns and geomantic grids; (7) retain raw OCR separately from corrected transcription; (8) have a human verify the extracted claim and locator; and (9) apply the repository's licence/provenance gates before distributing any text or derived editorial work. OCR is a way of making an image searchable; it is not evidence that the transcription is accurate, nor permission to reproduce the book.

Borrow-only material must be used through the Archive's permitted loan process; the app must not bypass lending controls or scrape restricted files. A free public-domain scan can still have complex edition, scan-host, or rights facts that deserve checking. A modern translation may be copyrighted even where the original text is public domain. Do not upload full scans, OCR text, or a book-derived dataset to the app merely because the item is viewable online. Until an ingestion/review workflow exists, the Archive feature should be described as **catalogue search and saved leads only**. This plan recommends making the distinction visible in the UI and adding an explicit “Open item / inspect files / OCR & verify” research workflow only after access and rights review.

## Different product opinions, and the recommendation

### The ritual-first opinion

A ritual-first designer would argue that the app must make the moment of casting feel special before adding more research controls. A quiet opening, a question-setting pause, a tactile cast, and a paced revelation of the chart can make a phone interaction feel like a deliberate practice rather than a form. That is a strong design argument: emotional pacing can create meaning and memory, and the current ability to cast by sand, taps, rows or holding already offers a foundation. Its danger is that ceremony can become theatrical friction, especially for a user who wants to inspect a known chart quickly. Keep the ritual optional, compact, respectful, and skippable; do not make sound, animations, or a forced “mystic” voice the price of access.

### The scholar-first opinion

A scholar would argue that the most magical thing is being able to travel from a figure to the actual witness in a historical source: edition, page, quotation where legally allowed, variant reading, and an explanation of OCR uncertainty. A well-curated primary-source experience would distinguish the app from generic AI divination and create lasting trust. This is also the most labor-intensive route. Some works have poor scans, incomplete text layers, borrowing restrictions, difficult scripts, and no clear redistribution right. Publishing a source explorer before we can actually verify its contents risks giving metadata the appearance of scholarship. Build careful ingestion and evidence review first; release material in small, audited, rights-cleared batches rather than promising that the entire Archive is “in the app.”

### The AI-first opinion

An AI-first product might put a fluent, personalized reading at the center and use a large model to weave figures into a long narrative. This can feel immediately expressive and may help a novice understand relationships. But a model can blend traditions, invent historical support, misread an OCR snippet, or turn a sparse source into false confidence. It also creates hosting costs, privacy concerns, network dependence and possible exposure of sensitive questions. AI should remain an optional **commentary layer**, with evidence labels linked to claims the app itself already knows; it should not author the audited verdict, silently add sources, or be necessary to use the core app. Offer a local model path where feasible and disclose that hosted models may charge and receive the supplied chart/evidence.

### The recommended synthesis

Lead with ritual and visual chart exploration, anchor every historical statement in the scholarly evidence layer, and use AI only as an explicitly labeled optional guide to connections already present. Do not make the app sound certain when the underlying library is uncertain. Let the user choose a voice—plain, scholarly, reflective or poetic—while keeping the same cited claims and visible gaps. A poetic mode changes cadence and metaphor, not the source record or the result of the chart arithmetic.

## What to do, in order

### 1. Finish the chart as an explorable object

The chart-weave is the first step: make every derivation visible and tappable. Next, synchronize the weave with the shield so selecting a node highlights its shield cell, and selecting a shield cell reveals its parents and children. Add a reduced-motion mode, screen-reader descriptions, contrast checks, and a compact layout that works at small widths. Preserve a simple table/ledger fallback: the diagram is a second way to understand the chart, never the only way. Add explanatory copy for the exact construction rules so “magical lines” do not imply a historical relationship the engine has not established.

### 2. Build a guided reading journey

After casting, guide a user through three optional stages: **the figure** (the chart and its court), **the question** (which house or houses are relevant and why), and **the evidence** (what named sources support, conflict with, or do not answer). Each stage should have an expressive visual transition, a short human-readable explanation, and an explicit “show the working” path. Give experienced users a “skip to full shield” action. Save the cast and question together so revisiting a reading preserves context. Avoid claiming fate, certainty, or predictive validity; phrase conclusions as readings in a documented tradition.

### 3. Make interpretive voices explicit

Offer several presentation voices rather than letting a single prose style imply objective certainty. **Plain** should prioritize short, direct wording. **Scholarly** should foreground provenance, variants and method. **Reflective** can ask the user questions and surface tensions. **Poetic** can be lyrical but should be labeled as an expressive rendering, not a quotation or historical authority. All modes must be grounded in the same structured reading and evidence records. Each paragraph should let a user distinguish engine calculation, sourced statement, editorial synthesis and AI-generated commentary. A missing source should remain a named gap in every voice.

### 4. Upgrade source reading from leads to verified evidence

Keep search results explicitly labeled as leads. Design a separate “Open research lead” screen to inspect Archive metadata and file availability, present access terms before any download, and allow the researcher to choose an available text layer or selected scan pages. Do not silently run whole-book OCR on the phone: that is costly, slow, battery-intensive, and unreliable on historic type. Use the existing Python acquisition/OCR tools on a research workstation or controlled server, then make the mobile client show status and verified extracts. For each extracted passage, retain the Archive identifier, exact filename, edition metadata, page image link, printed folio, digital page, OCR engine/version/language, confidence or uncertainty note, correction history, reviewer, licence/access decision and a cryptographic hash of the input. The phone can then review a rights-cleared, human-checked excerpt without pretending the catalogue snippet is the source.

### 5. Improve AI without letting it counterfeit scholarship

Turn the AI note into selectable “reading lenses” (for example, connective, beginner's guide, or reflective questions) and allow the user to choose a tone. Pass only the current chart plus already-grounded claim identifiers/text needed for that request. Have the endpoint return a structured response: prose segments, evidence IDs for each segment, and explicit interpretation labels. Validate evidence IDs against the supplied set before rendering; mark unsupported sentences as ungrounded or reject them. Keep a “show the evidence” control next to each section. Make local versus hosted model status, privacy implications, and possible hosted cost clear before the first request. Keep a no-AI path fully complete.

### 6. Make research leads usable without endorsing them

Add separate metadata fields for “not reviewed,” “edition checked,” “access checked,” “rights checked,” “OCR/transcription checked,” and “accepted into corpus.” These should be researcher annotations, not automated declarations. Provide a one-tap link to the Archive item and, when authorized, its individual files; do not imply that README previews or stars make a GitHub project reliable. The app's shelf is local today; a later export/import format should be stable, documented and useful for a curator's review queue. Do not auto-import from GitHub or the Archive into the knowledge base.

### 7. Prepare a real product release

Before a paid/store release, audit the licensing layer by layer, resolve commercial permissions for curated knowledge, produce a production signing key securely, choose a stable application ID and upgrade path, test installs and upgrades on real devices, review the current Android target SDK and store policies, write clear privacy disclosures, and decide who operates the AI/server endpoint. Add crash-free offline behavior, accessibility and small-screen checks, a real-device test matrix, a release changelog, backups/restore for user charts, and an account/data-deletion policy if accounts are ever introduced. Keep private signing material out of Git and chat. A successful CI APK verifies assembly; it does not certify these release requirements.

## Acceptance tests for the finished experience

A new user can cast without needing AI or a network, understand how the shield was built, and reach a sourced explanation without being forced through an ornate ritual. A returning practitioner can enter or revisit a chart quickly. Every line identified as historical evidence links to a source record and exact locator; any OCR-derived text states its transcription status and can be checked against an image. Archive catalogue search never presents metadata as book contents, and restricted lending material is not fetched or redistributed. AI commentary is visibly separate, uses only validated evidence references, and remains optional. The diagram has an accessible non-animated alternative. A commercial build contains only material cleared for that use, is signed with an owner-controlled production key, and has passed current Android release requirements.

## Practical next milestones

1. **Now:** test the chart-weave on a phone-sized browser and confirm it matches the established 16-place chart construction; refine the animation and accessible fallback.
2. **Next:** produce the guided reveal and user-selectable reading voices, keeping the current proof route intact.
3. **Research milestone:** design and implement a review-only Archive item inspector that states plainly “catalogue metadata, not book text,” then connect the existing OCR workflow only for authorized, selected items.
4. **Evidence milestone:** validate structured AI evidence references and add an explicit disclosure for local/hosted model behavior.
5. **Release milestone:** clear commercial rights, update target SDK/toolchain, establish production signing, and test a genuine store-candidate build.

These milestones should be accepted separately. A visually magical interface is worth making, but the trustworthy source pipeline and the legal release checklist must not be hidden behind the atmosphere.
