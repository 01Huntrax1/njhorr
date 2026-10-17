// FX rack UI test (jsdom): types, per-type defaults, reordering, preset round trip, legacy preset migration, instance isolation.
// Usage: node fxrack.test.js [path to index.js]
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const indexPath = process.argv[2] || path.join(__dirname, "..", "patch", "index.js");
const code = fs.readFileSync(indexPath, "utf8").replace("export default function createPatchView", "function createPatchView");
let failures = 0;
const check = (name, cond, extra) => { console.log((cond ? "PASS " : "FAIL ") + name + (extra ? "  (" + extra + ")" : "")); if (!cond) failures++; };
const sleep = ms => new Promise(r => setTimeout(r, ms));

function makeWebView () {
    const dom = new JSDOM("<!doctype html><body></body>", { url: "https://njohrr.test/", pretendToBeVisual: true, runScripts: "outside-only" });
    const w = dom.window;
    const noopCtx = new Proxy(function () {}, { get: (t, p) => (p === Symbol.toPrimitive ? () => 0 : noopCtx), set: () => true, apply: () => noopCtx });
    w.HTMLCanvasElement.prototype.getContext = () => noopCtx;
    w.eval(code + "\n;window.__create = createPatchView;");
    return w;
}
function makePC () {
    const pc = { state: {}, sent: [],
        requestFullStoredState (cb) { setTimeout(() => cb({ parameters: [], values: {} }), 5); },
        sendStoredStateValue () {},
        sendEventOrValue (ep, v) { pc.sent.push({ ep, v }); },
        requestParameterValue () {}, addEndpointListener () {}, removeEndpointListener () {}, addAllParameterListener () {}, removeAllParameterListener () {} };
    return pc;
}
const mount = (w, pc) => { const v = w.__create(pc); w.document.body.appendChild(v); return v; };
const last = (pc, ep) => { const m = pc.sent.filter(x => x.ep === ep); return m.length ? m[m.length - 1].v : undefined; };
const ctl = (v, n) => v._controls.get("param" + n);

