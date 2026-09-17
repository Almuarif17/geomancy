# What this costs you

Short answer: **$0 to build all of it, and money only shows up when people start using it.** Nothing below
is a subscription I can start for you; every paid line has a free path that works today. Figures are 2026
list prices from public pages, checked this session where linked; anything marked *(verify)* I could not
confirm and you should confirm before relying on it.

## Free, now, no card

| what | why it is free | limit you will eventually hit |
|---|---|---|
| Public repo, Issues, Discussions, Releases + assets | GitHub free for public repos | CI minutes are unlimited on public repos; storage soft-cap ~1-2 GB (we are at ~2 MB) |
| jsDelivr CDN for `by_outcome.jsonl`, schemas, types | free for open source | rate limits for huge traffic; fine to millions of reads/day |
| Hugging Face dataset card + a CPU Space as the demo | free tier | Spaces: 1,000 free CPU hours/month, sleeps when idle |
| Zenodo DOI, versioned archive of each release | operated by CERN, free | 50 GB per record (we need ~2 MB) |
| Corpus: archive.org text, Bayerische Staatsbibliothek images, Toronto thesis, Brill/Enc Islam citations | open hosting / free read-only access | some items are *borrow-only* (free account, 14-day loan) — that is a login, not a payment |
| OCR and extraction: Tesseract 5 + PyMuPDF, all local | open source | our own time; a paid cloud OCR (AWS Textract ~$1.50/1,000 pages) is never required here |
| The AI reader: local Ollama with a free open model, or any provider's free tier | open weights | the hosted demo, if you give it to strangers, needs a GPU or a per-token bill — start with "bring your own key" |
| A journal for the methods paper: *Journal of Open Humanities Data* and similar diamond open-access venues | no author fee *(verify for 2026 APC policy)* | editorial time, weeks to months |

## Where money actually appears, and the trigger

| item | cost | only pay when |
|---|---|---|
| Your own domain (optional) | ~$10-13/yr | you want a brand that is not `github.io`; otherwise free subdomains work |
| Hosted API above the free tier (Workers/Render/Neon free tiers first) | ~$5-20/mo | sustained traffic beyond free limits — i.e. after someone wants to pay you |
| Payment processing (Stripe etc.) | no monthly; ~2.9% + 30¢ per transaction | first paying customer. Note: *data and dev tooling* is an ordinary merchant category; **selling readings** is classed high-risk by processors, which is a strong reason to stay on the data/API side of the line |
| Manuscript image fees at a few libraries | ~$0-30 per image, some are free | when a specific folio decides an open question (e.g. Barcelona MS 84.7.4 f.50) |
| Trademark (name/logo) | official fee + agent; in Nigeria via the TM registry, in the US ~$250-350 *(verify current fee)* | revenue exists and someone is trading on your name |
| Legal review of the licence split below | varies | before the first commercial licence is signed |

## What I will not spend your money on

Paid OCR services, paid "occult data" feeds, advertising, a paid repo, or any service that requires a card
to keep the library alive. The design principle of this repo is that it must stay runnable and verifiable
with zero money in it — a buyer who cannot reproduce your numbers has nothing to pay for.

## The real cost is hours, not naira

Rough, from what this session took: grounding/voices layer ~1 day; hosted API + free-tier deploy ~1 day;
TS/WASM package ~1-2 days; wording layer for the 184 Calatarama cells ~2-4 days; one manuscript folio
resolved to transcription ~half a day; each additional tradition added to the corpus ~2-5 days. The
expensive part is *reading*, and it is the part a competitor cannot shortcut either.
