// Regression test: samples / wavetables must stay inside ONE plugin instance.
// Runs patch/index.js in jsdom with a mock patch connection (per-instance stored state) and two plugin instances
// that share one localStorage, which is what two plugin windows in a DAW look like to the web view.
//   cd tests && npm install && npm test
// Pass another index.js as the first argument to test it instead; set OLD_EP=1 for the older endpoint names that
// are baked into the UI inside cmajor_plugin.cpp.
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const indexPath = process.argv[2] || path.join(__dirname, "..", "patch", "index.js");
const code = fs.readFileSync(indexPath, "utf8").replace("export default function createPatchView", "function createPatchView");

// endpoint names differ between the V2 patch source and the older generation embedded in cmajor_plugin.cpp
const EP = process.env.OLD_EP ? { restore: "sampleRestore", s2: "synthSample2In", wt1: "wavetableIn" }
                              : { restore: "sampleBankV2Restore", s2: "sampleBank2V2Load", wt1: "wavetableBankV2Load" };
let failures = 0;
const check = (name, cond, extra) => {
    console.log((cond ? "PASS " : "FAIL ") + name + (extra ? "  (" + extra + ")" : ""));
    if (!cond) failures++;
};
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---- one WebView: jsdom window with ONE localStorage shared by every plugin instance in it ----
function makeWebView () {
    const dom = new JSDOM("<!doctype html><body></body>", { url: "https://njohrr.test/", pretendToBeVisual: true, runScripts: "outside-only" });
    const w = dom.window;
    const noopCtx = new Proxy(function () {}, { get: (t, p) => (p === Symbol.toPrimitive ? () => 0 : noopCtx), set: () => true, apply: () => noopCtx });
    w.HTMLCanvasElement.prototype.getContext = () => noopCtx;
    w.eval(code + "\n;window.__create = createPatchView;");
    return w;
}

// ---- mock host patch connection with per-instance stored state (what the real host provides) ----
function makePC (initialState) {
    const state = Object.assign({}, initialState || {});
    const pc = {
        state, sent: [], storedWrites: 0,
        requestFullStoredState (cb) { setTimeout(() => cb({ parameters: [], values: JSON.parse(JSON.stringify(state)) }), 5); },
        sendStoredStateValue (k, v) {
            pc.storedWrites++;
            if (v === null || v === undefined) delete state[k]; else state[k] = JSON.parse(JSON.stringify(v));   // host round-trips JSON
        },
        sendEventOrValue (ep, v) { pc.sent.push({ ep, v }); },
        requestParameterValue () {}, addEndpointListener () {}, removeEndpointListener () {},
        addAllParameterListener () {}, removeAllParameterListener () {}
    };
    return pc;
}

function mount (w, pc) {
    const view = w.__create(pc);
    w.document.body.appendChild(view);
    return view;
}

function ramp (n, seed) { const a = new Float32Array(n); for (let i = 0; i < n; i++) a[i] = Math.sin(i * 0.05 * seed) * 0.8; return a; }
function maxErr (a, b) { let m = 0; for (let i = 0; i < a.length; i++) m = Math.max(m, Math.abs(a[i] - b[i])); return m; }

