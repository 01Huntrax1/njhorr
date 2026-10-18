P="patch/index.js"
s=open(P).read()
def rep(old,new):
    global s
    assert s.count(old)==1,(old[:70],s.count(old))
    s=s.replace(old,new)
rep("        this._page = \"sound\";\n        this._store = new Map();","        this._page = \"sound\";\n        this._lfoPts = new Array(10).fill(null);\n        this._lfoGrid = 0;\n        this._modReady = false;\n        this._store = new Map();")
rep("        this.updateSlots();\n        this.buildManager();","        this.updateSlots();\n        this.buildModStrip();\n        this._modReady = true;\n        this.buildManager();")
rep("        if ((n >= 307 && n <= 336) || (n >= 472 && n <= 501)) this.updateSlots();\n","""        if ((n >= 307 && n <= 336) || (n >= 472 && n <= 501)) { this.updateSlots(); if (this._modReady) this.updateModRings(); }
        if (this._modReady) {
            if (MOD_TARGET[n]) this.updateModRings(n);
            if (n >= 247 && n <= 266) { const li = Math.floor((n - 247) / 2); if (n % 2 === 1) this.refreshLfoUi(li); if (li === this._lfoSel) this.drawLfo(); }
            if (n >= 502 && n <= 521) this.refreshLfoUi(Math.floor((n - 502) / 2));
            if (n >= 267 && n <= 306 && Math.floor((n - 267) / 4) === this._envSel) this.drawEnv();
        }
""")
# ready: restore shapes
rep("            this.loadStore();\n            this.loadS2Store();","            this.restoreLfo();\n            this.loadStore();\n            this.loadS2Store();")
# presets
rep("const rec = { name, saved: Date.now(), params: this.collectParams(), refs: this.collectRefs() };","const rec = { name, saved: Date.now(), params: this.collectParams(), refs: this.collectRefs(), lfo: this.collectLfo() };")
rep("            this.updateSlots();\n            this.drawFlt();\n            for (let g = 0; g < 30; g++) this.updateFxRow(g);","            this.applyLfo(rec.lfo);\n            this.updateSlots();\n            this.updateModRings();\n            this.drawFlt();\n            for (let g = 0; g < 30; g++) this.updateFxRow(g);")
# CSS
css = """
  /* serum style layout: top groups, oscillator sub tabs, bottom modulation strip */
  .subtabs { display: none; flex: 0 0 auto; gap: calc(var(--u) * 3); }
  eisenpuls-view[data-group="osc"] .subtabs { display: flex; }
  .stab { font-family: inherit; font-size: calc(var(--u) * 9); font-weight: 800; letter-spacing: 0.06em; padding: calc(var(--u) * 4) calc(var(--u) * 10); border: 1px solid var(--line); border-radius: 1px; background: var(--panel); color: var(--dim); cursor: pointer; }
  .stab.on { background: var(--panel2); color: var(--yel); border-color: var(--yel); }
  .bstrip { flex: 0 0 auto; height: calc(var(--u) * 232); display: flex; flex-direction: column; background: linear-gradient(#25282c, #1a1c1f); border: 1px solid var(--line); border-radius: calc(var(--u) * 2); min-height: 0; }
  eisenpuls-view.strip-closed .bstrip { height: calc(var(--u) * 26); }
  eisenpuls-view.strip-closed .bs-body { display: none; }
  .bs-tabs { flex: 0 0 auto; display: flex; align-items: center; gap: calc(var(--u) * 4); padding: calc(var(--u) * 3) calc(var(--u) * 8); }
  .bst, .bs-btn, .bs-toggle { font-family: inherit; font-size: calc(var(--u) * 9); font-weight: 800; letter-spacing: 0.08em; padding: calc(var(--u) * 3) calc(var(--u) * 9); border: 1px solid var(--line); border-radius: 1px; background: var(--panel2); color: var(--ink); cursor: pointer; }
  .bst.on { background: var(--yel); color: #111; border-color: var(--yel); }
  .bs-hint { flex: 1; text-align: right; font-size: calc(var(--u) * 8); color: var(--dim); letter-spacing: 0.06em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bs-body { flex: 1 1 0; min-height: 0; position: relative; }
  .bs-pane { position: absolute; inset: 0; display: none; padding: 0 calc(var(--u) * 8) calc(var(--u) * 6); min-height: 0; }
  .bs-pane.on { display: flex; gap: calc(var(--u) * 8); }
  .bs-mtx.on { display: block; overflow: hidden; }
  .bs-mtx .mtx2 { height: 100%; }
  .bs-env { flex: 0 0 36%; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
  .bs-lfo { flex: 1 1 0; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
  .bs-chips { flex: 0 0 auto; display: flex; flex-wrap: wrap; gap: calc(var(--u) * 3); align-items: center; margin-bottom: calc(var(--u) * 4); }
  .bs-gap { flex: 1; }
  .msrc { font-family: inherit; font-size: calc(var(--u) * 8); font-weight: 800; letter-spacing: 0.05em; padding: calc(var(--u) * 3) calc(var(--u) * 5); border: 1px solid var(--line); border-radius: calc(var(--u) * 8); background: #14161a; color: var(--ink); cursor: grab; touch-action: none; }
  .bs-lfo .msrc { border-color: #7a2d20; } .bs-env .msrc { border-color: #1f5d85; } .msrc.misc { border-color: #6b6828; }
  .bs-lfo .msrc.on { background: #ff6a4d; color: #111; } .bs-env .msrc.on { background: #4db8ff; color: #111; }
  .bs-envbody, .bs-lfobody { flex: 1 1 0; min-height: 0; display: flex; gap: calc(var(--u) * 8); }
  .bs-envbody { flex-direction: column; }
  .env-canvas, .lfo-canvas { width: 100%; flex: 1 1 0; min-height: 0; display: block; background: #0b0405; border: 1px solid var(--line); border-radius: 2px; touch-action: none; }
  .lfo-cv { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; }
  .lfo-help { flex: 0 0 auto; font-size: calc(var(--u) * 7); color: var(--dim); margin-top: calc(var(--u) * 2); }
  .lfo-sets { flex: 0 0 34%; min-width: 0; position: relative; }
  .lfo-set, .env-set { display: none; }
  .lfo-set.on { display: grid; grid-template-rows: auto 1fr; gap: calc(var(--u) * 4); height: 100%; }
  .env-set.on { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: calc(var(--u) * 6); }
  .ls-top { display: grid; grid-template-columns: 1fr 1fr; gap: calc(var(--u) * 4) calc(var(--u) * 8); }
  .ls-shape { grid-column: 1 / -1; display: flex; flex-direction: column; }
  .ls-knobs { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: calc(var(--u) * 4); align-items: center; }
  .ls-hid { display: none; }
  .lfo-set.synced .n248 { opacity: 0.35; } .lfo-set:not(.synced) .ls-div { opacity: 0.35; }
  .lfo-set .btns .row, .lfo-set .sel .row { display: none; }
  .lfo-set .control .lbl { font-size: calc(var(--u) * 7.5); }
  .bs-env .knb .knob, .bs-lfo .knb .knob { width: calc(var(--u) * 30); height: calc(var(--u) * 30); }
  /* modulation rings, handles, popover */
  .knb .knob { position: relative; }
  .mring { position: absolute; inset: -4px; width: calc(100% + 8px); height: calc(100% + 8px); pointer-events: none; overflow: visible; }
  .mbar { position: absolute; top: 0; height: 100%; opacity: 0.55; pointer-events: none; border-radius: 2px; }
  .control { position: relative; }
  .mdot { position: absolute; top: 0; right: 0; width: calc(var(--u) * 10); height: calc(var(--u) * 10); padding: 0; border: 1px solid #000; border-radius: 50%; font-size: calc(var(--u) * 7); font-weight: 800; color: #111; cursor: pointer; line-height: 1; }
  .modding .control[data-param] { cursor: copy; }
  .modhover { outline: 2px solid var(--yel); outline-offset: 1px; border-radius: 3px; }
  .mod-ghost { position: absolute; z-index: 50; padding: calc(var(--u) * 3) calc(var(--u) * 7); border-radius: calc(var(--u) * 8); color: #111; font-size: calc(var(--u) * 9); font-weight: 800; pointer-events: none; box-shadow: 0 2px 8px rgba(0,0,0,0.6); }
  .modpop { position: absolute; z-index: 60; min-width: calc(var(--u) * 190); padding: calc(var(--u) * 6); background: #17191c; border: 1px solid var(--yel); border-radius: 3px; box-shadow: 0 4px 14px rgba(0,0,0,0.7); }
  .mp-title { font-size: calc(var(--u) * 8); letter-spacing: 0.1em; color: var(--dim); text-transform: uppercase; margin-bottom: calc(var(--u) * 4); }
  .mp-row { display: flex; align-items: center; gap: calc(var(--u) * 5); margin-top: calc(var(--u) * 3); }
  .mp-src { font-size: calc(var(--u) * 8); font-weight: 800; color: #111; padding: calc(var(--u) * 2) calc(var(--u) * 5); border-radius: calc(var(--u) * 6); }
  .mp-row input { flex: 1; min-width: 0; } .mp-val { width: calc(var(--u) * 32); font-size: calc(var(--u) * 8.5); text-align: right; font-family: ui-monospace, Menlo, monospace; }
  .mp-x { background: none; border: 1px solid var(--line); color: var(--ink); cursor: pointer; border-radius: 2px; }
  .lfo-set .dd { width: 100%; }
</style>
<div class="shell">"""
rep("</style>\n<div class=\"shell\">",css)
open(P,"w").write(s)
