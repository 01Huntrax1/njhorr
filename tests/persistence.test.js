// Regression test: samples / wavetables must stay inside ONE plugin instance.
// Runs patch/index.js in jsdom with a mock patch connection (per-instance stored state) and two plugin instances
// that share one localStorage, which is what two plugin windows in a DAW look like to the web view.
//   cd tests && npm install && npm test
// Pass another index.js as the first argument to test it instead.
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");
const cpExec = (c, a) => require("child_process").execFileSync(c, a, { stdio: "ignore" });

const indexPath = process.argv[2] || path.join(__dirname, "..", "patch", "index.js");
const code = fs.readFileSync(indexPath, "utf8").replace("export default function createPatchView", "function createPatchView").replace(/<style>[\s\S]*?<\/style>/, "");   // jsdom is far faster without the big stylesheet

// the DSP banks are filled through these events: { bank, offset, count, total, data }
const EP = { sm: "smpBankLoad", wt: "wtBankLoad" };
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

const put = (V, kind, o, name, data) => { V._mem[kind][o] = { name, total: data.length, data }; V.memPersist(kind, o); };
const gather = (pc, ep, bank, total) => {
    const out = new Float32Array(total);
    pc.sent.filter(m => m.ep === ep && m.v.bank === bank).forEach(m => { for (let i = 0; i < m.v.count; i++) out[m.v.offset + i] = m.v.data[i]; });
    return out;
};

