# LICENSING — three layers, so "free" and "not yours to take" are both true

The whole repo used to be one licence, which meant either everything was free (bad for a business) or
everything was restricted (bad for adoption, and impossible anyway: the underlying texts are public domain).
So the repo is now layered, **by file, not by intention** — a layer is enforced by
`library/tools/check_licence_scope.py`, which fails the build when a tracked path is undeclared or claimed
by two layers.

```scope
L1-code=engine/,library/tools/,scripts/,server/,tools/,data/,examples/,library/schema/,types/,library/dataset/openapi.yaml,registry/,corpus/,.github/,Makefile,SETUP.md
L2-cc0=library/dataset/core_facts.json
L3-curated=kb/,library/dataset/index/,library/dataset/shards/,library/dataset/tables/,library/dataset/bundles.json,library/dataset/manifest.json,library/dataset/evaluation.json,library/README.md,notes/,docs/,README.md,FINDINGS.md,CHANGELOG.md,PLAN.md,LICENSE-DATA
```

| layer | licence | what it is | what you may do |
|---|---|---|---|
| **L1 code** | MIT | the engine, extractors, gates, schemas, generated types, the OpenAPI contract, fixtures, examples | use, copy, modify, sell software built on it |
| **L2 core facts** | CC0 | `library/dataset/core_facts.json`: the figure bit patterns, the house numbering, our routing table, and the consequences of the arithmetic over all 65,536 casts (attainable Judges, parity law, priors, surprisal) | anything, including commercial, no permission, attribution requested not required |
| **L3 curated layer** | CC BY-NC 4.0, **plus a separate commercial licence on request** | every translated ruling, every voice row, every gloss, the adjudication and gap notes, the outcome bundles, the findings | read, study, cite, share with attribution, non-commercial use; a paid or revenue-bearing product needs a licence |

## Reading it as a developer

- Building a free or research tool? Use everything. L1 and L2 need nothing from you beyond honesty in
  attribution; L3 needs a credit line.
- Building a paid app, a subscription, or anything with ads or in-app purchase? You need an **L3 commercial
  licence**. It is not expensive, it is not per-seat-surveillance, and what you get for it is the right to
  ship our curated text plus the version-pinned data, an attribution block you can paste, and a say in what
  we add next. Open an Issue titled "commercial licence" with what you are building.
- Republishing the data as a dataset, mirror, model fine-tune corpus or "free API of your own"? That is L3
  redistribution: attribution required, non-commercial unless licensed, and **no removing the citations**.
  A mirror that strips `locator` and `authority` turns sourced claims into folk wisdom — that is the one
  thing we will always object to, because the citations are what make the data worth anything.

## What the underlying sources are

The source texts are public domain or openly deposited; the *rights in our selections, translations,
transcriptions and annotations* are what these layers allocate. `LICENSE_POLICY.md` governs what may enter
the dataset at all (Bucket A/B/C) and is the stricter of the two: if the policy says no, no licence here
overrides it. Living-tradition material is not in this repo and not for licensing without the lineage's
consent — see `LICENSE_POLICY.md`, "Special case".

## The part that is not a licence, and should not be mistaken for one

Nothing here stops a competitor forking the public repo and shipping it. Cease-and-desist in this niche is
reputationally expensive and rarely worth it. The plan is different and it is in `docs/IP_STRATEGY.md`:
keep the machine (pipeline, gates, freshness, provenance, the audit of AI output) more valuable than any
snapshot, and make attribution the thing a copy cannot remove without destroying its own credibility.

Prose under `docs/` is L3 (it is argument and adjudication, not plumbing), but every *contract* artefact an
app has to embed - `types/geomancy.d.ts`, `library/schema/*.json`, `library/dataset/openapi.yaml` - is MIT,
because a client should never inherit a licensing question by including a type file. `LICENSE-DATA` is a
pointer to this file from the version of the repo that mis-licensed the dataset as plain CC BY.
