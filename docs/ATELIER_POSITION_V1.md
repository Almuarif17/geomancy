# Atelier position-reading service v1

This is an additive **deterministic** service for one selected chart position. It is not an applet change, a chatbot, a predictive guarantee, or a production-hosting plan. The existing chart arithmetic remains the source of truth; no model key or network connection is needed.

## Local run

Install the repository requirements (or at minimum PyYAML), then start the existing reader locally:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python app/server.py --host 127.0.0.1 --port 8044
```

The new endpoint is `POST http://127.0.0.1:8044/api/v1/read-position`. It is model-off; `model_called` is always `false`. Do not expose this research HTTP server to the public internet without deployment-specific authentication, rate/request limits, timeouts, privacy controls and a commercial-rights review.

## Contract

Request exactly four canonical Mothers in their supplied order and an integer `selected_position` from 1 through 16. The service derives every figure and pattern itself. A client cannot supply a Judge, chart, evidence record, claim, rights profile, or model instruction. Optional `confirmed_topic` must be a key in `kb/houses.yaml`'s `question_to_house`. An explicitly selected topic takes precedence over optional `question` wording. A raw question is only inspected locally for a conservative suggestion; it is not returned, logged as part of the reading, or sent to a model. Suggested intent is not confirmed and does not trigger a topic-specific ruling. Ambiguous or unrecognized wording still receives a usable general selected-position reading.

```sh
curl -sS http://127.0.0.1:8044/api/v1/read-position \
  -H 'content-type: application/json' \
  -d '{"mothers":["Carcer","Amissio","Caput Draconis","Populus"],"selected_position":7,"confirmed_topic":"marriage","locale":"en"}'
```

The response follows [`../types/atelier-position-v1.schema.json`](../types/atelier-position-v1.schema.json); the OpenAPI operation is in [`atelier-position-v1.openapi.yaml`](atelier-position-v1.openapi.yaml). Sections label arithmetic, attributed source claims, editorial glosses and tentative applications separately. `evidence[].scope` is one of `selected_position`, `related_position`, `general_figure`, or `multiple_scopes`; a source about a related house is never presented as the selected tile's ruling. `gaps` name unsupported exact position/figure records. `audit_status` reports the existing grounding audit; audit failure is fail-closed (503). `revisions` fingerprints the code and source dataset used.

### Position identity and court boundary

Numeric positions, not figure names, identify a selection. I–IV are ordered Mothers; V–VIII are transposed Daughter rows; IX–XII are derived by pairwise addition; XIII and XIV are the right and left witness as displayed by Atelier; XV is the Judge; XVI is one Reconciler/Sentence derived from Judge + Mother I. The upstream `engine/ground.py` uses opposite legacy witness-side labels. The v1 adapter translates only at its boundary and does not rename legacy fields. XVI is never counted as two positions or two pieces of evidence.

### Tested examples from the pinned chart fixture

`data/fixtures/atelier_position_v1.json` fixes all sixteen names and patterns for `[Carcer, Amissio, Caput Draconis, Populus]` and is checked against Python and both JS engines. On this chart:

- Position VII is Conjunctio, pattern `[2,1,1,2]`; the exact Calatarama source record is `figure_in_house:Conjunctio:7:calatarama`, locator `f.47v (house VII)`.
- Position II is Amissio; its exact record is `figure_in_house:Amissio:2:calatarama`, locator `f.26v (house II)`.
- Position XV is also Conjunctio, but it is a Judge role, not VII. The VII source is not labeled as a Judge ruling. Since no role- and condition-specific Judge evidence is established by the current contract, the packet reports a court gap. A separately labeled related VII record can appear when the confirmed topic is marriage; it remains `related_position`.
- Carcer at I has general figure notes but no permitted exact figure-in-house ruling in the shipped evidence. The result reports that gap rather than borrowing a ruling from another position.
- The Puer fixture surfaces the distinct Calatarama and Agrippa planetary attributions as an `unresolved_comparison`; it preserves each authority and does not decide the conflict from polarity labels. Puer/Puella selections also carry the documented pattern-label conflict: this build follows the Britannica/Golden Dawn mapping in `kb/figures.yaml`, while the cited Digital Ambler alternative swaps the two names. The dots and arithmetic do not change.

Change `confirmed_topic` from `marriage` to `wealth_money` on the same chart and position VII stays Conjunctio with the same pattern. The focus changes from house VII to II; the Amissio/II record, if present, is labeled `related_position`. The service does not recast.

## Topic routing, language and rights

Supported explicit topics are drawn from `kb/houses.yaml` rather than a second invented catalog. The included English phrase matcher is intentionally limited: a single match produces `suggested`, multiple candidate matches produce `needs_confirmation`, and unrecognized wording returns `general`. “Not a marriage question; I am asking about our savings” suggests `wealth_money`; the caller must confirm it before a topic-specific packet is assembled. “Should I accept the job or move house?” offers choices and still returns the general reading. The applet can avoid uploading the original question entirely by sending only a reader-confirmed topic key.

English is currently the only available language. A different `locale` receives `available_locale: "en"` and a `fallback_reason`; no translation is fabricated. The server chooses its rights profile (`research` today); it is not accepted from the request. Cite-only/summarize records are references only and do not gain reconstructed quotations. Evidence IDs are deduplicated; authority, work, transmission, locator and permission metadata remain attached. A future commercial build must apply the per-work rules in `LICENSING.md` and `LICENSE_POLICY.md`; this research endpoint is not a commercial grant.

## Examples and gates

- Request bodies: [`examples/atelier_position_v1_requests.json`](../examples/atelier_position_v1_requests.json)
- Captured deterministic responses: [`atelier_position_v1_responses.json`](atelier_position_v1_responses.json)
- Run the example client against a live local service: `python examples/atelier_position_v1_client.py`
- Targeted contract tests: `python engine/test_position_reading.py`
- HTTP integration tests: `python app/test_app.py`
- Project tests: `make test`

No optional AI writer is implemented in this milestone. No support is claimed for arbitrary natural-language understanding, non-English reading, unverified traditions, or conditioned Judge/cofigure answer tables. The applet interface has not been modified.