(async () => {
    const w = makeWebView();
    const pcA = makePC(), pcB = makePC();
    const A = mount(w, pcA), B = mount(w, pcB);
    await sleep(150);

    // ---- structure
    check("3 racks of 10 rows", A.querySelectorAll(".fxrow").length === 30 && A.querySelectorAll(".f-rack").length === 3);
    check("no legacy fixed-chain controls left", ![30, 31, 32, 60, 61, 62, 164, 170, 173, 183, 191, 537, 540].some(n => ctl(A, n)));
    check("rack starts empty", A.querySelectorAll(".fxrow.empty").length === 30);
    check("initial order is 0..9", JSON.stringify(A.fxOrderNow(0)) === JSON.stringify([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]));

    // ---- choosing a type in slot 3 (id base 561) sends type + the effect's own defaults
    pcA.sent.length = 0;
    ctl(A, 561).setValue(3, true);                       // Delay
    check("type sent to the DSP", last(pcA, "param561") === 3);
    check("delay default mix sent", Math.abs(last(pcA, "param563") - 0.35) < 1e-6, String(last(pcA, "param563")));
    check("delay default time sent (375 ms)", Math.abs(last(pcA, "param565") - Math.log(37.5) / Math.log(100)) < 1e-3);
    check("row no longer empty", !A.querySelector('.fxrow[data-g="2"]').classList.contains("empty"));
    const lbls = [...A.querySelectorAll('.fxrow[data-g="2"] .fxps .lbl')].map(e => e.textContent);
    check("labels follow the type", JSON.stringify(lbls) === JSON.stringify(["Time", "Feedback", "Damp", "Ping-Pong", "", ""]), JSON.stringify(lbls));
    check("unused knobs are hidden", A.querySelectorAll('.fxrow[data-g="2"] .fxps .nop').length === 2);
    check("mode list follows the type", A.querySelector('.fxrow[data-g="2"] .fxmd select').options.length === 3);
    check("value text uses real units", /ms$/.test(A.querySelector('.fxrow[data-g="2"] .n565 .val').textContent), A.querySelector('.fxrow[data-g="2"] .n565 .val').textContent);

    // ---- the other instance is untouched (shared formatting state must not leak)
    check("instance B slot 3 still empty", B.querySelector('.fxrow[data-g="2"]').classList.contains("empty") && B._fxTypes[2] === 0);
    ctl(B, 561).setValue(8, true);                       // reverb in B
    check("A keeps its own type formatting", /ms$/.test(A.querySelector('.fxrow[data-g="2"] .n565 .val').textContent));
    check("B formats as reverb", A._fxTypes[2] === 3 && B._fxTypes[2] === 8);

    // ---- switching a slot to another type loads that type's defaults and mode 0
    ctl(A, 564).setValue(2, true);
    ctl(A, 561).setValue(7, true);                       // Tremolo
    check("mode reset on type change", ctl(A, 564).value === 0);
    check("tremolo mix default 1", Math.abs(ctl(A, 563).value - 1) < 1e-6);
    check("bit-crush has two knobs", (ctl(A, 561).setValue(2, true), A.querySelectorAll('.fxrow[data-g="2"] .fxps .nop').length === 4));

    // ---- the Filter effect offers all 30 filter types of the Filter page
    ctl(A, 561).setValue(9, true);
    check("filter effect lists all 30 filter types", A.querySelector('.fxrow[data-g="2"] .fxmd select').options.length === 30);
    ctl(A, 564).setValue(23, true);
    check("filter type 23 (Vowel) selectable and sent", last(pcA, "param564") === 23 && A.querySelector('.fxrow[data-g="2"] .fxmd select').selectedIndex === 23);
    ctl(A, 561).setValue(2, true);

    // ---- reordering: slot 3 up to the top
    pcA.sent.length = 0;
    A.fxMove(0, 2, 0);
    check("order is now 2,0,1,3..", JSON.stringify(A.fxOrderNow(0)) === JSON.stringify([2, 0, 1, 3, 4, 5, 6, 7, 8, 9]), JSON.stringify(A.fxOrderNow(0)));
    check("order events sent for the changed positions only", pcA.sent.filter(m => /^param64\d|^param650$/.test(m.ep)).length === 3);
    check("row 3 is displayed first", A.querySelector('.fxrow[data-g="2"]').style.order === "0" && A.querySelector('.fxrow[data-g="0"]').style.order === "1");
    check("position badge updated", A.querySelector('.fxrow[data-g="2"] .fxpos').textContent === "1");
    A.querySelector('.fxrow[data-g="2"] .fxdn').click();
    check("down arrow moves one place", JSON.stringify(A.fxOrderNow(0)) === JSON.stringify([0, 2, 1, 3, 4, 5, 6, 7, 8, 9]));
    check("the sent order is always a permutation at the end", new Set(A.fxOrderNow(0)).size === 10);

    // ---- buses: Bus 1 (651..) and Bus 2 (761..) racks, source routing, bus levels
    pcA.sent.length = 0;
    ctl(A, 651 + 10).setValue(10, true);                  // EQ in Bus 1 slot 2
    ctl(A, 761).setValue(8, true);                        // reverb in Bus 2 slot 1
    check("Bus 1 slot parameters reach the DSP", last(pcA, "param661") === 10 && last(pcA, "param651") !== 10);
    check("Bus 2 slot parameters reach the DSP", last(pcA, "param761") === 8);
    check("Bus slots are global slots 10-29", A._fxTypes[11] === 10 && A._fxTypes[20] === 8 && A._fxTypes[1] === 0);
    check("Bus rows labelled by their own type", /Reverb/.test(A.querySelector('.fxrow[data-g="20"] .fxty select').value));
    A.fxMove(1, 1, 0);
    check("Bus 1 reorder uses its own order parameters", JSON.stringify(A.fxOrderNow(1)) === JSON.stringify([1, 0, 2, 3, 4, 5, 6, 7, 8, 9]) && last(pcA, "param751") === 1);
    check("Main order untouched by Bus 1 reorder", JSON.stringify(A.fxOrderNow(0)) === JSON.stringify([0, 2, 1, 3, 4, 5, 6, 7, 8, 9]));
    check("rack tabs exist (Bus 1, Bus 2, Main)", [...A.querySelectorAll(".fxtab")].map(t => t.textContent).join("|") === "Bus 1|Bus 2|Main");
    A.querySelector('.fxtab[data-rack="1"]').click();
    check("tab switches the visible rack", A.querySelector('.f-rack[data-rack="1"]').classList.contains("on") && !A.querySelector('.f-rack[data-rack="0"]').classList.contains("on"));
    check("tab marks racks in use", A.querySelector('.fxtab[data-rack="1"]').classList.contains("used") && A.querySelector('.fxtab[data-rack="2"]').classList.contains("used"));
    ctl(A, 874).setValue(2, true);
    check("source output route is sent", last(pcA, "param874") === 2 && A.querySelectorAll(".chrt").length === 9);
    ctl(A, 880).setValue(0.5, true);
    check("bus level is sent", last(pcA, "param880") === 0.5);
    const sv = A.collectParams();
    check("preset stores routes, bus levels and bus racks", sv["874"] === 2 && sv["880"] === 0.5 && sv["661"] === 10 && sv["761"] === 8 && sv["751"] === 1);
    const E = mount(makeWebView(), makePC());
    await sleep(100);
    await E.presetApply({ name: "bus", params: sv, refs: {} });
    check("preset restores bus state", E._fxTypes[11] === 10 && E._fxTypes[20] === 8 && JSON.stringify(E.fxOrderNow(1)) === JSON.stringify(A.fxOrderNow(1)) && ctl(E, 874).value === 2 && ctl(E, 880).value === 0.5);
    ctl(A, 874).setValue(0, true); ctl(A, 880).setValue(1, true); ctl(A, 661).setValue(0, true); ctl(A, 761).setValue(0, true);

    // ---- preset round trip
    ctl(A, 541).setValue(4, true); ctl(A, 546).setValue(0.9, true);     // chorus in slot 1, P3? (param546 = P3 of slot 1)
    const saved = A.collectParams();
    check("preset contains rack + order", saved["541"] === 4 && saved["642"] === 2 && "546" in saved);
    const C = mount(makeWebView(), makePC());
    await sleep(100);
    await C.presetApply({ name: "t", params: saved, refs: {} });
    check("preset restores types", C._fxTypes[0] === 4 && C._fxTypes[2] === 2, JSON.stringify(C._fxTypes));
    check("preset restores order", JSON.stringify(C.fxOrderNow(0)) === JSON.stringify(A.fxOrderNow(0)));
    check("preset restores knob", Math.abs(ctl(C, 546).value - 0.9) < 1e-6);
    check("loading a preset does not reset knobs to type defaults", Math.abs(ctl(C, 546).value - 0.9) < 1e-6 && Math.abs(ctl(C, 543).value - ctl(A, 543).value) < 1e-6);

    // ---- legacy presets (fixed chain) are migrated into slots
    const legacy = { "32": 1, "183": 0.5, "30": 375, "31": 0.4, "60": 8000, "184": 0.7, "537": 1,       // tape delay
                     "164": 0.6, "165": 0.8, "166": 0.6, "177": 0.2, "538": 2,                          // vibrato chorus
                     "170": 0.5, "171": 0.5, "172": 0.5, "179": 20, "180": 1, "540": 2,                 // plate reverb
                     "61": 8, "62": 4, "191": 0.7, "36": 0.5 };
    const D = mount(makeWebView(), makePC());
    await sleep(100);
    await D.presetApply({ name: "old", params: legacy, refs: {} });
    check("legacy: delay lands in slot 1 (tape, 50% mix)", D._fxTypes[0] === 3 && ctl(D, 544).value === 1 && Math.abs(ctl(D, 543).value - 0.5) < 1e-6);
    check("legacy: delay time maps back (375 ms)", Math.abs(ctl(D, 545).value - Math.log(37.5) / Math.log(100)) < 1e-3);
    check("legacy: chorus slot 2 vibrato", D._fxTypes[1] === 4 && ctl(D, 554).value === 2);
    check("legacy: reverb slot 3 plate", D._fxTypes[2] === 8 && ctl(D, 564).value === 2);
    check("legacy: bit crush slot 4", D._fxTypes[3] === 2 && Math.abs(ctl(D, 575).value - (8 / 12)) < 1e-6 && Math.abs(ctl(D, 576).value - 3 / 31) < 1e-6);
    check("legacy: remaining slots empty", D._fxTypes.slice(4).every(t => t === 0));
    check("legacy: unrelated parameters untouched", Math.abs(ctl(D, 36).value - 0.5) < 1e-6);
    check("legacy: order is the identity", JSON.stringify(D.fxOrderNow(0)) === JSON.stringify([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]));

    console.log(failures ? "\n" + failures + " FAILED" : "\nALL PASSED");
    process.exit(failures ? 1 : 0);
})().catch(e => { console.error("HARNESS ERROR", e); process.exit(2); });
