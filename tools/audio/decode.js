// Native audio decoders for the sampler / wavetable loader: no dependency on what the plugin's web view can decode.
// decodeNative(arrayBuffer, maxFrames) -> { ch: [Float32Array, ...], rate, format } or null when the container is not recognised.
// Containers: WAV (PCM 8-32, float, A-law, mu-law, IMA / MS ADPCM, extensible, RF64), Wave64, AIFF / AIFF-C (PCM, float, sowt, ulaw, alaw),
// Sun / NeXT .au, Core Audio .caf (lpcm, ulaw, alaw), FLAC. Anything else (mp3, ogg, m4a ...) is left to the web view's decoder.
const AudioDecode = (() => {
    const fcc = (u8, o) => String.fromCharCode(u8[o], u8[o + 1], u8[o + 2], u8[o + 3]);
    const ALAW = new Float32Array(256), ULAW = new Float32Array(256);
    for (let i = 0; i < 256; i++) {
        let a = i ^ 0x55, s = a & 0x80 ? 1 : -1, e = (a & 0x70) >> 4, m = a & 0x0f;
        let v = e === 0 ? (m << 4) + 8 : ((m << 4) + 0x108) << (e - 1);
        ALAW[i] = s * v / 32768;
        let u = ~i & 0xff; s = u & 0x80 ? -1 : 1; e = (u & 0x70) >> 4; m = u & 0x0f;
        v = (((m << 3) + 0x84) << e) - 0x84;
        ULAW[i] = s * v / 32768;
    }
    const limit = (frames, maxFrames) => (maxFrames > 0 ? Math.min(frames, maxFrames) : frames);

    // interleaved PCM / float -> channel arrays. kind: "int" | "uint8" | "float" | "alaw" | "ulaw"
    function pcm(dv, off, bytes, nch, bps, kind, le, maxFrames) {
        const bw = kind === "alaw" || kind === "ulaw" ? 1 : bps >> 3;
        const frames = limit(Math.floor(bytes / (bw * nch)), maxFrames);
        const ch = [];
        for (let c = 0; c < nch; c++) ch.push(new Float32Array(frames));
        let p = off;
        for (let i = 0; i < frames; i++) for (let c = 0; c < nch; c++, p += bw) {
            let v;
            if (kind === "alaw") v = ALAW[dv.getUint8(p)];
            else if (kind === "ulaw") v = ULAW[dv.getUint8(p)];
            else if (kind === "uint8") v = (dv.getUint8(p) - 128) / 128;
            else if (kind === "float") v = bw === 4 ? dv.getFloat32(p, le) : dv.getFloat64(p, le);
            else if (bw === 1) v = dv.getInt8(p) / 128;
            else if (bw === 2) v = dv.getInt16(p, le) / 32768;
            else if (bw === 3) { const x = le ? dv.getUint8(p) | (dv.getUint8(p + 1) << 8) | (dv.getUint8(p + 2) << 16) : (dv.getUint8(p) << 16) | (dv.getUint8(p + 1) << 8) | dv.getUint8(p + 2); v = ((x << 8) >> 8) / 8388608; }
            else v = dv.getInt32(p, le) / 2147483648;
            ch[c][i] = v;
        }
        return ch;
    }

    // ---- ADPCM (inside WAV) ----
    const IMA_STEP = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767];
    const IMA_IDX = [-1, -1, -1, -1, 2, 4, 6, 8];
    function imaAdpcm(dv, off, bytes, nch, blockAlign, spb, maxFrames) {
        const out = []; for (let c = 0; c < nch; c++) out.push([]);
        const blocks = Math.floor(bytes / blockAlign);
        for (let b = 0; b < blocks; b++) {
            const bo = off + b * blockAlign;
            const pred = [], idx = [];
            for (let c = 0; c < nch; c++) { pred.push(dv.getInt16(bo + 4 * c, true)); idx.push(Math.min(88, dv.getUint8(bo + 4 * c + 2))); out[c].push(pred[c] / 32768); }
            const dec = (c, nib) => {
                const step = IMA_STEP[idx[c]];
                const diff = ((2 * (nib & 7) + 1) * step) >> 3;
                pred[c] = Math.max(-32768, Math.min(32767, pred[c] + (nib & 8 ? -diff : diff)));
                idx[c] = Math.max(0, Math.min(88, idx[c] + IMA_IDX[nib & 7]));
                out[c].push(pred[c] / 32768);
            };
            let p = bo + 4 * nch;
            const end = bo + blockAlign;
            while (p + 4 * nch <= end) {
                // each channel gets 4 bytes (8 samples) in turn
                for (let c = 0; c < nch; c++) for (let k = 0; k < 4; k++) { const v = dv.getUint8(p + c * 4 + k); dec(c, v & 15); dec(c, v >> 4); }
                p += 4 * nch;
            }
            if (maxFrames > 0 && out[0].length >= maxFrames) break;
        }
        return out.map(a => Float32Array.from(a.length > limit(a.length, maxFrames) ? a.slice(0, limit(a.length, maxFrames)) : a));
    }
    const MS_ADAPT = [230, 230, 230, 230, 307, 409, 512, 614, 768, 614, 512, 409, 307, 230, 230, 230];
    function msAdpcm(dv, off, bytes, nch, blockAlign, coefs, maxFrames) {
        const out = []; for (let c = 0; c < nch; c++) out.push([]);
        const blocks = Math.floor(bytes / blockAlign);
        for (let b = 0; b < blocks; b++) {
            let p = off + b * blockAlign;
            const end = p + blockAlign;
            const pi = [], delta = [], s1 = [], s2 = [];
            for (let c = 0; c < nch; c++) { pi.push(Math.min(coefs.length - 1, dv.getUint8(p++))); }
            for (let c = 0; c < nch; c++) { delta.push(dv.getInt16(p, true)); p += 2; }
            for (let c = 0; c < nch; c++) { s1.push(dv.getInt16(p, true)); p += 2; }
            for (let c = 0; c < nch; c++) { s2.push(dv.getInt16(p, true)); p += 2; }
            for (let c = 0; c < nch; c++) out[c].push(s2[c] / 32768);
            for (let c = 0; c < nch; c++) out[c].push(s1[c] / 32768);
            const dec = (c, nib) => {
                const co = coefs[pi[c]];
                let v = ((s1[c] * co[0] + s2[c] * co[1]) >> 8) + (nib >= 8 ? nib - 16 : nib) * delta[c];
                v = Math.max(-32768, Math.min(32767, v));
                s2[c] = s1[c]; s1[c] = v;
                delta[c] = Math.max(16, (MS_ADAPT[nib] * delta[c]) >> 8);
                out[c].push(v / 32768);
            };
            while (p < end) {
                const v = dv.getUint8(p++);
                if (nch === 1) { dec(0, v >> 4); dec(0, v & 15); }
                else { dec(0, v >> 4); dec(1, v & 15); }
            }
            if (maxFrames > 0 && out[0].length >= maxFrames) break;
        }
        return out.map(a => Float32Array.from(maxFrames > 0 && a.length > maxFrames ? a.slice(0, maxFrames) : a));
    }

    // ---- WAV / RF64 / Wave64 ----
    function wav(buf, maxFrames) {
        const u8 = new Uint8Array(buf), dv = new DataView(buf), id = fcc(u8, 0);
        const w64 = id === "riff" && u8.length > 40 && fcc(u8, 24) === "wave";
        if (!(id === "RIFF" || id === "RF64" || id === "BW64") && !w64) return null;
        if (!w64 && fcc(u8, 8) !== "WAVE") return null;
        let fmt = null, dataOff = -1, dataLen = 0, ds64 = 0;
        if (w64) {
            let p = 40;
            while (p + 24 <= u8.length) {
                const cid = fcc(u8, p), sz = Number(dv.getBigUint64(p + 16, true)) - 24;
                const body = p + 24;
                if (cid === "fmt ") fmt = body; else if (cid === "data") { dataOff = body; dataLen = Math.min(sz, u8.length - body); break; }
                p = body + sz + ((8 - (sz & 7)) & 7);
            }
        } else {
            let p = 12;
            while (p + 8 <= u8.length) {
                const cid = fcc(u8, p); let sz = dv.getUint32(p + 4, true);
                const body = p + 8;
                if (cid === "ds64") ds64 = Number(dv.getBigUint64(body + 8, true));
                else if (cid === "fmt ") fmt = body;
                else if (cid === "data") {
                    if (sz === 0xffffffff && ds64) sz = ds64;
                    dataOff = body; dataLen = Math.min(sz, u8.length - body); if (sz === 0xffffffff || sz === 0) dataLen = u8.length - body;
                    break;
                }
                p = body + sz + (sz & 1);
            }
        }
        if (fmt === null || dataOff < 0) return null;
        let tag = dv.getUint16(fmt, true); const nch = dv.getUint16(fmt + 2, true), rate = dv.getUint32(fmt + 4, true);
        const blockAlign = dv.getUint16(fmt + 12, true), bps = dv.getUint16(fmt + 14, true);
        const cb = w64 ? 0 : 0, ext = fmt + 16 <= u8.length - 2 ? dv.getUint16(fmt + 16, true) : 0;
        if (tag === 0xfffe && ext >= 22) tag = dv.getUint16(fmt + 24, true);
        if (!nch || !rate) return null;
        let ch;
        if (tag === 1) ch = pcm(dv, dataOff, dataLen, nch, bps === 8 ? 8 : Math.ceil(bps / 8) * 8, bps === 8 ? "uint8" : "int", true, maxFrames);
        else if (tag === 3) ch = pcm(dv, dataOff, dataLen, nch, bps, "float", true, maxFrames);
        else if (tag === 6) ch = pcm(dv, dataOff, dataLen, nch, 8, "alaw", true, maxFrames);
        else if (tag === 7) ch = pcm(dv, dataOff, dataLen, nch, 8, "ulaw", true, maxFrames);
        else if (tag === 0x11) ch = imaAdpcm(dv, dataOff, dataLen, nch, blockAlign, ext >= 2 ? dv.getUint16(fmt + 18, true) : 0, maxFrames);
        else if (tag === 2) {
            const nc = dv.getUint16(fmt + 20, true), coefs = [];
            for (let i = 0; i < nc; i++) coefs.push([dv.getInt16(fmt + 22 + 4 * i, true), dv.getInt16(fmt + 24 + 4 * i, true)]);
            if (!coefs.length) coefs.push([256, 0], [512, -256], [0, 0], [192, 64], [240, 0], [460, -208], [392, -232]);
            ch = msAdpcm(dv, dataOff, dataLen, nch, blockAlign, coefs, maxFrames);
        } else return null;   // mp3 in wav, etc.: leave to the web view
        return { ch, rate, format: w64 ? "Wave64" : "WAV" };
    }

    // ---- AIFF / AIFF-C ----
    function ext80(dv, o) {
        const se = dv.getUint16(o, false), hi = dv.getUint32(o + 2, false), lo = dv.getUint32(o + 6, false);
        const e = (se & 0x7fff) - 16383;
        return (se & 0x8000 ? -1 : 1) * (hi * Math.pow(2, e - 31) + lo * Math.pow(2, e - 63));
    }
    function aiff(buf, maxFrames) {
        const u8 = new Uint8Array(buf), dv = new DataView(buf);
        if (fcc(u8, 0) !== "FORM") return null;
        const ty = fcc(u8, 8);
        if (ty !== "AIFF" && ty !== "AIFC") return null;
        let nch = 0, frames = 0, bits = 0, rate = 0, comp = "NONE", ssnd = -1, ssndLen = 0;
        let p = 12;
        while (p + 8 <= u8.length) {
            const cid = fcc(u8, p), sz = dv.getUint32(p + 4, false), body = p + 8;
            if (cid === "COMM") {
                nch = dv.getUint16(body, false); frames = dv.getUint32(body + 2, false); bits = dv.getUint16(body + 6, false); rate = ext80(dv, body + 8);
                if (ty === "AIFC" && sz >= 22) comp = fcc(u8, body + 18);
            } else if (cid === "SSND") { const o = dv.getUint32(body, false); ssnd = body + 8 + o; ssndLen = Math.min(sz - 8 - o, u8.length - ssnd); break; }
            p = body + sz + (sz & 1);
        }
        if (ssnd < 0 || !nch || !rate) return null;
        const c = comp.toLowerCase();
        let ch;
        if (c === "none" || c === "twos" || c === "in24" || c === "in32" || c === "42ni") ch = pcm(dv, ssnd, ssndLen, nch, Math.ceil(bits / 8) * 8, "int", false, maxFrames);
        else if (c === "sowt") ch = pcm(dv, ssnd, ssndLen, nch, Math.ceil(bits / 8) * 8, "int", true, maxFrames);
        else if (c === "raw ") ch = pcm(dv, ssnd, ssndLen, nch, 8, "uint8", false, maxFrames);
        else if (c === "fl32") ch = pcm(dv, ssnd, ssndLen, nch, 32, "float", false, maxFrames);
        else if (c === "fl64") ch = pcm(dv, ssnd, ssndLen, nch, 64, "float", false, maxFrames);
        else if (c === "ulaw") ch = pcm(dv, ssnd, ssndLen, nch, 8, "ulaw", false, maxFrames);
        else if (c === "alaw") ch = pcm(dv, ssnd, ssndLen, nch, 8, "alaw", false, maxFrames);
        else return null;
        return { ch, rate, format: ty };
    }

    // ---- Sun / NeXT .au ----
    function au(buf, maxFrames) {
        const u8 = new Uint8Array(buf), dv = new DataView(buf);
        const m = fcc(u8, 0);
        if (m !== ".snd" && m !== "dns.") return null;
        const le = m === "dns.";
        const off = dv.getUint32(4, le), enc = dv.getUint32(12, le), rate = dv.getUint32(16, le), nch = dv.getUint32(20, le);
        let size = dv.getUint32(8, le); if (size === 0xffffffff || off + size > u8.length) size = u8.length - off;
        let ch;
        if (enc === 1) ch = pcm(dv, off, size, nch, 8, "ulaw", le, maxFrames);
        else if (enc === 2) ch = pcm(dv, off, size, nch, 8, "int", le, maxFrames);
        else if (enc === 3) ch = pcm(dv, off, size, nch, 16, "int", le, maxFrames);
        else if (enc === 4) ch = pcm(dv, off, size, nch, 24, "int", le, maxFrames);
        else if (enc === 5) ch = pcm(dv, off, size, nch, 32, "int", le, maxFrames);
        else if (enc === 6) ch = pcm(dv, off, size, nch, 32, "float", le, maxFrames);
        else if (enc === 7) ch = pcm(dv, off, size, nch, 64, "float", le, maxFrames);
        else if (enc === 27) ch = pcm(dv, off, size, nch, 8, "alaw", le, maxFrames);
        else return null;
        return { ch, rate, format: "AU" };
    }

    // ---- Core Audio Format ----
    function caf(buf, maxFrames) {
        const u8 = new Uint8Array(buf), dv = new DataView(buf);
        if (fcc(u8, 0) !== "caff") return null;
        let p = 8, desc = null, dOff = -1, dLen = 0;
        while (p + 12 <= u8.length) {
            const cid = fcc(u8, p); let sz = Number(dv.getBigInt64(p + 4, false)); const body = p + 12;
            if (cid === "desc") desc = { rate: dv.getFloat64(body, false), fid: fcc(u8, body + 8), flags: dv.getUint32(body + 12, false), nch: dv.getUint32(body + 24, false), bits: dv.getUint32(body + 28, false) };
            else if (cid === "data") { if (sz < 0 || body + sz > u8.length) sz = u8.length - body; dOff = body + 4; dLen = sz - 4; break; }
            p = body + sz;
        }
        if (!desc || dOff < 0 || !desc.nch) return null;
        const le = !!(desc.flags & 2); let ch;
        if (desc.fid === "lpcm") ch = desc.flags & 1 ? pcm(dv, dOff, dLen, desc.nch, desc.bits, "float", le, maxFrames) : pcm(dv, dOff, dLen, desc.nch, Math.ceil(desc.bits / 8) * 8, "int", le, maxFrames);
        else if (desc.fid === "ulaw") ch = pcm(dv, dOff, dLen, desc.nch, 8, "ulaw", false, maxFrames);
        else if (desc.fid === "alaw") ch = pcm(dv, dOff, dLen, desc.nch, 8, "alaw", false, maxFrames);
        else return null;
        return { ch, rate: desc.rate, format: "CAF" };
    }

    // ---- FLAC ----
    function flac(buf, maxFrames) {
        const u8 = new Uint8Array(buf);
        let p = 0;
        if (u8[0] === 0x49 && u8[1] === 0x44 && u8[2] === 0x33) p = 10 + ((u8[6] << 21) | (u8[7] << 14) | (u8[8] << 7) | u8[9]);   // ID3v2
        if (fcc(u8, p) !== "fLaC") return null;
        p += 4;
        let rate = 0, nch = 0, bps = 0, total = 0, last = false;
        while (!last && p + 4 <= u8.length) {
            const h = u8[p]; last = !!(h & 0x80); const type = h & 0x7f, len = (u8[p + 1] << 16) | (u8[p + 2] << 8) | u8[p + 3];
            if (type === 0) {
                rate = (u8[p + 14] << 12) | (u8[p + 15] << 4) | (u8[p + 16] >> 4);
                nch = ((u8[p + 16] >> 1) & 7) + 1; bps = (((u8[p + 16] & 1) << 4) | (u8[p + 17] >> 4)) + 1;
                total = (u8[p + 17] & 15) * 4294967296 + ((u8[p + 18] << 24) >>> 0) + ((u8[p + 19] << 16) | (u8[p + 20] << 8) | u8[p + 21]);
            }
            p += 4 + len;
        }
        if (!rate) return null;
        // bit reader
        let pos = p * 8;
        const bitsLeft = () => u8.length * 8 - pos;
        const rd = n => { let v = 0; while (n > 0) { const byte = u8[pos >> 3] | 0, avail = 8 - (pos & 7), take = Math.min(avail, n); v = v * Math.pow(2, take) + ((byte >> (avail - take)) & ((1 << take) - 1)); pos += take; n -= take; } return v; };
        const rds = n => { const v = rd(n); return n === 0 ? 0 : (v >= Math.pow(2, n - 1) ? v - Math.pow(2, n) : v); };
        const unary = () => { let n = 0; while (rd(1) === 0 && bitsLeft() > 0) n++; return n; };
        const out = []; for (let c = 0; c < nch; c++) out.push([]);
        const cap = maxFrames > 0 ? maxFrames : Infinity;
        let done = 0;
        const FIXED = [[], [1], [2, -1], [3, -3, 1], [4, -6, 4, -1]];
        const BS = [0, 192, 576, 1152, 2304, 4608, -1, -2, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768];
        const SR = [0, 88200, 176400, 192000, 8000, 16000, 22050, 24000, 32000, 44100, 48000, 96000, -1, -2, -3, 0];
        const BPS = [0, 8, 12, 0, 16, 20, 24, 32];
        try {
            while (done < cap && bitsLeft() > 64) {
                pos = (pos + 7) & ~7;
                if (rd(14) !== 0x3ffe) { pos -= 14; pos += 8; continue; }   // resync byte-wise
                rd(1); const varBs = rd(1);
                const bsc = rd(4), src = rd(4), cha = rd(4), bpc = rd(3); rd(1);
                let b0 = rd(8); let extra = 0; if (b0 >= 0xc0) { extra = b0 >= 0xfe ? 6 : b0 >= 0xfc ? 5 : b0 >= 0xf8 ? 4 : b0 >= 0xf0 ? 3 : b0 >= 0xe0 ? 2 : 1; } for (let i = 0; i < extra; i++) rd(8);
                let bs = BS[bsc]; if (bs === -1) bs = rd(8) + 1; else if (bs === -2) bs = rd(16) + 1;
                if (SR[src] === -1) rd(8); else if (SR[src] === -2) rd(16); else if (SR[src] === -3) rd(16);
                rd(8);   // header crc
                const fb = BPS[bpc] || bps;
                const nc = cha < 8 ? cha + 1 : 2;
                const sub = [];
                for (let c = 0; c < nc; c++) {
                    let sb = fb; if (cha === 8 && c === 1) sb++; else if (cha === 9 && c === 0) sb++; else if (cha === 10 && c === 1) sb++;
                    rd(1); const type = rd(6); let wasted = 0;
                    if (rd(1)) { wasted = unary() + 1; }
                    sb -= wasted;
                    const s = new Array(bs);
                    if (type === 0) { const v = rds(sb); for (let i = 0; i < bs; i++) s[i] = v; }
                    else if (type === 1) { for (let i = 0; i < bs; i++) s[i] = rds(sb); }
                    else {
                        let order, coefs, shift = 0;
                        if (type >= 8 && type <= 12) { order = type - 8; coefs = FIXED[order]; }
                        else if (type >= 32) {
                            order = type - 31;
                        } else throw new Error("bad subframe");
                        for (let i = 0; i < order; i++) s[i] = rds(sb);
                        if (type >= 32) {
                            const prec = rd(4) + 1; shift = rds(5); coefs = [];
                            for (let i = 0; i < order; i++) coefs.push(rds(prec));
                        }
                        // residual
                        const method = rd(2), pbits = method === 0 ? 4 : 5, pord = rd(pbits);
                        const parts = 1 << pord;
                        let i = order;
                        for (let pt = 0; pt < parts; pt++) {
                            const rice = rd(pbits);
                            const n = pord === 0 ? bs - order : (pt === 0 ? (bs >> pord) - order : (bs >> pord));
                            const esc = rice === (method === 0 ? 15 : 31);
                            const eb = esc ? rd(5) : 0;
                            for (let k = 0; k < n; k++, i++) {
                                let r;
                                if (esc) r = eb ? rds(eb) : 0;
                                else { const q = unary(); const low = rice ? rd(rice) : 0; const u = q * Math.pow(2, rice) + low; r = (u % 2) ? -(u + 1) / 2 : u / 2; }
                                let pred = 0;
                                if (type >= 32) { for (let j = 0; j < order; j++) pred += coefs[j] * s[i - 1 - j]; pred = Math.floor(pred / Math.pow(2, shift)); }
                                else for (let j = 0; j < order; j++) pred += coefs[j] * s[i - 1 - j];
                                s[i] = pred + r;
                            }
                        }
                    }
                    if (wasted) for (let i = 0; i < bs; i++) s[i] *= Math.pow(2, wasted);
                    sub.push(s);
                }
                pos = (pos + 7) & ~7; rd(16);   // frame crc
                if (cha === 8) for (let i = 0; i < bs; i++) sub[1][i] = sub[0][i] - sub[1][i];
                else if (cha === 9) for (let i = 0; i < bs; i++) sub[0][i] = sub[0][i] + sub[1][i];
                else if (cha === 10) for (let i = 0; i < bs; i++) { const m = sub[0][i], sd = sub[1][i]; const mm = m * 2 + (sd & 1); sub[0][i] = (mm + sd) / 2; sub[1][i] = (mm - sd) / 2; }
                const sc = Math.pow(2, fb - 1);
                for (let c = 0; c < Math.min(nc, nch); c++) { const dst = out[c]; for (let i = 0; i < bs; i++) dst.push(sub[c][i] / sc); }
                done += bs;
            }
        } catch (e) { /* truncated / damaged stream: keep what was decoded */ }
        if (!out[0].length) return null;
        return { ch: out.map(a => Float32Array.from(a.length > cap ? a.slice(0, cap) : a)), rate, format: "FLAC" };
    }

    // ---- raw PCM fallback (16 bit little endian, mono) for headerless dumps ----
    function raw(buf, maxFrames) {
        const dv = new DataView(buf), n = limit(Math.floor(buf.byteLength / 2), maxFrames), a = new Float32Array(n);
        for (let i = 0; i < n; i++) a[i] = dv.getInt16(i * 2, true) / 32768;
        return { ch: [a], rate: 44100, format: "RAW" };
    }

    function decodeNative(buf, maxFrames) {
        const tries = [wav, aiff, au, caf, flac];
        for (const f of tries) { let r = null; try { r = f(buf, maxFrames); } catch (_) { r = null; } if (r && r.ch && r.ch.length && r.ch[0].length) return r; }
        return null;
    }
    return { decodeNative, raw, wav, aiff, au, caf, flac };
})();
