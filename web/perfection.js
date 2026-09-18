/**
 * Modes of perfection, house aspects, company kinds.
 * Uses GeomancyEngine. Chart math stays in engine.js.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./engine.js"));
  else root.GeomancyPerfection = factory(root.GeomancyEngine);
})(typeof self !== "undefined" ? self : this, function (E) {
  "use strict";
  var PAIRS = [[1,2],[3,4],[5,6],[7,8],[9,10],[11,12]];
  var ANG = {1:1,4:1,7:1,10:1}, SUC = {2:1,5:1,8:1,11:1}, CAD = {3:1,6:1,9:1,12:1};

  function neighbors(h) {
    var n = [];
    if (h > 1) n.push(h - 1);
    if (h < 12) n.push(h + 1);
    return n;
  }
  function aspect(a, b) {
    var d = Math.abs(a - b);
    d = Math.min(d, 12 - d);
    if (d === 0) return "same";
    if (d === 1) return "adjacent";
    if (d === 2) return "sextile";
    if (d === 3) return "square";
    if (d === 4) return "trine";
    if (d === 6) return "opposition";
    return "unaspecting";
  }
  function complement(p) { return p.map(function (v) { return v === 1 ? 2 : 1; }); }
  function samePat(a, b) { return a && b && a.join(",") === b.join(","); }

  function companyKind(pa, pb, planetOf) {
    if (samePat(pa, pb)) return "simple";
    if (planetOf && planetOf(pa) && planetOf(pa) === planetOf(pb)) return "demi_simple";
    if (samePat(complement(pa), pb)) return "compound";
    if (pa[0] === pb[0]) return "capitular";
    return "none";
  }

  function perfection(houses, qHouse, planetOf) {
    qHouse = qHouse || 7;
    var h = houses; // 16 patterns, index 0 = house I
    var q1 = h[0], qq = h[qHouse - 1];
    var modes = [];
    if (samePat(q1, qq)) modes.push({ mode: "occupation", conf: "HIGH" });
    neighbors(1).forEach(function (n) {
      if (samePat(h[n - 1], qq) && n !== qHouse) modes.push({ mode: "conjunction", by: "querent_passes", house: n, conf: "HIGH" });
    });
    neighbors(qHouse).forEach(function (n) {
      if (samePat(h[n - 1], q1) && n !== 1) modes.push({ mode: "conjunction", by: "quesited_passes", house: n, conf: "HIGH" });
    });
    var i;
    for (i = 0; i < 11; i++) {
      if (samePat(h[i], q1) && samePat(h[i + 1], qq) && i !== 0 && (i + 1) !== (qHouse - 1))
        modes.push({ mode: "mutation", houses: [i + 1, i + 2], conf: "HIGH" });
      if (samePat(h[i], qq) && samePat(h[i + 1], q1) && i !== 0 && (i + 1) !== (qHouse - 1))
        modes.push({ mode: "mutation", houses: [i + 1, i + 2], conf: "HIGH" });
    }
    var nQ = neighbors(1), nS = neighbors(qHouse), seen = {};
    nQ.forEach(function (a) {
      nS.forEach(function (b) {
        if (a === b) return;
        if (samePat(h[a - 1], h[b - 1]) && !samePat(h[a - 1], q1) && !samePat(h[a - 1], qq)) {
          var k = E.nameOf(h[a - 1]) + ":" + a + ":" + b;
          if (seen[k]) return;
          seen[k] = 1;
          modes.push({
            mode: "translation",
            figure: E.nameOf(h[a - 1]),
            houses: [a, b],
            planet: planetOf ? planetOf(h[a - 1]) : null,
            conf: "HIGH",
            note: "third party; colour by planet/sign in kb/astrology.yaml"
          });
        }
      });
    });
    var companies = PAIRS.map(function (pair) {
      var k = companyKind(h[pair[0] - 1], h[pair[1] - 1], planetOf);
      return { houses: pair, kind: k, conf: k === "none" ? null : (k === "simple" ? "HIGH" : "MED") };
    }).filter(function (c) { return c.kind !== "none"; });

    var asp = aspect(1, qHouse);
    return {
      quesited_house: qHouse,
      modes: modes.length ? modes : [{ mode: "no_relation", conf: "HIGH" }],
      aspect: { name: asp, conf: "HIGH", use_when: "no_relation" },
      house_strength: {
        querent: ANG[1] ? "angular" : "succedent",
        quesited: ANG[qHouse] ? "angular" : (SUC[qHouse] ? "succedent" : "cadent")
      },
      company: companies
    };
  }

  return { perfection: perfection, aspect: aspect, companyKind: companyKind, PAIRS: PAIRS };
});