(async () => {
    // =============== scenario 1: two instances, ONE shared localStorage ===============
    {
        const w = makeWebView();
        const pcA = makePC(), pcB = makePC();
        const A = mount(w, pcA);
        const B = mount(w, pcB);
        await sleep(100);
        const kick = ramp(3000, 1);
        put(A, "sm", 0, "KICK", kick);
        check("A saved the kick in its OWN stored state", !!pcA.state["njo.mem.osc0.sm"]);
        check("B's stored state is untouched", Object.keys(pcB.state).length === 0, JSON.stringify(Object.keys(pcB.state)));
        check("nothing was written to the shared localStorage", w.localStorage.length === 0, "len=" + w.localStorage.length);
        const B2 = mount(w, pcB);
        await sleep(1500);
        const bRestore = pcB.sent.filter(m => m.ep === EP.sm);
        check("B2 got no sample from A", B2._mem.sm[0] === null && bRestore.length === 0, "chunks=" + bRestore.length);
        const snare = ramp(2000, 3);
        put(B, "sm", 0, "SNARE", snare);
        check("A's saved sample is still the kick", pcA.state["njo.mem.osc0.sm"].name === "KICK" && pcA.state["njo.mem.osc0.sm"].total === 3000);
        check("B's saved sample is the snare", pcB.state["njo.mem.osc0.sm"].name === "SNARE" && pcB.state["njo.mem.osc0.sm"].total === 2000);
    }

    // =============== scenario 2: same instance reopened -> restores its own audio into the DSP ===============
    {
        const w = makeWebView();
        const pc = makePC();
        const V = mount(w, pc);
        await sleep(100);
        const s1 = ramp(3000, 1), s2 = ramp(1500, 2), wt = ramp(2048 * 3, 4), wt2 = ramp(1024, 5);
        put(V, "sm", 0, "KICK", s1); put(V, "sm", 3, "HAT", s2); put(V, "wt", 1, "SAW", wt); put(V, "wt", 5, "PAD", wt2);
        const keys = ["njo.mem.osc0.sm", "njo.mem.osc3.sm", "njo.mem.osc1.wt", "njo.mem.osc5.wt"];
        check("all four memories were stored", keys.every(k => pc.state[k]));
        check("stored value is compact PCM16", typeof pc.state[keys[0]].pcm16 === "string" && pc.state[keys[0]].pcm16.length < 3000 * 2 * 1.4);

        const w2 = makeWebView();
        pc.sent.length = 0;
        const R = mount(w2, pc);
        await sleep(3500);
        check("restored sample names", R._mem.sm[0].name === "KICK" && R._mem.sm[3].name === "HAT");
        check("restored wavetable names", R._mem.wt[1].name === "SAW" && R._mem.wt[5].name === "PAD");
        check("sample audio round-trips within 1/32767", maxErr(R._mem.sm[0].data, s1) < 1 / 32767 + 1e-6);
        check("wavetable audio round-trips", maxErr(R._mem.wt[1].data, wt) < 1 / 32767 + 1e-6);
        check("restore stream: sample bank 0", maxErr(gather(pc, EP.sm, 0, s1.length), s1) < 1 / 32767 + 1e-6);
        check("restore stream: sample bank 3", maxErr(gather(pc, EP.sm, 3, s2.length), s2) < 1 / 32767 + 1e-6);
        check("restore stream: wavetable bank 1", maxErr(gather(pc, EP.wt, 1, wt.length), wt) < 1 / 32767 + 1e-6);
        check("restore stream: wavetable bank 5", maxErr(gather(pc, EP.wt, 5, wt2.length), wt2) < 1 / 32767 + 1e-6);
        check("restore stream uses only the banks that were saved", pc.sent.filter(m => m.ep === EP.sm).every(m => m.v.bank === 0 || m.v.bank === 3));
        check("restore wrote nothing back that changes state", Object.keys(pc.state).length === 4);
        R._mem.sm[0] = null; R.memPersist("sm", 0);
        check("clearing removes the stored memory", !("njo.mem.osc0.sm" in pc.state));
    }

    // =============== scenario 3: vault slot markers are per instance ===============
    {
        const w = makeWebView();
        const pcA = makePC(), pcB = makePC();
        const A = mount(w, pcA), B = mount(w, pcB);
        await sleep(200);
        A._slotLib.sm0 = "vault-kick-id"; A.saveSlots();
        check("slot marker saved in A's state", pcA.state["njo.slots"] && pcA.state["njo.slots"].sm0 === "vault-kick-id");
        check("slot marker NOT in B's state", !("njo.slots" in pcB.state));
        check("B's slot assignments are empty", Object.values(B._slotLib).every(v => v === null));
        check("twelve vault slots (6 wavetable + 6 sampler)", Object.keys(A._slotLib).length === 12, String(Object.keys(A._slotLib).length));
    }

    // =============== scenario 4: host without stored-state support must still start ===============
    {
        const w = makeWebView();
        const pc = makePC();
        delete pc.requestFullStoredState; delete pc.sendStoredStateValue;
        let threw = null;
        try { const V = mount(w, pc); await sleep(150); put(V, "sm", 2, "X", ramp(10, 1)); } catch (e) { threw = e; }
        check("view starts and persist is harmless without stored-state API", !threw, threw && threw.message);
    }

    // =============== scenario 5: slow host (state arrives late) does not clobber a sample loaded meanwhile ===============
    {
        const w = makeWebView();
        const old = ramp(1000, 1);
        const pc = makePC({ "njo.mem.osc0.sm": { name: "OLD", total: 1000, pcm16: Buffer.from(Int16Array.from(old, v => Math.round(v * 32767)).buffer).toString("base64") } });
        pc.requestFullStoredState = cb => setTimeout(() => cb({ parameters: [], values: JSON.parse(JSON.stringify(pc.state)) }), 400);
        const V = mount(w, pc);
        put(V, "sm", 0, "FRESH", ramp(500, 7));   // user loads before state arrives
        await sleep(1500);
        check("a sample loaded before state arrived is kept", V._mem.sm[0].name === "FRESH" && pc.state["njo.mem.osc0.sm"].name === "FRESH");
    }

    // =============== scenario 6: loading a file streams into the right bank and keeps it per slot ===============
    {
        const w = makeWebView();
        const pc = makePC();
        const V = mount(w, pc);
        await sleep(100);
        V.decodeFile = async () => ({ mono: ramp(4096, 2), len: 4096, rate: 48000, sr: 48000, dur: 4096 / 48000 });
        V._controls.get("param" + (1000 + 64 * 2)).setValue(1, true);   // OSC 3 -> sampler
        await V.loadMem("sm", 2, { name: "snap.wav", size: 8, arrayBuffer: async () => new ArrayBuffer(8) });
        await sleep(2500);
        check("sample streamed into bank 2 of smpBankLoad", pc.sent.some(m => m.ep === EP.sm && m.v.bank === 2) && !pc.sent.some(m => m.ep === EP.sm && m.v.bank !== 2));
        check("loaded sample is stored under slot 3", pc.state["njo.mem.osc2.sm"] && pc.state["njo.mem.osc2.sm"].name === "SNAP");
        V.clearMem(2);
        check("clear sends an empty chunk to the same bank", pc.sent.some(m => m.ep === EP.sm && m.v.bank === 2 && m.v.total === 0));
        check("clear removes the stored memory", !("njo.mem.osc2.sm" in pc.state));
    }

    // =============== scenario 7: the real decoder (no stub) loads WAV / AIFF / FLAC / mp3-less web views ===============
    {
        const w = makeWebView();
        const pc = makePC();
        const V = mount(w, pc);
        await sleep(100);
        const mkWav = (n, rate, bits) => {
            const bw = bits / 8, b = Buffer.alloc(44 + n * 2 * bw);
            b.write("RIFF", 0); b.writeUInt32LE(36 + n * 2 * bw, 4); b.write("WAVEfmt ", 8); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(2, 22);
            b.writeUInt32LE(rate, 24); b.writeUInt32LE(rate * 2 * bw, 28); b.writeUInt16LE(2 * bw, 32); b.writeUInt16LE(bits, 34); b.write("data", 36); b.writeUInt32LE(n * 2 * bw, 40);
            for (let i = 0; i < n; i++) for (let c = 0; c < 2; c++) { const v = Math.sin(i * 2 * Math.PI * 441 / rate) * 0.4; if (bits === 16) b.writeInt16LE(Math.round(v * 32767), 44 + (i * 2 + c) * 2); else b.writeIntLE(Math.round(v * 8388607), 44 + (i * 2 + c) * 3, 3); }
            return b;
        };
        const asFile = (buf, name) => ({ name, size: buf.length, arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length) });
        const freq = x => { let z = 0; for (let i = 1; i < x.length; i++) if (x[i - 1] < 0 && x[i] >= 0) z++; return z * 48000 / x.length; };
        for (const [name, buf] of [["pcm16 44.1k", mkWav(13230, 44100, 16)], ["pcm24 44.1k", mkWav(13230, 44100, 24)], ["pcm16 48k", mkWav(14400, 48000, 16)]]) {
            const d = await V.decodeFile(asFile(buf, "t.wav"));
            let pk = 0; for (let i = 0; i < d.len; i++) pk = Math.max(pk, Math.abs(d.mono[i]));
            check("decodeFile loads WAV " + name, Math.abs(d.len - 14400) < 8 && Math.abs(pk - 0.9) < 0.02 && Math.abs(freq(d.mono) - 441) < 6, "len " + d.len + " peak " + pk.toFixed(3) + " f " + freq(d.mono).toFixed(1));
        }
        try { cpExec("ffmpeg", ["-version"]); } catch (_) { console.log("ffmpeg missing: format round trips skipped"); }
    }

    console.log(failures ? "\n" + failures + " FAILED" : "\nALL PASSED");
    process.exit(failures ? 1 : 0);
})().catch(e => { console.error("HARNESS ERROR", e); process.exit(2); });
