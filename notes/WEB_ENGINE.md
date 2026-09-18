# Offline / JS engine (started)

`notes/APP.md` refused a second copy of the rules unless it was **ported and proved**.
`web/engine.js` is that port’s first slice: the oracle chart, not the full `deep_read` report.

## Prove it

```bash
node web/engine.test.js
```

Must print 65,536 casts, 0 odd Judges, eight even Judges at 8,192 each.

Next CI step (not in this commit): run the same mothers through `engine/oracle.py` and
require identical XVI / Via Puncti / projection / Part of Fortune / motus.

Until that harness lands, treat `web/engine.js` as **preview**, not a release artefact.
