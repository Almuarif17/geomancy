# Public, and still not copyable

Your instinct is right that a public repo is bad for business — but the fix is not secrecy. Data in a
public repo **will** be copied; what cannot be copied is the machine that produced it, the right to be
cited, and the licence terms on the parts people actually want. Here is the shape.

## 1. Split the licence into three layers (this is the load-bearing decision)

| layer | what it holds | licence | why |
|---|---|---|---|
| L1 code | `engine/`, `library/tools/`, `scripts/`, schemas | **MIT** | you want developers to depend on it, not to negotiate with you |
| L2 core facts | figure bit patterns, house names, the derived statistics of all 65,536 casts, the registry of works | **CC0** | zero-carrying-cost, and it is the layer that gets cited; you cannot sell what anyone can regenerate, so give it away and own the standard |
| L3 the curated layer | `kb/voices.jsonl`, the grounded readings, plain-language glosses, the adjudication notes, outcome bundles | **CC BY-NC 4.0, with a separate commercial licence on request** | this is the paid thing: NC means a company shipping it in a revenue app must talk to you; attribution means every copy still advertises you |

Today the whole repo is MIT (`LICENSE`), which puts L3 in the public domain for commercial use. Changing
that is your call, not mine to make silently: it needs `LICENSE_DATA.md`, a `LICENSING.md` with the two
tiers, and a line in the README. If you say go, I will write the files and the migration note.

Two alternatives, and when to prefer them: **ODbL** (database right + share-alike) if you would rather
force any derivative to stay open than sell licences; **CC BY 4.0 for L3 as well** if the goal is maximal
adoption and citations instead of revenue. Do not pick "all rights reserved": a closed dataset in this
field gets ignored and then independently reinvented, which is the worst outcome.

## 2. Sell the parts a clone cannot have

A clone gets a **snapshot**. These are not snapshots:

- **The pipeline.** 23 registered works, `sync_corpus.py` re-fetching and verifying, per-work licence
  decisions, 15 extractors, 31 gates including the ones that catch our own tooling lies. Anyone can copy
  1,408 voices; nobody can copy the fact that they are reproducible from `make sync && make build`.
- **Freshness with proof.** A release every few weeks with a CI badge and `verify_release.py`. Consumers of
  a stale fork have no way to show *their* data is right; yours is one command.
- **The audit of AI output.** `engine/ground.py validate()/score()` is the exam every divination app now
  needs and none of them can build in a weekend. Free data + paid exam is a real business; free data alone
  is not.
- **Access you personally have.** Borrow-only archive.org items, library folio requests, and — decisively —
  the living *ʿilm al-raml* / sand-divination lineages reachable from where you are, collected with
  consent. That is not a scraping job; nobody in Berlin or San Francisco can do it.
- **Trust artifacts.** A DOI, a methods paper, a named editor, a public corrections policy. In scholarship
  and in procurement, the citation is the moat.

## 3. Free defences worth turning on

- **Fingerprint the build.** `manifest.json` already hashes every shipped file; publish a canonical
  digest of the voices ordering. If someone republishes our rows, that digest and our editorial phrasing
  travel with them and it is trivial to demonstrate provenance.
- **Keep distinctive editorial notes in your own voice** (already true: `editorial_notes`, the gap
  explanations, the "we refuse to guess" rulings). Generic data is untraceable; an argument is a signature.
- **Version everything, name versions.** `v0.2.3` beats "some CSV on someone's blog" because a consumer can
  pin it, cite it and diff it.
- **A visible corrections path** (Issues + Discussions + a `docs/RESEARCH_LEDGER.md` entry per fix). A
  dataset that admits and fixes errors is worth paying for; one that never has them is assumed to hide them.
- **Do not** plant hidden "trap" rows without deciding to: it is a real technique (dictionaries do it), but
  it must be disclosed in the licence doc to be useful in a dispute.

## 4. What stays out of the public repo

Commercial licence drafts; anything a rights-holder asked us to keep as citation-only (already enforced by
the licence gate); contact details or field-recording material without written consent; your API keys; and
the ranking/prompt tuning for the reader product (publish the *evaluation* of it, keep the tuning).

## 5. The one-line frame

Do not sell information — it is free and increasingly worthless. Sell **the ability to be believed**: a cast
that any engine can reproduce, a rule any test can execute, a sentence any reader can trace to a named
author on a named folio, and an AI reading that fails automatically the moment it says more than its
sources do.
