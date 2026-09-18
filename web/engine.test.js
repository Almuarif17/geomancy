#!/usr/bin/env node
/** Prove web/engine.js on all 65,536 casts. No Python required for this gate. */
var E = require("./engine.js");
var r = E.selfCheck();
if (r.casts !== 65536) throw new Error("casts " + r.casts);
if (r.odd_judges !== 0) throw new Error("odd judges " + r.odd_judges);
if (!r.even_population_ok) throw new Error("judge population " + JSON.stringify(r.judge_counts));
var sample = E.cast(["Carcer", "Amissio", "Caput Draconis", "Populus"]);
if (sample.names.length !== 16) throw new Error("shield length");
if (!sample.judge_even) throw new Error("sample judge odd");
if (E.rowValue(1) !== 1 || E.rowValue(2) !== 2 || E.rowValue(3) !== 1) throw new Error("rowValue");
console.log("web/engine.js OK — 65,536 casts, 0 odd Judges, 8 even Judges × 8192");
console.log("sample Carcer,Amissio,Caput Draconis,Populus → Judge " + sample.judge + " · XVI " + sample.reconciler + " · code " + sample.code);
