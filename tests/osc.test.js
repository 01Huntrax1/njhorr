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
    check("6 oscillator pages, 6 filter pages, 6 distortion pages", [..."ofd"].every(k => [...V.querySelectorAll(".page")].filter(e => new RegExp("\\bp-" + k + "\\d\\b").test(e.className)).length === 6));
    check("every slot has all 44 parameters", [0, 1, 2, 3, 4, 5].every(o => [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44].every(k => ctl(1000 + 64 * o + k))));
    check("36 PD amounts", [0,1,2,3,4,5].every(s => [0,1,2,3,4,5].every(d => ctl(1480 + 6 * s + d))));
    check("36 RM and 36 AM amounts", [0,1,2,3,4,5].every(s => [0,1,2,3,4,5].every(d => ctl(1520 + 6 * s + d) && ctl(1560 + 6 * s + d))));
    check("dest list: RM / AM cells (186..257) then every Physical / Alpha Juno parameter (258..443) and every Kick parameter (444..539)", opts(308).length === 540 && opts(308)[444] === "OSC 1 Kick Mode" && opts(308)[539] === "OSC 6 Kick Character" && opts(308)[258] === "OSC 1 Physical Noise vs Mallet" && opts(308)[443] === "OSC 6 Juno Vibrato" && opts(308)[186] === "RM A > A" && opts(308)[221] === "RM F > F" && opts(308)[222] === "AM A > A" && opts(308)[257] === "AM F > F");
    check("36 FM amounts", [0,1,2,3,4,5].every(s => [0,1,2,3,4,5].every(d => ctl(1400 + 6 * s + d))));
    check("filter has all 30 types plus the Wavefilter", opts(1031).length === 31 && opts(1031 + 64 * 5).length === 31 && opts(1031)[30] === "Wavefilter");
    check("distortion has 6 types plus the Wavedistortion", opts(1042).length === 8 && opts(1042)[7] === "Wavedistortion");
    check("table position controls exist for every slot", [0,1,2,3,4,5].every(o => ctl(1046 + 64 * o) && ctl(1047 + 64 * o)));
    check("every slot has a Frequency knob (0 = Off)", [0,1,2,3,4,5].every(o => ctl(1048 + 64 * o)) && V.querySelector(".control[data-param=\"param1048\"] .val") !== undefined);
    check("old filter / mixer / sampler controls are gone", !V.querySelector(".p-flt, .p-mix, .p-smp, .p-s2, .p-wt1") && !ctl(12) && !ctl(176) && !ctl(154));
    check("Plaits engine selector lists 24 engines", opts(1024).length === 24);
    check("Source selector is a dropdown with the Kick source", opts(1000).length === 6 && opts(1000)[5] === "Kick" && opts(1064).length === 6 && ctl(1900) && ctl(1995) && opts(1900).length === 4 && opts(1910).length === 6);

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
    check("slot dest list covers 185 (incl. the Frequency knobs)", opts(308).length >= 186 && opts(308)[180] === "OSC 1 Frequency" && opts(308)[185] === "OSC 6 Frequency" && opts(308)[168] === "OSC 1 Wavefilter Pos" && opts(308)[179] === "OSC 6 Wavedistortion Pos" && opts(308)[6] === "OSC 1 Pitch" && opts(308)[59] === "OSC 6 Dist Drive" && opts(308)[60] === "FM A > A" && opts(308)[167] === "PD F > F");
    V.querySelector('.stab[data-page="fm"]').click();
    check("FM page opens", V.getAttribute("data-page") === "fm" && V.querySelectorAll(".fmx-c").length === 180 && V.querySelectorAll(".fmx-panel").length === 5 && V.querySelectorAll(".p-fm .fmx-panel").length === 3 && V.querySelectorAll(".p-rm .fmx-panel").length === 2);
    V.querySelector('.stab[data-page="rm"]').click();
    check("RM / AM page opens", V.getAttribute("data-page") === "rm");
    V.querySelector('.stab[data-page="fm"]').click();
    V.querySelector('.stab[data-page="glob"]').click();
    check("global page opens", V.getAttribute("data-page") === "glob");
    // Wavefilter / Wavedistortion tables
    {
        const mono = new Float32Array(3 * 2048); for (let f = 0; f < 3; f++) for (let i = 0; i < 2048; i++) mono[f * 2048 + i] = f / 2;
        const t = V.tblFromMono(mono);
        check("a 3 frame wavetable file becomes 3 frames of 512 points", t.length === 3 * 512 && Math.abs(t[512 * 2 + 100] - 1) < 1e-6 && Math.abs(t[512 + 7] - 0.5) < 1e-6);
        check("built-in filter table 0 is a low-pass (open below the cutoff)", V.tblFrame("ft", 0, 0)[10] > 0.9 && V.tblFrame("ft", 0, 0)[500] < -0.9);
        check("built-in shaper table 0 is the identity", Math.abs(V.tblFrame("sh", 0, 0)[255] + 0.002) < 0.01 && Math.abs(V.tblFrame("sh", 0, 0)[511] - 1) < 1e-6);
        pc.sent.length = 0;
        V.memStream("ft", 2, { name: "T", total: 1024, data: new Float32Array(1024) }, null); V.memStream("sh", 2, { name: "S", total: 512, data: new Float32Array(512) }, null);
        await sleep(100);
        const banks = pc.sent.filter(x => x.ep === "tblLoad").map(x => x.v.bank);
        check("filter table streams to bank o, shaper table to bank 6 + o", banks.includes(2) && banks.includes(8) && pc.sent.every(x => x.ep === "tblLoad"), banks.join());
        ctl(1031).setValue(30, true); ctl(1042).setValue(7, true);
        V.updateOscUi(0);
        const tbf = V.querySelector('.o-tb[data-o="0"][data-k="ft"]'), tbs = V.querySelector('.o-tb[data-o="0"][data-k="sh"]');
        check("table cards are active with the table types", !tbf.classList.contains("off") && !tbs.classList.contains("off"));
        ctl(1031).setValue(0, true); V.updateOscUi(0);
        check("and dimmed again", tbf.classList.contains("off"));
        // Filter / Wavefilter and Distortion / Wavedistortion switches
        const mf = V.querySelector('.o-mode[data-o="0"][data-k="f"]'), md = V.querySelector('.o-mode[data-o="0"][data-k="d"]');
        ctl(1031).setValue(5, true); mf.querySelectorAll("button")[1].click();
        check("WAVEFILTER switch selects the table filter", Math.round(V.oscVal(0, "ftype")) === 30);
        mf.querySelectorAll("button")[0].click();
        check("FILTER switch returns to the previous type", Math.round(V.oscVal(0, "ftype")) === 5);
        ctl(1042).setValue(3, true); md.querySelectorAll("button")[1].click();
        check("WAVEDISTORTION switch selects the table shaper", Math.round(V.oscVal(0, "dtype")) === 7);
        md.querySelectorAll("button")[0].click();
        check("DISTORTION switch returns to the previous type", Math.round(V.oscVal(0, "dtype")) === 3);
        // FILTER / DIST tabs and oscillator chips
        V.querySelector('.stab[data-grp="f"]').click();
        check("FILTER tab opens the filter page", V.getAttribute("data-page") === "f0");
        V.querySelector('.otab[data-pg="f"][data-oo="3"]').click();
        check("chip D opens OSC 4 on the filter page", V.getAttribute("data-page") === "f3");
        V.querySelector('.stab[data-page="o0"]').click(); V.querySelector('.stab[data-grp="d"]').click();
        check("DIST tab opens the distortion page", V.getAttribute("data-page") === "d0");
        V.querySelector('.stab[data-grp="f"]').click();
        check("FILTER tab remembers the oscillator", V.getAttribute("data-page") === "f3");
        // transfer curve of the distortion display (mirror of the DSP)
        ctl(1042).setValue(0, true);
        check("distortion Off is the identity", Math.abs(V.distY(0, 0.4) - 0.4) < 1e-9);
        ctl(1042).setValue(1, true); ctl(1043).setValue(0, true); ctl(1044).setValue(1, true);
        check("Soft at drive 0 is x / (1 + |x|)", Math.abs(V.distY(0, 0.5) - 0.5 / 1.5) < 1e-6, String(V.distY(0, 0.5)));
    }

    console.log(failures ? failures + " FAILED" : "all passed");
    process.exit(failures ? 1 : 0);
})();
