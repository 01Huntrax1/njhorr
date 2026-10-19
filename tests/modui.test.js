// Serum-style layout, LFO shape editor and drag-and-drop modulation (jsdom)
const fs = require("fs"), path = require("path");
const { JSDOM } = require("jsdom");
const code = fs.readFileSync(process.argv[2] || path.join(__dirname, "..", "patch", "index.js"), "utf8").replace("export default function createPatchView", "function createPatchView").replace(/<style>[\s\S]*?<\/style>/, "");   // jsdom is far faster without the big stylesheet
let failures = 0;
const check = (n, c, x) => { console.log((c ? "PASS " : "FAIL ") + n + (x ? "  (" + x + ")" : "")); if (!c) failures++; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
function makeWebView () {
    const dom = new JSDOM("<!doctype html><body></body>", { url: "https://njohrr.test/", pretendToBeVisual: true, runScripts: "outside-only" });
    const w = dom.window;
    const noop = new Proxy(function () {}, { get: (t, p) => (p === Symbol.toPrimitive ? () => 0 : noop), set: () => true, apply: () => noop });
    w.HTMLCanvasElement.prototype.getContext = () => noop;
    w.eval(code + "\n;window.__create = createPatchView;");
    return w;
}
function makePC (store) {
    const pc = { sent: [], store: store || {},
        requestFullStoredState (cb) { setTimeout(() => cb({ parameters: [], values: JSON.parse(JSON.stringify(pc.store)) }), 5); },
        sendStoredStateValue (k, v) { pc.store[k] = v; },
        sendEventOrValue (ep, v) { pc.sent.push({ ep, v }); },
        requestParameterValue () {}, addEndpointListener () {}, removeEndpointListener () {}, addAllParameterListener () {}, removeAllParameterListener () {} };
    return pc;
}
const ctl = (v, n) => v._controls.get("param" + n);
const ptr = (w, type, x, y, id) => { const e = new w.Event(type, { bubbles: true }); Object.assign(e, { clientX: x, clientY: y, pointerId: id || 1 }); return e; };

(async () => {
    const w = makeWebView(), pc = makePC();
    const V = w.__create(pc); w.document.body.appendChild(V); await sleep(150);

    check("top tabs are OSC / FM / FX / GLOBAL", [...V.querySelectorAll(".tab")].map(t => t.textContent).join() === "OSC,FM,FX,GLOBAL");
    check("osc sub tabs", [...V.querySelectorAll(".stab")].map(t => t.textContent).join() === "OSC 1,OSC 2,OSC 3,OSC 4,OSC 5,OSC 6");
    V.querySelector('.stab[data-page="o1"]').click();
    check("sub tab opens OSC 2", V.getAttribute("data-page") === "o1" && V.getAttribute("data-group") === "osc");
    V.querySelector('.tab[data-group="fx"]').click();
    check("FX group", V.getAttribute("data-page") === "fx");
    V.querySelector('.tab[data-group="osc"]').click();
    check("OSC group remembers the sub tab", V.getAttribute("data-page") === "o1");
    check("old LFO/ENV/MOD pages are gone", !V.querySelector(".p-lfo, .p-env, .p-mod"));
    check("10 LFO + 10 ENV chips", V.querySelectorAll(".bs-lfo .msrc").length === 10 && V.querySelectorAll(".bs-env .msrc:not(.misc)").length === 10);

    // LFO controls exist
    check("LFO 1 mode/delay/rise/smooth/phase exist", [882, 883, 884, 885, 886].every(n => ctl(V, n)));
    check("wave has 7 values incl. Drawn", ctl(V, 247).max === 6);

    // shape editing
    pc.sent.length = 0;
    V.selectLfo(2);
    const P = V.lfoEnsurePts(2);
    P.splice(1, 0, { x: 0.5, y: 0.25, c: 0 });
    V.lfoCommit(2, true);
    const sent = pc.sent.filter(x => x.ep === "lfoShapeLoad");
    check("shape sent to the DSP", sent.length === 1 && sent[0].v.lfo === 2 && sent[0].v.data.length === 256);
    check("wave switched to Drawn", Math.round(ctl(V, 251).value) === 6);
    check("shape table follows the points", Math.abs(sent[0].v.data[128] - 0.25) < 0.01, String(sent[0].v.data[128]));
    check("shape stored in instance state", Array.isArray(pc.store["njo.lfo"]) && pc.store["njo.lfo"][2] && pc.store["njo.lfo"][2].length === P.length);

    // preset shape menu
    V.setLfoPreset(2, 1);
    check("built-in preset clears the drawn shape", V._lfoPts[2] === null && Math.round(ctl(V, 251).value) === 1);
    pc.sent.length = 0;
    V.setLfoPreset(2, 7);   // Pulse 25%
    check("drawn preset sends a table", pc.sent.some(x => x.ep === "lfoShapeLoad" && x.v.lfo === 2));

    // drag and drop
    V.selectLfo(0);
    const knob = V.querySelector('.control[data-param="param1032"]');
    check("OSC 1 cutoff is a mod target", !!V.modTargetOf(knob.querySelector(".knob")) && V.modTargetOf(knob).dst === 12);
    const slot = V.modAssign(1, 12, 0.5);
    check("assign uses the first free slot", slot === 0 && Math.round(ctl(V, 307).value) === 1 && Math.round(ctl(V, 308).value) === 12 && Math.abs(ctl(V, 309).value - 0.5) < 1e-6);
    check("same pair updates, not duplicates", V.modAssign(1, 12, -0.3) === 0 && Math.abs(ctl(V, 309).value + 0.3) < 1e-6);
    check("second source takes next slot", V.modAssign(11, 12, 0.4) === 1);
    V.updateModRings();
    check("ring + dot on the modulated knob", knob.classList.contains("modded") && !!knob.querySelector(".mdot"));
    check("dot shows count of 2", knob.querySelector(".mdot").textContent === "2");
    V.modClear(1);
    V.updateModRings();
    check("clearing a slot lowers the count", knob.querySelector(".mdot").textContent === "");
    V.modClear(0);
    V.updateModRings();
    check("no mod: ring removed", !knob.classList.contains("modded") && !knob.querySelector(".mdot"));

    // full matrix
    for (let k = 0; k < 20; k++) V.modAssign(1 + (k % 10), 2 + (k % 3) + (k > 9 ? 10 : 0), 0.1);
    check("full matrix returns -1", V.modAssign(21, 40, 0.5) === -1);
    for (let k = 0; k < 20; k++) V.modClear(k);

    // persistence + isolation
    const w2 = makeWebView(), pc2 = makePC(JSON.parse(JSON.stringify(pc.store)));
    const V2 = w2.__create(pc2); w2.document.body.appendChild(V2); await sleep(200);
    check("shape restored in a new view", !!V2._lfoPts[2]);
    check("restored shape resent to the DSP", pc2.sent.some(x => x.ep === "lfoShapeLoad" && x.v.lfo === 2));
    const pc3 = makePC(), V3 = w2.__create(pc3); w2.document.body.appendChild(V3); await sleep(200);
    check("other instance has no shapes", V3._lfoPts.every(p => p === null));

    // preset round trip
    const rec = { name: "t", params: V.collectParams(), refs: {}, lfo: V.collectLfo() };
    V3.applyLfo(rec.lfo);
    check("preset carries the shape", !!V3._lfoPts[2] && V3._lfoPts[2].length === V._lfoPts[2].length);
    V3.applyLfo(null);
    check("preset without shapes clears them", V3._lfoPts.every(p => p === null));

    console.log(failures ? failures + " FAILED" : "all passed");
    process.exit(failures ? 1 : 0);
})();
