// 6-slot oscillator UI: pages, source switching, Plaits labels, FM matrix, parameter ids (jsdom)
const fs = require("fs"), path = require("path");
const { JSDOM } = require("jsdom");
const code = fs.readFileSync(process.argv[2] || path.join(__dirname, "..", "patch", "index.js"), "utf8").replace("export default function createPatchView", "function createPatchView").replace(/<style>[\s\S]*?<\/style>/, "");
let failures = 0;
const check = (n, c, x) => { console.log((c ? "PASS " : "FAIL ") + n + (x ? "  (" + x + ")" : "")); if (!c) failures++; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const dom = new JSDOM("<!doctype html><body></body>", { url: "https://njohrr.test/", pretendToBeVisual: true, runScripts: "outside-only" });
const w = dom.window;
const noop = new Proxy(function () {}, { get: (t, p) => (p === Symbol.toPrimitive ? () => 0 : noop), set: () => true, apply: () => noop });
w.HTMLCanvasElement.prototype.getContext = () => noop;
w.eval(code + "\n;window.__create = createPatchView;");
const pc = { sent: [], requestFullStoredState (cb) { setTimeout(() => cb({ values: {} }), 5); }, sendStoredStateValue () {}, sendEventOrValue (ep, v) { pc.sent.push({ ep, v }); },
    requestParameterValue () {}, addEndpointListener () {}, removeEndpointListener () {}, addAllParameterListener () {}, removeAllParameterListener () {} };
(async () => {
    const V = w.__create(pc); w.document.body.appendChild(V); await sleep(200);
    const ctl = n => V._controls.get("param" + n);
    const opts = n => [...V.querySelectorAll(".control[data-param=\"param" + n + "\"] option")].map(o => o.textContent);
    check("6 oscillator pages", V.querySelectorAll(".page[data-src]").length === 6);
    check("every slot has all 44 parameters", [0, 1, 2, 3, 4, 5].every(o => [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44].every(k => ctl(1000 + 64 * o + k))));
    check("36 PD amounts", [0,1,2,3,4,5].every(s => [0,1,2,3,4,5].every(d => ctl(1480 + 6 * s + d))));
    check("36 FM amounts", [0,1,2,3,4,5].every(s => [0,1,2,3,4,5].every(d => ctl(1400 + 6 * s + d))));
    check("filter has all 30 types", opts(1031).length === 30 && opts(1031 + 64 * 5).length === 30);
    check("old filter / mixer / sampler controls are gone", !V.querySelector(".p-flt, .p-mix, .p-smp, .p-s2, .p-wt1") && !ctl(12) && !ctl(176) && !ctl(154));
    check("Plaits engine selector lists 24 engines", opts(1024).length === 24);

    const pg = V.querySelector(".p-o0");
    const shown = sel => { const e = V.querySelector(sel); return e && e.style.display !== "none"; };
    check("wavetable source shows warp, hides Plaits", shown('[data-o="0"][data-show="0"].o-g2') && !shown('[data-o="0"][data-show="2"]'));
    ctl(1000).setValue(1, true);
    check("sampler source shows sample controls", pg.getAttribute("data-src") === "1" && shown('[data-o="0"][data-show="1"]') && !shown('[data-o="0"][data-show="0"].o-g2'));
    ctl(1000).setValue(2, true);
    check("Plaits source shows engine controls", pg.getAttribute("data-src") === "2" && shown('[data-o="0"][data-show="2"]'));
    ctl(1024).setValue(21, true);
    check("Plaits knob labels follow the engine", V.querySelector(".n1025 .lbl").textContent === "Attack" && V.querySelector(".n1027 .lbl").textContent === "Decay", V.querySelector(".n1025 .lbl").textContent);
    ctl(1024 + 64).setValue(15, true);
    check("labels are per slot", V.querySelector(".n1089 .lbl").textContent === "Species" && V.querySelector(".n1025 .lbl").textContent === "Attack");
    check("slot dest list covers 167", opts(308).length === 168 && opts(308)[6] === "OSC 1 Pitch" && opts(308)[59] === "OSC 6 Dist Drive" && opts(308)[60] === "FM A > A" && opts(308)[167] === "PD F > F");
    V.querySelector('.stab[data-page="fm"]').click();
    check("FM page opens", V.getAttribute("data-page") === "fm" && V.querySelectorAll(".fmx-c").length === 108 && V.querySelectorAll(".fmx-panel").length === 3);
    V.querySelector('.stab[data-page="glob"]').click();
    check("global page opens", V.getAttribute("data-page") === "glob");
    console.log(failures ? failures + " FAILED" : "all passed");
    process.exit(failures ? 1 : 0);
})();
