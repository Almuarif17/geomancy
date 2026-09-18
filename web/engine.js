/**
 * Runtime geomancy engine (JavaScript).
 *
 * Python `engine/oracle.py` and `engine/deep_read.py` remain the reference.
 * This file is the copy the phone is allowed to run. It must agree with the
 * oracle on every one of the 65,536 casts before a release may ship it
 * (see docs/APP_ARCHITECTURE.md and notes/APP.md "offline engine" backlog).
 *
 * Chart arithmetic only. No passages, no guesses, no network.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.GeomancyEngine = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Patterns from library/dataset/core_facts.json (CC0).
  const FIG = {
    "Acquisitio": [2, 1, 2, 1],
    "Albus": [2, 2, 1, 2],
    "Amissio": [1, 2, 1, 2],
    "Caput Draconis": [2, 1, 1, 1],
    "Carcer": [1, 2, 2, 1],
    "Cauda Draconis": [1, 1, 1, 2],
    "Conjunctio": [2, 1, 1, 2],
    "Fortuna Major": [2, 2, 1, 1],
    "Fortuna Minor": [1, 1, 2, 2],
    "Laetitia": [1, 2, 2, 2],
    "Populus": [2, 2, 2, 2],
    "Puella": [1, 1, 2, 1],
    "Puer": [1, 2, 1, 1],
    "Rubeus": [2, 1, 2, 2],
    "Tristitia": [2, 2, 2, 1],
    "Via": [1, 1, 1, 1]
  };
  const BYP = {};
  Object.keys(FIG).forEach(function (n) { BYP[FIG[n].join(",")] = n; });
  const NAMES = Object.keys(FIG).sort();
  const ROMAN = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV","XVI"];
  const EVEN_JUDGES = ["Acquisitio","Amissio","Carcer","Conjunctio","Fortuna Major","Fortuna Minor","Populus","Via"];

  function add(a, b) {
    return [0, 1, 2, 3].map(function (i) { return ((a[i] + b[i]) % 2 === 0) ? 2 : 1; });
  }
  function rowValue(taps) {
    var n = Number(taps) || 0;
    if (n < 1) n = 1;
    return (n % 2 === 0) ? 2 : 1;
  }
  function nameOf(pat) { return BYP[pat.join(",")] || "??"; }
  function idxOf(pat) {
    return pat.reduce(function (s, v, i) { return s | ((v === 1 ? 1 : 0) << (3 - i)); }, 0);
  }
  function rowsOf(i) {
    return [0, 1, 2, 3].map(function (b) { return ((i >> (3 - b)) & 1) ? 1 : 2; });
  }
  function chartCode(M) {
    return M.map(function (r) { return idxOf(r).toString(16).toUpperCase(); }).join("");
  }

  function castFromPatterns(M) {
    var D = [0, 1, 2, 3].map(function (r) { return M.map(function (m) { return m[r]; }); });
    var N = [add(M[0], M[1]), add(M[2], M[3]), add(D[0], D[1]), add(D[2], D[3])];
    var W = [add(N[0], N[1]), add(N[2], N[3])];
    var J = add(W[0], W[1]);
    var S = add(J, M[0]);
    return M.concat(D, N, W, [J, S]);
  }

  function cast(mothers) {
    var M = mothers.map(function (m) {
      if (Array.isArray(m)) return m.slice();
      if (!FIG[m]) throw new Error("unknown figure: " + m);
      return FIG[m].slice();
    });
    if (M.length !== 4) throw new Error("need four Mothers");
    var houses = castFromPatterns(M);
    return {
      mothers: M,
      houses: houses,
      names: houses.map(nameOf),
      roman: ROMAN,
      judge: nameOf(houses[14]),
      reconciler: nameOf(houses[15]),
      code: chartCode(M),
      judge_even: houses[14].reduce(function (s, v) { return s + v; }, 0) % 2 === 0
    };
  }

  function viaPuncti(h) {
    var par = { 14: [12, 13], 12: [8, 9], 13: [10, 11], 8: [0, 1], 9: [2, 3], 10: [4, 5], 11: [6, 7] };
    var ends = [], branches = [], stack = [[14, [14]]];
    while (stack.length) {
      var cur = stack.shift(), node = cur[0], path = cur[1];
      var ps = par[node];
      if (!ps) { ends.push([node + 1, nameOf(h[node]), "root"]); continue; }
      var val = h[node][0];
      var hits = ps.filter(function (q) { return h[q][0] === val; });
      if (!hits.length) { ends.push([node + 1, nameOf(h[node]), "died"]); continue; }
      if (hits.length > 1) {
        hits.slice(1).forEach(function (q) {
          var nm = nameOf(h[q]);
          if (branches.indexOf(nm) < 0) branches.push(nm);
        });
      }
      hits.slice().reverse().forEach(function (q) { stack.unshift([q, path.concat([q])]); });
    }
    var seen = {}, uniq = [];
    ends.forEach(function (e) {
      var k = e.join("|");
      if (!seen[k]) { seen[k] = 1; uniq.push(e); }
    });
    var primary = [], n = 14;
    while (true) {
      primary.push(n);
      var up = par[n];
      if (!up) break;
      var hit = up.filter(function (q) { return h[q][0] === h[n][0]; });
      if (!hit.length) break;
      n = hit[0];
    }
    return { primary: primary, branches: branches, ends: uniq };
  }

  function projection(h) {
    var s = 0, i, j;
    for (i = 0; i < 12; i++) for (j = 0; j < 4; j++) if (h[i][j] === 1) s++;
    return { singles: s, house: (s % 12) || 12 };
  }

  function partOfFortune(h) {
    var t = 0, i, j;
    for (i = 0; i < 12; i++) for (j = 0; j < 4; j++) t += h[i][j];
    return { points: t, house: (t % 12) || 12 };
  }

  function motus(h) {
    var seen = {}, i, n;
    for (i = 0; i < h.length; i++) {
      n = nameOf(h[i]);
      if (!seen[n]) seen[n] = [];
      seen[n].push(i + 1);
    }
    var out = {};
    Object.keys(seen).forEach(function (f) { if (seen[f].length > 1) out[f] = seen[f]; });
    return out;
  }

  function selfCheck() {
    var cJ = {}, i, a, b, c, d, ch, jn, odd = 0, n = 0;
    EVEN_JUDGES.forEach(function (x) { cJ[x] = 0; });
    for (a = 0; a < 16; a++) for (b = 0; b < 16; b++) for (c = 0; c < 16; c++) for (d = 0; d < 16; d++) {
      ch = castFromPatterns([rowsOf(a), rowsOf(b), rowsOf(c), rowsOf(d)]);
      jn = nameOf(ch[14]);
      if (ch[14].reduce(function (s, v) { return s + v; }, 0) % 2 !== 0) odd++;
      if (cJ[jn] == null) cJ[jn] = 0;
      cJ[jn]++;
      n++;
    }
    var evenOk = EVEN_JUDGES.every(function (x) { return cJ[x] === 8192; });
    return { casts: n, odd_judges: odd, judge_counts: cJ, even_population_ok: evenOk && odd === 0 };
  }

  return {
    FIG: FIG, NAMES: NAMES, ROMAN: ROMAN, EVEN_JUDGES: EVEN_JUDGES,
    add: add, rowValue: rowValue, nameOf: nameOf, idxOf: idxOf, rowsOf: rowsOf, chartCode: chartCode,
    cast: cast, castFromPatterns: castFromPatterns,
    viaPuncti: viaPuncti, projection: projection, partOfFortune: partOfFortune, motus: motus,
    selfCheck: selfCheck
  };
});
