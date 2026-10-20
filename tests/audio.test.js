// Native decoder test against ffmpeg: every container is produced by ffmpeg and decoded by both.
const fs = require("fs"), path = require("path"), cp = require("child_process"), os = require("os");
const src = fs.readFileSync(path.join(__dirname, "../tools/audio/decode.js"), "utf8");
const AudioDecode = new Function(src + "\nreturn AudioDecode;")();
let failures = 0;
const check = (n, ok, x) => { console.log((ok ? "PASS " : "FAIL ") + n + (x ? "  (" + x + ")" : "")); if (!ok) failures++; };
try { cp.execFileSync("ffmpeg", ["-version"], { stdio: "ignore" }); } catch (_) { console.log("ffmpeg not found: skipped"); process.exit(0); }
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "adec"));
const base = path.join(tmp, "base.wav");
cp.execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.6:sample_rate=44100", "-f", "lavfi", "-i", "anoisesrc=d=0.6:c=pink:a=0.3:r=44100", "-filter_complex", "[0][1]amerge=inputs=2,volume=0.7", "-c:a", "pcm_s16le", base]);
const cases = [
    ["wav pcm16", "a.wav", ["-c:a", "pcm_s16le"], 1e-6],
    ["wav pcm8", "b.wav", ["-c:a", "pcm_u8"], 1e-6],
    ["wav pcm24", "c.wav", ["-c:a", "pcm_s24le"], 1e-6],
    ["wav pcm32", "d.wav", ["-c:a", "pcm_s32le"], 1e-6],
    ["wav float32", "e.wav", ["-c:a", "pcm_f32le"], 1e-6],
    ["wav float64", "f.wav", ["-c:a", "pcm_f64le"], 1e-6],
    ["wav alaw", "g.wav", ["-c:a", "pcm_alaw"], 1e-6],
    ["wav mulaw", "h.wav", ["-c:a", "pcm_mulaw"], 1e-6],
    ["wav ima adpcm", "i.wav", ["-c:a", "adpcm_ima_wav"], 1e-6],
    ["wav ms adpcm", "j.wav", ["-c:a", "adpcm_ms"], 2e-3],
    ["wav mono", "k.wav", ["-ac", "1", "-c:a", "pcm_s16le"], 1e-6],
    ["wav rf64", "l.wav", ["-c:a", "pcm_s16le", "-rf64", "always"], 1e-6],
    ["wave64", "m.w64", ["-c:a", "pcm_s16le"], 1e-6],
    ["aiff pcm16", "n.aiff", ["-c:a", "pcm_s16be"], 1e-6],
    ["aiff pcm24", "o.aiff", ["-c:a", "pcm_s24be"], 1e-6],
    ["aiff pcm32", "p.aiff", ["-c:a", "pcm_s32be"], 1e-6],
    ["aifc sowt", "q.aifc", ["-c:a", "pcm_s16le", "-f", "aiff"], 1e-6],
    ["aifc float32", "r.aifc", ["-c:a", "pcm_f32be", "-f", "aiff"], 1e-6],
    ["au pcm16", "s.au", ["-c:a", "pcm_s16be"], 1e-6],
    ["au mulaw", "t.au", ["-c:a", "pcm_mulaw"], 1e-6],
    ["au alaw", "u.au", ["-c:a", "pcm_alaw"], 1e-6],
    ["au float", "v.au", ["-c:a", "pcm_f32be"], 1e-6],
    ["caf pcm16", "w.caf", ["-c:a", "pcm_s16le"], 1e-6],
    ["caf pcm24", "x.caf", ["-c:a", "pcm_s24le"], 1e-6],
    ["flac 16", "y.flac", ["-c:a", "flac"], 1e-6],
    ["flac 24", "z.flac", ["-c:a", "flac", "-sample_fmt", "s32"], 1e-6],
    ["flac mono level 8", "z2.flac", ["-ac", "1", "-c:a", "flac", "-compression_level", "8"], 1e-6],
    ["flac level 0", "z3.flac", ["-c:a", "flac", "-compression_level", "0"], 1e-6],
    ["flac 8 bit", "z4.flac", ["-c:a", "flac", "-sample_fmt", "s16", "-bits_per_raw_sample", "8"], 2e-2],
];
for (const [name, file, args, tol] of cases) {
    const out = path.join(tmp, file);
    try { cp.execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", base, ...args, out]); }
    catch (e) { console.log("skip " + name + " (ffmpeg cannot write it)"); continue; }
    const ref = path.join(tmp, file + ".f32");
    const probe = JSON.parse(cp.execFileSync("ffprobe", ["-v", "error", "-show_streams", "-of", "json", out]).toString()).streams[0];
    cp.execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", out, "-f", "f32le", "-c:a", "pcm_f32le", ref]);
    const r = fs.readFileSync(ref), refA = new Float32Array(r.buffer, r.byteOffset, r.length / 4);
    const fb = fs.readFileSync(out), ab = fb.buffer.slice(fb.byteOffset, fb.byteOffset + fb.length);
    const d = AudioDecode.decodeNative(ab, 0);
    if (!d) { check(name, false, "not decoded"); continue; }
    const nch = d.ch.length, n = d.ch[0].length;
    let err = 0;
    const cmp = Math.min(n, refA.length / nch);
    for (let i = 0; i < cmp; i++) for (let c = 0; c < nch; c++) err = Math.max(err, Math.abs(d.ch[c][i] - refA[i * nch + c]));
    check(name, nch === Number(probe.channels) && d.rate === Number(probe.sample_rate) && Math.abs(n - refA.length / nch) <= 1 && err <= tol, "ch " + nch + " rate " + d.rate + " n " + n + "/" + refA.length / nch + " err " + err.toExponential(1));
}
// frame limit
{
    const fb = fs.readFileSync(path.join(tmp, "y.flac")), d = AudioDecode.decodeNative(fb.buffer.slice(fb.byteOffset, fb.byteOffset + fb.length), 5000);
    check("frame limit is respected", d && d.ch[0].length === 5000, d && d.ch[0].length);
    const wb = fs.readFileSync(path.join(tmp, "i.wav")), w = AudioDecode.decodeNative(wb.buffer.slice(wb.byteOffset, wb.byteOffset + wb.length), 3000);
    check("frame limit on adpcm", w && w.ch[0].length === 3000, w && w.ch[0].length);
}
check("garbage is not decoded", AudioDecode.decodeNative(new Uint8Array(1000).buffer, 0) === null);
check("mp3 / ogg are left to the web view", (() => { const mp = path.join(tmp, "t.mp3"); try { cp.execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", base, mp]); } catch (_) { return true; } const b = fs.readFileSync(mp); return AudioDecode.decodeNative(b.buffer.slice(b.byteOffset, b.byteOffset + b.length), 0) === null; })());
console.log(failures ? failures + " FAILED" : "all passed");
process.exit(failures ? 1 : 0);