(async () => {
    // =============== scenario 1: two instances, ONE shared localStorage (the reported bug) ===============
    {
        const w = makeWebView();
        const pcA = makePC(), pcB = makePC();
        const A = mount(w, pcA);
        const B = mount(w, pcB);
        await sleep(100);

        // instance A loads a "kick" into sampler 1
        const kick = ramp(3000, 1);
        A._smpState[0] = "KICK"; A._store.set(0, { name: "KICK", total: kick.length, data: kick }); A.persist(0);

        check("A saved the kick in its OWN stored state", !!pcA.state["njo.mem.sampler1.0"]);
        check("B's stored state is untouched", Object.keys(pcB.state).length === 0, JSON.stringify(Object.keys(pcB.state)));
        check("nothing was written to the shared localStorage", w.localStorage.length === 0, "len=" + w.localStorage.length);

        // a fresh editor for instance B (as when a second plugin window opens / project loads)
        const B2 = mount(w, pcB);
        await sleep(2500);
        const bRestore = pcB.sent.filter(m => m.ep === EP.restore);
        check("B2 got no sample from A", B2._store.size === 0 && bRestore.length === 0, "chunks=" + bRestore.length);

        // B loads its own sample; A must not change
        const snare = ramp(2000, 3);
        B._smpState[0] = "SNARE"; B._store.set(0, { name: "SNARE", total: snare.length, data: snare }); B.persist(0);
        check("A's saved sample is still the kick", pcA.state["njo.mem.sampler1.0"].name === "KICK" && pcA.state["njo.mem.sampler1.0"].total === 3000);
        check("B's saved sample is the snare", pcB.state["njo.mem.sampler1.0"].name === "SNARE" && pcB.state["njo.mem.sampler1.0"].total === 2000);
    }

    // =============== scenario 2: same instance reopened -> restores its own audio into the DSP ===============
    {
        const w = makeWebView();
        const pc = makePC();
        const V = mount(w, pc);
        await sleep(100);
        const s1 = ramp(3000, 1), s2 = ramp(1500, 2), wt = ramp(2048 * 3, 4), wt2 = ramp(1024, 5);
        V._smpState[0] = "KICK"; V._store.set(0, { name: "KICK", total: s1.length, data: s1 }); V.persist(0);
        V._s2State[0] = "HAT";   V._s2Store.set(0, { name: "HAT", total: s2.length, data: s2 }); V.persistS2(0);
        V._wt[0].state[0] = "SAW"; V._wt[0].store.set(0, { name: "SAW", total: wt.length, data: wt }); V.persistWt(0, 0);
        V._wt[1].state[0] = "PAD"; V._wt[1].store.set(0, { name: "PAD", total: wt2.length, data: wt2 }); V.persistWt(1, 0);
        check("all four memories were stored", ["njo.mem.sampler1.0", "njo.mem.sampler2.0", "njo.mem.wt1.0", "njo.mem.wt2.0"].every(k => pc.state[k]));
        check("stored value is compact PCM16", typeof pc.state["njo.mem.sampler1.0"].pcm16 === "string" && pc.state["njo.mem.sampler1.0"].pcm16.length < 3000 * 2 * 1.4);

        // new window + new view, same instance state (what a project reload gives us)
        const w2 = makeWebView();
        pc.sent.length = 0;
        const R = mount(w2, pc);
        await sleep(3500);
        check("restored sampler1 name", R._smpState[0] === "KICK");
        check("restored sampler2 name", R._s2State[0] === "HAT");
        check("restored wavetable 1 name", R._wt[0].state[0] === "SAW");
        check("restored wavetable 2 name", R._wt[1].state[0] === "PAD");
        check("sampler1 audio round-trips within 1/32767", R._store.get(0) && maxErr(R._store.get(0).data, s1) < 1 / 32767 + 1e-6, R._store.get(0) && maxErr(R._store.get(0).data, s1).toExponential(2));
        check("wavetable audio round-trips", R._wt[0].store.get(0) && maxErr(R._wt[0].store.get(0).data, wt) < 1 / 32767 + 1e-6);

        // the restore stream that goes to the DSP must reproduce the samples
        const gather = (ep, total) => {
            const out = new Float32Array(total);
            pc.sent.filter(m => m.ep === ep).forEach(m => { for (let i = 0; i < m.v.count; i++) out[m.v.offset + i] = m.v.data[i]; });
            return out;
        };
        const g1 = gather(EP.restore, s1.length);
        check("DSP restore stream for sampler 1 matches the kick", maxErr(g1, s1) < 1 / 32767 + 1e-6, "err=" + maxErr(g1, s1).toExponential(2));
        const g2 = gather(EP.s2, s2.length);
        check("DSP restore stream for sampler 2 matches the hat", maxErr(g2, s2) < 1 / 32767 + 1e-6);
        const gw = gather(EP.wt1, wt.length);
        check("DSP restore stream for wavetable 1 matches", maxErr(gw, wt) < 1 / 32767 + 1e-6);
        check("restore wrote nothing back that changes state", Object.keys(pc.state).length === 4);

        // clearing a memory removes it from the instance state
        R._store.delete(0); R._smpState[0] = null; R.persist(0);
        check("clearing removes the stored memory", !("njo.mem.sampler1.0" in pc.state));
    }

    // =============== scenario 3: vault slot markers are per instance ===============
    {
        const w = makeWebView();
        const pcA = makePC(), pcB = makePC();
        const A = mount(w, pcA), B = mount(w, pcB);
        await sleep(200);
        A._slotLib.smp = "vault-kick-id"; A.saveSlots();
        check("slot marker saved in A's state", pcA.state["njo.slots"] && pcA.state["njo.slots"].smp === "vault-kick-id");
        check("slot marker NOT in B's state", !("njo.slots" in pcB.state));
        check("B's slot assignments are empty", Object.values(B._slotLib).every(v => v === null));
    }

    // =============== scenario 4: host without stored-state support must still start ===============
    {
        const w = makeWebView();
        const pc = makePC();
        delete pc.requestFullStoredState; delete pc.sendStoredStateValue;
        let threw = null;
        try { const V = mount(w, pc); await sleep(150); V._smpState[0] = "X"; V._store.set(0, { name: "X", total: 10, data: ramp(10, 1) }); V.persist(0); } catch (e) { threw = e; }
        check("view starts and persist is harmless without stored-state API", !threw, threw && threw.message);
    }

    // =============== scenario 5: slow host (state arrives late) does not clobber a sample loaded meanwhile ===============
    {
        const w = makeWebView();
        const old = ramp(1000, 1);
        const pc = makePC({ "njo.mem.sampler1.0": { name: "OLD", total: 1000, pcm16: Buffer.from(Int16Array.from(old, v => Math.round(v * 32767)).buffer).toString("base64") } });
        pc.requestFullStoredState = cb => setTimeout(() => cb({ parameters: [], values: JSON.parse(JSON.stringify(pc.state)) }), 400);
        const V = mount(w, pc);
        const fresh = ramp(500, 7);
        V._smpState[0] = "FRESH"; V._store.set(0, { name: "FRESH", total: 500, data: fresh }); V.persist(0);   // user loads before state arrives
        await sleep(1500);
        check("a sample loaded before state arrived is kept", V._store.get(0).name === "FRESH" && pc.state["njo.mem.sampler1.0"].name === "FRESH");
    }

    console.log(failures ? "\n" + failures + " FAILED" : "\nALL PASSED");
    process.exit(failures ? 1 : 0);
})().catch(e => { console.error("HARNESS ERROR", e); process.exit(2); });
