# registry/works.jsonl - the source control plane

One line per work. This file, not a folder of PDFs, is what makes the library maintainable:
`engine/` and `kb/` reference works by `id`, and `library/tools/sync_corpus.py` decides - mechanically -
whether a work's text is fetched in full, fetched for note-taking, or never fetched at all.

| field | meaning |
|---|---|
| `id` | internal key; appears in `kb/*.json` as `work`, and in every dataset passage's `work` |
| `stable_id` | **persistent** locator: archive.org identifier, ARK, handle, DOI or shelfmark - never a bare web URL |
| `licence_bucket` | `A` public domain / open, `B` cite only, `C` never use (see `LICENSE_POLICY.md`) |
| `disposition` | `full` = text may be downloaded into `corpus/` and extracted; `summarize` = read, take notes, no redistribution; `cite` = reference only; `drop` = do not fetch at all |
| `why_trusted` | the host's durability claim, in one line - so a future maintainer knows whether to rely on it |
| `retrieval` | the API/URL recipe, so fetching is scripted and repeatable rather than manual clicking |

**Why these hosts are trusted for years:** Internet Archive items are addressable by identifier,
mirrored, and have survived 25+ years with the same URL shape; Gallica addresses by **ARK**
(`ark:/12148/...`), which is a handle system and survives redesigns; institutional repositories
(Toronto scholaris, Leiden, McGill) use handles/IIIF; BSB and other German libraries expose IIIF manifests;
DOIs cover the commercial scholarship. Everything in `registry/` is therefore addressed by identifier plus
an API recipe - so `sync_corpus.py` can rebuild the whole corpus from scratch after a disk loss, and
`--check` can tell you in one run which source has gone quiet.

**Uploads are not admitted silently.** Anything dropped into `corpus/inbox/` goes through
`library/tools/triage.py`, which computes a hash, proposes a bucket and disposition with reasons, and
appends to `registry/proposed.jsonl`. A human edits that line into `works.jsonl` - the tool never does.
