/**
 * Fetch application data from GitHub via jsDelivr. No Python, no private server.
 * Pin a tag in production. @latest is for evaluation only.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.GeomancyCdn = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var DEFAULT_BASE = "https://cdn.jsdelivr.net/gh/Almuarif17/geomancy@v0.2.5/library/dataset/";

  function Cdn(opts) {
    opts = opts || {};
    this.base = opts.base || DEFAULT_BASE;
    this.store = opts.store || (typeof localStorage === "undefined" ? memStore() : localStorage);
  }

  function memStore() {
    var m = {};
    return {
      getItem: function (k) { return m[k] || null; },
      setItem: function (k, v) { m[k] = String(v); }
    };
  }

  Cdn.prototype.url = function (path) {
    return this.base.replace(/\/?$/, "/") + path.replace(/^\//, "");
  };

  Cdn.prototype.getText = async function (path) {
    var key = "gm:" + this.base + path;
    var hit = this.store.getItem(key);
    if (hit) return hit;
    var res = await fetch(this.url(path));
    if (!res.ok) throw new Error("cdn " + res.status + " " + path);
    var text = await res.text();
    try { this.store.setItem(key, text); } catch (e) {}
    return text;
  };

  Cdn.prototype.getJSON = async function (path) {
    return JSON.parse(await this.getText(path));
  };

  Cdn.prototype.manifest = function () { return this.getJSON("manifest.json"); };
  Cdn.prototype.coreFacts = function () { return this.getJSON("core_facts.json"); };

  return { Cdn: Cdn, DEFAULT_BASE: DEFAULT_BASE };
});
