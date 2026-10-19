    // ======================================================================
    // Oscillator slots: sample / wavetable memory (one of each per slot), display, filter response
    // The UI keeps the audio data (in this instance's stored state) and streams it into the DSP banks.
    // ======================================================================
    memKey (kind, o) { return "njo.mem.osc" + o + "." + kind; }

    memEndpoint (kind) { return kind === "wt" ? "wtBankLoad" : "smpBankLoad"; }

    oscVal (o, key) {
        const id = oscId(o, key);
        const c = this._controls.get("param" + id);
        return c ? c.value : SPEC_BY_NUM.get(id).init;
    }

    srcKind (o) { return Math.round(this.oscVal(o, "type")) === 1 ? "sm" : "wt"; }

    setMgr (text) {
        const el = this.querySelector(".mgr-status");
        if (el) el.textContent = text;
    }

    loadMemStore () {
        for (const kind of ["wt", "sm"]) {
            for (let o = 0; o < OSC_N; o++) {
                if (this._mem[kind][o]) continue;   // loaded by the user since startup: newer than the saved copy
                try { const m = decodeMem(this.kvGet(this.memKey(kind, o)), kind === "wt" ? "TABLE" : "SAMPLE"); if (m) this._mem[kind][o] = m; } catch (_) {}
            }
        }
    }

    memPersist (kind, o) {
        const s = this._mem[kind][o];
        try {
            if (!s) { this.kvRemove(this.memKey(kind, o)); return; }
            this.kvSet(this.memKey(kind, o), encodeMem(s));
        } catch (_) { this.setMgr("STORAGE FULL"); }
    }

    memCancel (kind, o) {
        const t = this._memTimer[kind][o];
        if (t) { clearInterval(t); this._memTimer[kind][o] = null; }
    }

    // streams one memory into its DSP bank in chunks (the event queue is small)
    memStream (kind, o, s, done) {
        this.memCancel(kind, o);
        const ep = this.memEndpoint(kind), total = s.total;
        let offset = 0;
        this._memTimer[kind][o] = setInterval(() => {
            for (let k = 0; k < 6 && offset < total; k++) {
                const count = Math.min(CHUNK, total - offset);
                const data = new Array(CHUNK).fill(0);
                for (let i = 0; i < count; i++) data[i] = s.data[offset + i];
                this.pc.sendEventOrValue(ep, { bank: o, offset, count, total, data });
                offset += count;
            }
            if (this.srcKind(o) === kind) this.setDz(o, "LOADING " + Math.round(offset / total * 100) + "%", "busy");
            if (offset >= total) { this.memCancel(kind, o); if (done) done(); }
        }, 6);
    }

    // UI -> DSP: stream every saved memory back, staggered
    startMemRestore () {
        let n = 0;
        for (const kind of ["wt", "sm"]) {
            for (let o = 0; o < OSC_N; o++) {
                const s = this._mem[kind][o];
                if (!s) continue;
                this._memStart.push(setTimeout(() => this.memStream(kind, o, s, () => this.updateOscUi(o)), 150 * n++));
            }
        }
    }

    setDz (o, text, cls) {
        const dz = this.querySelector('.dz-osc[data-o="' + o + '"]');
        if (!dz) return;
        dz.querySelector(".dz-txt").textContent = text;
        dz.classList.toggle("loaded", cls === "loaded");
        dz.classList.toggle("busy", cls === "busy");
        dz.classList.toggle("err", cls === "err");
    }

    pickFrameIndex (len) {
        if (len % 4096 === 0) return 4;
        if (len % 2048 === 0) return 3;
        if (len >= 2048) return 3;
        const rest = [2, 1, 0];
        for (let i = 0; i < rest.length; i++) if (len % FRAME_SIZES[rest[i]] === 0) return rest[i];
        let k = 0;
        for (let j = 0; j < FRAME_SIZES.length; j++) if (FRAME_SIZES[j] <= len) k = j;
        return k;
    }

    async loadMem (kind, o, file, libId) {
        this.memCancel(kind, o);
        this.setDz(o, "DECODING...", "busy");
        try {
            const dec = await this.decodeFile(file);
            this.libTrack(kind + o, file, libId, dec);
            const name = (file.name || (kind === "wt" ? "TABLE" : "SAMPLE")).replace(/\.[^.]+$/, "").slice(0, 14).toUpperCase();
            const s = { name, total: dec.len, data: dec.mono };
            if (kind === "wt") { const fc = this._controls.get("param" + oscId(o, "wsize")); if (fc) fc.setValue(this.pickFrameIndex(s.total), true); }
            this.memStream(kind, o, s, () => {
                this._mem[kind][o] = s;
                this.memPersist(kind, o);
                this.updateOscUi(o);
                this.setMgr("LOADED " + name);
                const lvl = this._controls.get("param" + oscId(o, "level"));
                if (lvl && lvl.value < 0.05) lvl.setValue(0.8, true);
            });
        } catch (err) {
            this.memCancel(kind, o);
            this.setDz(o, "UNSUPPORTED FILE", "err");
        }
    }

    clearMem (o) {
        const kind = this.srcKind(o);
        this.memCancel(kind, o);
        this.pc.sendEventOrValue(this.memEndpoint(kind), { bank: o, offset: 0, count: 0, total: 0, data: new Array(CHUNK).fill(0) });
        this.libUntrack(kind + o);
        this._mem[kind][o] = null;
        this.memPersist(kind, o);
        this.updateOscUi(o);
        this.setMgr("OSC " + (o + 1) + " CLEARED");
    }

    buildOscPages () {
        for (let o = 0; o < OSC_N; o++) {
            const dz = this.querySelector('.dz-osc[data-o="' + o + '"]');
            if (!dz) continue;
            dz.addEventListener("dragover", ev => { ev.preventDefault(); dz.classList.add("over"); });
            dz.addEventListener("dragleave", () => dz.classList.remove("over"));
            dz.addEventListener("drop", ev => {
                ev.preventDefault(); dz.classList.remove("over");
                const f = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
                if (f) this.loadMem(this.srcKind(o), o, f);
            });
            dz.addEventListener("click", () => {
                const inp = document.createElement("input");
                inp.type = "file"; inp.accept = "audio/*,.wav,.aif,.aiff,.mp3,.ogg,.flac";
                inp.onchange = () => { if (inp.files && inp.files[0]) this.loadMem(this.srcKind(o), o, inp.files[0]); };
                inp.click();
            });
            const clr = dz.querySelector(".dz-clr");
            if (clr) clr.addEventListener("click", ev => { ev.stopPropagation(); this.clearMem(o); });
            const lib = this.querySelector('.dz-lib[data-o="' + o + '"]');
            if (lib) lib.addEventListener("click", () => { lib.dataset.slot = this.srcKind(o) + o; });
            this.updateOscUi(o);
        }
        this._oscReady = true;
    }

    // refreshes everything that depends on the source type / engine of one slot
    updateOscUi (o) {
        const type = Math.max(0, Math.min(2, Math.round(this.oscVal(o, "type"))));
        const pg = this.querySelector(".p-o" + o);
        if (pg) pg.setAttribute("data-src", String(type));
        this.querySelectorAll('[data-o="' + o + '"][data-show]').forEach(el => {
            el.style.display = el.dataset.show.split(",").indexOf(String(type)) >= 0 ? "" : "none";
        });
        const kind = type === 1 ? "sm" : "wt";
        const s = this._mem[kind][o];
        if (!this._memTimer[kind][o]) this.setDz(o, s ? s.name : (kind === "wt" ? WT_DZ_EMPTY : SMP_DZ_EMPTY), s ? "loaded" : "");
        const eng = Math.max(0, Math.min(PLAITS_ENGINES.length - 1, Math.round(this.oscVal(o, "pleng"))));
        ["pharm", "ptimb", "pmorph"].forEach((key, i) => {
            const lbl = this.querySelector(".n" + oscId(o, key) + " .lbl");
            if (lbl) lbl.textContent = PLAITS_PARAMS[eng][i];
        });
        this.drawOsc(o);
        this.drawOscFlt(o);
    }

    onOscValue (o, k) {
        if (!this._oscReady) return;   // controls are still being created
        if (k === OSC_K.type || k === OSC_K.pleng) { this.updateOscUi(o); return; }
        if (k === OSC_K.wpos || k === OSC_K.wsize || k === OSC_K.w1m || k === OSC_K.w1a || k === OSC_K.w2m || k === OSC_K.w2a
            || k === OSC_K.sstart || k === OSC_K.sloop || k === OSC_K.root) this.drawOsc(o);
        if (k >= OSC_K.fon && k <= OSC_K.fkey) this.drawOscFlt(o);
    }

    // interpolated single cycle of slot o at the current position / frame size
    wtCycle (o, W) {
        const s = this._mem.wt[o];
        if (!s || s.total < 2) return null;
        const fl = Math.max(2, Math.min(FRAME_SIZES[Math.max(0, Math.min(4, Math.round(this.oscVal(o, "wsize"))))], s.total));
        const nF = Math.max(1, Math.floor(s.total / fl));
        const p = Math.max(0, Math.min(1, this.oscVal(o, "wpos"))) * (nF - 1);
        const fa = Math.max(0, Math.min(nF - 1, Math.floor(p)));
        const fb = Math.min(nF - 1, fa + 1);
        const ff = p - fa;
        const out = new Float32Array(W);
        for (let x = 0; x < W; x++) {
            const i = Math.min(fl - 1, Math.floor(x / W * fl));
            out[x] = (s.data[fa * fl + i] || 0) * (1 - ff) + (s.data[fb * fl + i] || 0) * ff;
        }
        let mean = 0;
        for (let x = 0; x < W; x++) mean += out[x];
        mean /= W;
        for (let x = 0; x < W; x++) out[x] -= mean;   // the DSP removes the DC of every frame
        return { cyc: out, nF, frame: p + 1, name: s.name };
    }

    // the same cycle after both warp slots (null when no warp is active)
    warpCycle (cyc, ws) {
        const m1 = ws[0], a1 = ws[1], m2 = ws[2], a2 = ws[3];
        if (m1 === 0 && m2 === 0) return null;
        const W = cyc.length;
        const out = new Float32Array(W);
        let mean = 0;
        for (let x = 0; x < W; x++) {
            let rp = x / W;
            if (m1 >= 1 && m1 <= 6) rp = warpPhase(m1, a1, rp);
            if (m2 >= 1 && m2 <= 6) rp = warpPhase(m2, a2, rp);
            rp = Math.max(0, Math.min(0.99999, rp));
            const fi = rp * W, i0 = Math.floor(fi), fr = fi - i0;
            let y = cyc[i0] * (1 - fr) + cyc[(i0 + 1) % W] * fr;
            if (m1 >= 7) y = warpAmp(m1, a1, y);
            if (m2 >= 7) y = warpAmp(m2, a2, y);
            out[x] = y;
            mean += y;
        }
        mean /= W;
        for (let x = 0; x < W; x++) out[x] -= mean;
        return out;
    }

    // HUD style frame shared by the display canvases
    hudFrame (cv) {
        const ctx = cv.getContext("2d");
        if (!ctx) return null;
        const W = cv.width, H = cv.height;
        ctx.clearRect(0, 0, W, H);
        ctx.fillStyle = "#0d0404";
        ctx.fillRect(0, 0, W, H);
        ctx.strokeStyle = "rgba(255,59,48,0.10)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let gx = 0; gx <= W; gx += W / 16) { ctx.moveTo(gx, 0); ctx.lineTo(gx, H); }
        for (let gy = 0; gy <= H; gy += H / 4) { ctx.moveTo(0, gy); ctx.lineTo(W, gy); }
        ctx.stroke();
        ctx.strokeStyle = "rgba(255,59,48,0.38)";
        ctx.beginPath(); ctx.moveTo(0, H / 2); ctx.lineTo(W, H / 2); ctx.stroke();
        ctx.strokeStyle = "rgba(255,80,66,0.85)";
        ctx.lineWidth = 2;
        const bl = 16, bm = 3;
        ctx.beginPath();
        ctx.moveTo(bm, bm + bl); ctx.lineTo(bm, bm); ctx.lineTo(bm + bl, bm);
        ctx.moveTo(W - bm - bl, bm); ctx.lineTo(W - bm, bm); ctx.lineTo(W - bm, bm + bl);
        ctx.moveTo(bm, H - bm - bl); ctx.lineTo(bm, H - bm); ctx.lineTo(bm + bl, H - bm);
        ctx.moveTo(W - bm - bl, H - bm); ctx.lineTo(W - bm, H - bm); ctx.lineTo(W - bm, H - bm - bl);
        ctx.stroke();
        ctx.lineWidth = 1;
        return { ctx, W, H };
    }

    drawOsc (o) {
        const cv = this.querySelector('.osc-canvas[data-o="' + o + '"]');
        const info = this.querySelector('.osc-info[data-o="' + o + '"]');
        if (!cv) return;
        const fr = this.hudFrame(cv);
        if (!fr) return;
        const { ctx, W, H } = fr;
        const type = Math.round(this.oscVal(o, "type"));
        const trace = (arr, color, lw) => {
            ctx.strokeStyle = color; ctx.lineWidth = lw;
            ctx.shadowColor = "rgba(255,59,48,0.9)"; ctx.shadowBlur = lw > 1 ? 8 : 0;
            ctx.beginPath();
            for (let x = 0; x < W; x++) {
                const y = H / 2 - Math.max(-1.2, Math.min(1.2, arr[x])) * (H / 2 - 4);
                if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.stroke();
            ctx.shadowBlur = 0;
        };
        if (type === 0) {
            const r = this.wtCycle(o, W);
            if (!r) { if (info) info.textContent = "NO WAVETABLE LOADED"; return; }
            const ws = [Math.round(this.oscVal(o, "w1m")), this.oscVal(o, "w1a"), Math.round(this.oscVal(o, "w2m")), this.oscVal(o, "w2a")];
            const warped = this.warpCycle(r.cyc, ws);
            let tag = "";
            if (warped) tag = " / WARP " + [0, 2].filter(k => ws[k] > 0).map(k => WARP_MODES[ws[k]]).join(" + ");
            if (info) info.textContent = r.name + " / FRAME " + r.frame.toFixed(1) + " OF " + r.nF + tag;
            if (warped) { trace(r.cyc, "rgba(255,150,140,0.40)", 1); trace(warped, "#ff7a45", 2); }
            else trace(r.cyc, "#ff3b30", 2);
        } else if (type === 1) {
            const s = this._mem.sm[o];
            if (!s) { if (info) info.textContent = "NO SAMPLE LOADED"; return; }
            const n = s.total, step = Math.max(1, Math.floor(n / W));
            const start = Math.max(0, Math.min(1, this.oscVal(o, "sstart")));
            ctx.fillStyle = "rgba(255,59,48,0.12)";
            ctx.fillRect(0, 0, W * start, H);
            ctx.strokeStyle = "#ff3b30"; ctx.lineWidth = 1.5;
            ctx.beginPath();
            for (let x = 0; x < W; x++) {
                const a = Math.floor(x / W * n);
                let mn = 1, mx = -1;
                for (let i = a; i < Math.min(n, a + step); i++) { const v = s.data[i]; if (v < mn) mn = v; if (v > mx) mx = v; }
                if (mx < mn) { mn = mx = 0; }
                ctx.moveTo(x, H / 2 - mx * (H / 2 - 4)); ctx.lineTo(x, H / 2 - mn * (H / 2 - 4));
            }
            ctx.stroke();
            ctx.strokeStyle = "rgba(255,200,190,0.7)"; ctx.setLineDash([4, 4]);
            ctx.beginPath(); ctx.moveTo(W * start, 0); ctx.lineTo(W * start, H); ctx.stroke();
            ctx.setLineDash([]);
            if (info) info.textContent = s.name + " / " + (n / 48000).toFixed(2) + " S" + (this.oscVal(o, "sloop") > 0.5 ? " / LOOP" : "");
        } else {
            const eng = Math.max(0, Math.min(PLAITS_ENGINES.length - 1, Math.round(this.oscVal(o, "pleng"))));
            ctx.fillStyle = "rgba(255,120,100,0.85)";
            ctx.font = "bold " + Math.round(H * 0.2) + "px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(PLAITS_ENGINES[eng].toUpperCase(), W / 2, H / 2 + H * 0.05);
            ctx.font = "bold " + Math.round(H * 0.1) + "px sans-serif";
            ctx.fillStyle = "rgba(255,200,190,0.5)";
            ctx.fillText("PLAITS / " + (eng + 1) + " OF " + PLAITS_ENGINES.length, W / 2, H / 2 + H * 0.25);
            ctx.textAlign = "left";
            if (info) info.textContent = PLAITS_ENGINES[eng] + " / " + PLAITS_PARAMS[eng].join(" - ");
        }
    }

    // magnitude response (complex) of the filter of slot o on a log frequency grid
    oscFltCurve (o, N, sweep) {
        const ft = Math.round(this.oscVal(o, "ftype")), fc = this.oscVal(o, "fcut"), res = this.oscVal(o, "fres");
        const out = [];
        for (let i = 0; i < N; i++) out.push(filterH(ft, fc, res, 20 * Math.pow(1000, i / (N - 1)), sweep));
        return out;
    }

    drawOscFlt (o) {
        const cv = this.querySelector('.flt-canvas[data-o="' + o + '"]');
        if (!cv) return;
        const fr = this.fltFrame(cv);
        if (!fr) return;
        const N = 220, ft = Math.round(this.oscVal(o, "ftype"));
        if (this.oscVal(o, "fon") < 0.5) { this.fltTrace(fr, this.oscFltCurve(o, N), "rgba(180,170,165,0.45)", 1.5, false, true); return; }
        if (ft === 28 || ft === 29) {
            this.fltTrace(fr, this.oscFltCurve(o, N, 0.5), "rgba(255,150,130,0.35)", 1, false, true);
            this.fltTrace(fr, this.oscFltCurve(o, N, 1.5), "rgba(255,150,130,0.35)", 1, false, true);
        }
        this.fltTrace(fr, this.oscFltCurve(o, N), "#ff3b30", 2.5, true, false);
        this.fltCutMark(fr, this.oscVal(o, "fcut"));
    }

    drawAllOsc () { for (let o = 0; o < OSC_N; o++) { this.drawOsc(o); this.drawOscFlt(o); } }

    // ---------- page HTML ----------
    oscPageHTML (o) {
        const c = key => this.controlHTML(oscId(o, key), true);
        const sh = (list, inner, cls) => `<div class="${cls || "cgrid"}" data-o="${o}" data-show="${list}">${inner}</div>`;
        const src = `<section class="card o-src"><h2>OSC ${o + 1} Source</h2>
            <div class="o-type">${c("type")}</div>
            <canvas class="osc-canvas" data-o="${o}" width="640" height="190"></canvas>
            <div class="osc-info" data-o="${o}">--</div>
            <div class="o-mem" data-o="${o}" data-show="0,1"><div class="dz dz-osc" data-o="${o}"><span class="dz-txt"></span><span class="dz-clr" title="Clear this memory">&times;</span></div><button type="button" class="pb dz-lib" data-o="${o}" data-slot="wt${o}" title="Open the sound vault">VAULT</button></div>
            ${sh("0", ["wpos", "wsize", "w1m", "w1a", "w2m", "w2a"].map(c).join(""), "cgrid o-g2")}
            ${sh("1", ["root", "sstart", "sloop"].map(c).join(""), "cgrid o-g3")}
            ${sh("2", ["pleng", "pharm", "ptimb", "pmorph"].map(c).join(""), "cgrid o-g3 o-pl")}
          </section>`;
        const tune = `<section class="card o-tune"><h2>Tune</h2>
            <div class="cgrid o-g2">${["oct", "semi", "fine", "track"].map(c).join("")}${sh("0,1", ["phase", "rphase"].map(c).join(""), "o-sub o-g2")}</div>
            ${sh("0", "<div class=\"o-uh\">Unison</div>" + ["uvox", "udet", "ublend", "uwid", "ustyle"].map(c).join(""), "cgrid o-g2 o-uni")}
          </section>`;
        const flt = `<section class="card o-flt"><h2>Filter</h2>
            <canvas class="flt-canvas" data-o="${o}" width="600" height="200"></canvas>
            <div class="cgrid o-g3">${["fon", "ftype"].map(c).join("")}${["fcut", "fres", "fdrv", "fkey", "feg", "fvel", "fatk", "fdec", "fsus", "frel"].map(c).join("")}</div>
          </section>`;
        const out = `<section class="card o-out"><h2>Distortion / Out</h2>
            <div class="cgrid o-g2">${["dtype", "ddrv", "dmix"].map(c).join("")}</div>
            <h2 class="o-h2">Output</h2>
            <div class="cgrid o-g2">${["level", "pan", "out"].map(c).join("")}</div>
          </section>`;
        return src + tune + flt + out;
    }

    fmPageHTML () {
        let head = `<div class="fm-corner">MOD \u2193 / CARRIER \u2192</div>` + Array.from({ length: OSC_N }, (_, d) => `<div class="fm-h">OSC ${d + 1}</div>`).join("");
        let rows = "";
        for (let s = 0; s < OSC_N; s++) {
            rows += `<div class="fm-h fm-r">OSC ${s + 1}</div>`;
            for (let d = 0; d < OSC_N; d++) rows += `<div class="fm-c${s === d ? " fb" : ""}">${this.controlHTML(fmId(s, d), true)}</div>`;
        }
        return `<section class="card fm-card"><h2>FM Matrix</h2><div class="fm-grid">${head}${rows}</div><div class="fm-note">Row = modulator, column = carrier (phase modulation). The diagonal is self feedback. A modulator with Level 0 still modulates, so you can use it as a pure FM operator. Level, pan and output of every oscillator are on its own page.</div></section>`;
    }

    globalPageHTML () {
        const k = ids => ids.map(i => this.controlHTML(i, true)).join("");
        return this.card("Voice", [2, 3, 63], "g-voice") + this.card("Amp EG", [18, 19, 20, 21, 22], "g-amp") + this.card("Pitch EG", [45, 46], "g-peg")
            + this.card("Output", [29, 190, 36, 880, 881, 522], "g-out");
    }
