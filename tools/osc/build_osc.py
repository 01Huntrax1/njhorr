#!/usr/bin/env python3
"""Turns the rack + LFO version of patch/Eisenpuls_Synth.cmajor into the 6-slot oscillator version.

Run once on the committed pre-slot source (`git show <rev>:patch/Eisenpuls_Synth.cmajor`).
Usage: build_osc.py <in.cmajor> <out.cmajor>
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import layout as L

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(sys.argv[1]).read()

def die(m): raise SystemExit("build_osc: " + m)

# ---------- helpers ----------
def match_brace(s, i):
    """s[i] == '{' -> index just after the matching '}'"""
    assert s[i] == '{', s[i - 20:i + 20]
    d = 0
    while True:
        c = s[i]
        if c == '{': d += 1
        elif c == '}':
            d -= 1
            if d == 0: return i + 1
        i += 1

def line_start(s, i): return s.rfind("\n", 0, i) + 1

def cut_function(name, required=True):
    global src
    m = re.search(r'^    [A-Za-z0-9_<>\[\]:, ]+? ' + re.escape(name) + r'\s*\(.*\)\s*\n    \{', src, re.M)
    if not m:
        if required: die("function not found: " + name)
        return
    a = line_start(src, m.start())
    b = match_brace(src, src.index("{", m.end() - 6))
    # include leading comment lines directly above
    while True:
        p = src.rfind("\n", 0, a - 1) + 1
        ln = src[p:a - 1]
        if ln.strip().startswith("//") and ln.strip() != "":
            a = p
        else:
            break
    while src[b] == "\n": b += 1
    src = src[:a] + src[b:]

def cut_event(name):
    global src
    m = re.search(r'^    event ' + re.escape(name) + r' \(.*\)\s*\n?\s*\{', src, re.M)
    if not m: die("event not found: " + name)
    a = line_start(src, m.start())
    b = match_brace(src, src.index("{", m.start()))
    while True:
        p = src.rfind("\n", 0, a - 1) + 1
        ln = src[p:a - 1]
        if ln.strip().startswith("//") and ln.strip() != "": a = p
        else: break
    while src[b] == "\n": b += 1
    src = src[:a] + src[b:]

def replace_between(start_marker, end_marker, new, keep_end=True):
    global src
    a = src.index(start_marker)
    b = src.index(end_marker, a)
    src = src[:a] + new + (src[b:] if keep_end else src[b + len(end_marker):])

# ---------- parameters ----------
KEEP = set([2, 3, 18, 19, 20, 21, 22, 28, 29, 36, 45, 46, 63, 175, 189, 190, 221, 222, 522, 536, 880, 881])
KEEP |= set(range(247, 337)) | set(range(472, 523)) | set(range(541, 871)) | set(range(882, 932))
decl = re.compile(r'^    input event float param(\d+)\b.*\n', re.M)
all_ids = [int(m.group(1)) for m in decl.finditer(src)]
remove_ids = sorted(set(i for i in all_ids if i not in KEEP))
removed_vars = set()

for pid in remove_ids:
    m = re.search(r'^    event param%d\s+\(float v\)\s*' % pid, src, re.M)
    if m:
        a = line_start(src, m.start())
        j = m.end()
        if src[j] == '{':
            b = match_brace(src, j)
        else:
            die("handler without body %d" % pid)
        body = src[j:b]
        for t in re.finditer(r'([A-Za-z_][A-Za-z0-9_]*)(?:\.at \([^)]*\))?\s*=[^=]', body):
            removed_vars.add(t.group(1))
        while src[b] == "\n": b += 1
        src = src[:a] + src[b:]

src = decl.sub(lambda m: "" if int(m.group(1)) in set(remove_ids) else m.group(0), src)

# mod matrix destination range 0..N_DST-1
src = src.replace("Dest (0-45, see Dest list)", "Dest (0-%d, see Dest list)" % (L.N_DST - 1))
src = re.sub(r'(Dest \(0-%d, see Dest list\)", min: 0\.0, max: )45\.0' % (L.N_DST - 1), r'\g<1>%d.0' % (L.N_DST - 1), src)
src = src.replace("mmDstI.at", "mmDstI.at")
src = re.sub(r'(mmDstI\.at \((\d+)\) = clamp \(int \(v \+ 0\.5f\), 0, )45\)', r'\g<1>%d)' % (L.N_DST - 1), src)
src = src.replace("float[46]   vmod;", "float[%d]   vmod;" % (L.N_DST + 4)).replace("float[46]   gmod;", "float[%d]   gmod;" % (L.N_DST + 4))
src = src.replace("for (int d = 0; d < 46; ++d)", "for (int d = 0; d < %d; ++d)" % (L.N_DST + 4))

# ---------- per-osc and FM parameter declarations + handlers ----------
decls, handlers = [], []
for o in range(L.OSC_COUNT):
    for (k, key, label, short, lo, hi, init, unit, kind, labels) in L.PARAMS:
        pid = L.pid(o, k)
        step = ", step: 1.0" if kind in ("btn", "sel", "stp") else ""
        u = ', unit: "%s"' % unit if unit in ("Hz", "ms") else ""
        decls.append('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s%s%s ]];' % (pid, o + 1, label, float(lo), float(hi), float(init) if not (k == 1 and o == 0) else 0.8, step, u))
        handlers.append('    event param%d (float v) { opSet (%d, %d, v); }' % (pid, o, k))
for s in range(6):
    for d in range(6):
        pid = L.fm_id(s, d)
        decls.append('    input event float param%d [[ name: "FM %d to %d", min: 0.0, max: 100.0, init: 0.0, step: 1.0 ]];' % (pid, s + 1, d + 1))
        handlers.append('    event param%d (float v) { fmSet (%d, %d, v * 0.01f); }' % (pid, s, d))
        pid = L.pm_id(s, d)
        decls.append('    input event float param%d [[ name: "PM %d to %d", min: 0.0, max: 100.0, init: 0.0, step: 1.0 ]];' % (pid, s + 1, d + 1))
        handlers.append('    event param%d (float v) { pmSet (%d, %d, v * 0.01f); }' % (pid, s, d))

# anchor: right before the first handler of a kept param
anchor_decl = re.search(r'^    input event float param2 ', src, re.M)
src = src[:anchor_decl.start()] + "\n".join(decls) + "\n\n" + src[anchor_decl.start():]
anchor_h = re.search(r'^    event param2\s+\(', src, re.M)
src = src[:anchor_h.start()] + "\n".join(handlers) + "\n\n" + src[anchor_h.start():]

# ---------- endpoints, structs ----------
src, n = re.subn(r'^\s*(?:input|output)\s+event\s+(?:SynthSampleChunk|SampleSave)\s+\w+;[^\n]*\n', '', src, flags=re.M)
if n != 7: die("endpoint count %d" % n)
src, n = re.subn(r'^(\s*input\s+event\s+LfoShapeChunk\s+lfoShapeLoad;[^\n]*\n)', lambda m: m.group(1) + "    input event BankChunk wtBankLoad;\n    input event BankChunk smpBankLoad;\n", src, count=1, flags=re.M)
if n != 1: die("lfo endpoint")
for st in ["SynthSampleChunk", "SampleSave"]:
    m = re.search(r'^    struct %s\s*\n    \{' % st, src, re.M)
    a = line_start(src, m.start()); b = match_brace(src, src.index("{", m.start()))
    src = src[:a] + src[b:]

# ---------- functions to drop ----------
for f in ["queueSave", "clearSampleBankV2", "beginSampleBankV2", "writeSampleBankV2Chunk",
          "clearSampleBank2V2", "beginSampleBank2V2", "writeSampleBank2V2Chunk",
          "clearWavetableBankV2", "calculateWavetableBankV2Means", "wtMeanOf", "beginWavetableBankV2", "writeWavetableBankV2Chunk",
          "clearWavetableBank2V2", "calculateWavetableBank2V2Means", "wt2MeanOf", "beginWavetableBank2V2", "writeWavetableBank2V2Chunk",
          "clearWavetableBank3V2", "calculateWavetableBank3V2Means", "wt3MeanOf", "beginWavetableBank3V2", "writeWavetableBank3V2Chunk",
          "updateWtUni", "updateWtPan", "resetWtUni", "wtUniStep", "updateSuperSaw", "polyBlep", "oscWave", "superSawStep",
          "filterStep", "smpRead", "s2Read", "wtBankRead", "wt2BankRead", "wt3BankRead", "updateEq", "eqProcess"]:
    cut_function(f)
for e in ["sampleBankV2Load", "sampleBank2V2Load", "wavetableBankV2Load", "wavetableBank2V2Load", "wavetableBank3V2Load", "sampleBankV2Restore"]:
    cut_event(e)

# ---------- state declarations ----------
# variables only assigned by removed parameter handlers, plus the memory banks / eq / supersaw state
names = set(removed_vars)
names |= {"synthLoadIdx", "synthLoad2Idx", "wtLoadIdx", "wt2LoadIdx", "wt3LoadIdx", "ssOff", "ssPos", "ssRatio", "ssGL", "ssGR", "ssCount",
          "centerGain", "sideGain", "ssNorm", "saveQueued", "autosaveOn", "dumpIdx", "dumpOff", "dumpTimer", "srcRoute",
          "sampleBankV2Has", "sampleBankV2Length", "sampleBankV2Buffer", "sampleBank2V2Has", "sampleBank2V2Length", "sampleBank2V2Buffer",
          "wavetableBankV2Has", "wavetableBankV2Length", "wavetableBankV2Buffer", "wavetableBankV2Means", "wavetableBankV2MeanAll",
          "wavetableBank2V2Has", "wavetableBank2V2Length", "wavetableBank2V2Buffer", "wavetableBank2V2Means", "wavetableBank2V2MeanAll",
          "wavetableBank3V2Has", "wavetableBank3V2Length", "wavetableBank3V2Buffer", "wavetableBank3V2Means", "wavetableBank3V2MeanAll",
          "wtUniCnt", "wtUniRatio", "wtUniCents1", "wtUniGL", "wtUniGR", "wtPanGL", "wtPanGR", "wtPanV", "wtPhaseV",
          "eqOn", "eqFreq", "eqGain", "eqQ", "eqB0", "eqB1", "eqB2", "eqA1", "eqA2", "lfoPhase", "shValue"}
kept_assigned = {"flfPhase", "noiseState", "voices"}
decl_re = re.compile(r'^    (?:float64|float|int|bool|float<2>)(?:\[\d+\])?\s+(\w+)\b[^;(]*;[^\n]*\n', re.M)
def drop_decl(m):
    return "" if m.group(1) in names and m.group(1) not in kept_assigned else m.group(0)
src = decl_re.sub(drop_decl, src)

# ---------- Voice struct ----------
a = src.index("    struct Voice\n")
b = match_brace(src, src.index("{", a))
voice_struct = """    struct Voice
    {
        int     noteNumber;
        int     stage;        // amp envelope: 0 off, 1 attack, 2 decay/sustain, 3 release
        int     age;
        float   curFreq;
        float   targetFreq;
        float64[6]  synPos;   // sampler read position per slot
        float64[42] wtUPh;    // wavetable unison phases: slot * 7 + unison voice
        float[24]   wtDcS;    // wavetable warp DC blocker: slot * 4 + {xL, yL, xR, yR}
        float[6]    fmPrev;   // last output of every slot (FM source)
        float[6]    fenv;     // filter envelope level per slot
        int[6]      fstage;   // filter envelope stage per slot
        float[10] menv;       // mod envelope levels
        float64[10] lfoPh;    // per-voice LFO phases (modes Trig / Env)
        float[10] lfoV;       // per-voice LFO outputs
        float[10] lfoAge;     // seconds since note-on, -1 before the first update
        float[10] lfoSh;      // per-voice sample & hold values
        float[10] lfoSm;      // per-voice smoothing state
        int[10]   mstage;     // mod envelope stages (0 off, 1 attack, 2 decay/sustain, 3 release)
        float   env;
        float   penv;
        float   velGain;
        float   velRaw;
        float   modRand;      // per-note random value for the mod matrix
        float[192]  fx;       // filter states: slot * 32 + channel * 16 + stage state
        float[24576] fdl;     // comb filter delay lines: slot * 4096 + channel * 2048 + position
        int     fdlW;         // comb delay write position
        bool    active;
    }
"""
src = src[:a] + voice_struct + src[b:]

# ---------- init ----------
replace_between("        // supersaw detune offsets", "        // LFO sync divisions", "", True)
a = src.index("        // wavetable unison defaults")
b = src.index("        // mod page defaults")
src = src[:a] + """        // slot defaults (the annotated parameter inits) and wavetable unison tables
        for (int io = 0; io < 6; ++io)
        {
            for (int ik = 0; ik < 64; ++ik)
                op.at (io * 64 + ik) = 0.0f;

            op.at (io * 64 + 1)  = 0.0f;
            op.at (io * 64 + 7)  = 1.0f;
            op.at (io * 64 + 11) = 3.0f;
            op.at (io * 64 + 12) = 60.0f;
            op.at (io * 64 + 13) = 1.0f;
            op.at (io * 64 + 14) = 0.25f;
            op.at (io * 64 + 15) = 1.0f;
            op.at (io * 64 + 16) = 0.75f;
            op.at (io * 64 + 19) = 0.5f;
            op.at (io * 64 + 21) = 0.5f;
            op.at (io * 64 + 24) = 8.0f;
            op.at (io * 64 + 25) = 0.5f;
            op.at (io * 64 + 26) = 0.5f;
            op.at (io * 64 + 27) = 0.5f;
            op.at (io * 64 + 30) = 1.0f;
            op.at (io * 64 + 32) = 8000.0f;
            op.at (io * 64 + 33) = 0.25f;
            op.at (io * 64 + 35) = 0.5f;
            op.at (io * 64 + 39) = 300.0f;
            op.at (io * 64 + 41) = 250.0f;
            op.at (io * 64 + 43) = 0.3f;
            op.at (io * 64 + 44) = 1.0f;
            updateWtUni (io);
        }
        op.at (1) = 0.8f;

""" + src[b:]
a = src.index("        // mixer EQ defaults")
b = src.index("        // reverb delay line lengths")
src = src[:a] + src[b:]

# ---------- main(): LFO block, voice loop, sample memory manager ----------
a = src.index("            // ----- LFO -----")
b = src.index("            // ----- mod page: 10 LFOs + global matrix sums -----")
src = src[:a] + "            flfPhase += 0.3 * processor.period;\n            if (flfPhase >= 1.0) flfPhase -= 1.0;\n\n" + src[b:]
voice_loop = open(os.path.join(HERE, "voice_loop.cmajor.part")).read()
a = src.index("            float[3] mixSynthL;")
b = src.index("            // ----- global mod destinations")
src = src[:a] + voice_loop + src[b:]
src = src.replace("gmod.at (5)", "gmod.at (3)").replace("gmod.at (8)", "gmod.at (4)").replace("gmod.at (10)", "gmod.at (5)")

# ---------- MIDI handler ----------
a = src.index("    event midiIn (std::midi::Message msg)")
b = src.index("    // ---------------- AUDIO ----------------")
midi = r'''    event midiIn (std::midi::Message msg)
    {
        if (msg.isNoteOn())
        {
            int   nn       = msg.getNoteNumber();
            float vel      = msg.getFloatVelocity();
            float velGainV = (1.0f - velSens) + velSens * vel;
            bool  monoMode = voiceMode > 0.5f;

            int v = 0;
            if (! monoMode) v = findFreeVoice();

            bool wasActive = voices.at (v).active;
            float target = float (std::notes::noteToFrequency (nn));

            voices.at (v).noteNumber = nn;
            voices.at (v).targetFreq = target;

            if (! (monoMode && wasActive))
                voices.at (v).curFreq = target;

            // restart every slot on each non-legato note
            if (! (monoMode && wasActive))
            {
                for (int o = 0; o < 6; ++o)
                {
                    int sLen   = smpLen.at (o);
                    int sStart = clamp (int (opv (o, 22) * float (sLen)), 0, max (sLen - 1, 0));
                    voices.at (v).synPos.at (o) = float64 (sStart);
                    resetWtUni (v, o);
                    plaitsNoteOn (v, o);
                }
            }

            if (! wasActive)
            {
                voices.at (v).env  = 0.0f;
                voices.at (v).fdlW = 0;

                for (int fq = 0; fq < 192; ++fq)
                    voices.at (v).fx.at (fq) = 0.0f;

                for (int fd = 0; fd < 24576; ++fd)
                    voices.at (v).fdl.at (fd) = 0.0f;

                for (int me = 0; me < 10; ++me)
                    voices.at (v).menv.at (me) = 0.0f;

                for (int o = 0; o < 6; ++o)
                    voices.at (v).fmPrev.at (o) = 0.0f;
            }

            voices.at (v).stage = 1;

            for (int o = 0; o < 6; ++o)
            {
                voices.at (v).fstage.at (o) = 1;
                voices.at (v).fenv.at (o)   = opv (o, 38) > 0.5f ? 0.0f : 1.0f;
            }

            for (int ms = 0; ms < 10; ++ms)
                voices.at (v).mstage.at (ms) = 1;

            voices.at (v).penv    = 1.0f;
            voices.at (v).velGain = velGainV;
            voices.at (v).velRaw  = vel;
            voices.at (v).modRand = nextNoise();
            lastVoice = v;

            for (int lm = 0; lm < 10; ++lm)
            {
                voices.at (v).lfoPh.at (lm)  = 0.0;
                voices.at (v).lfoAge.at (lm) = -1.0f;
                voices.at (v).lfoSh.at (lm)  = nextNoise();
                voices.at (v).lfoV.at (lm)   = 0.0f;
            }

            lastVelV  = vel;
            lastKeyV  = clamp ((float (nn) - 60.0f) / 48.0f, -1.0f, 1.0f);
            lastRandV = voices.at (v).modRand;
            voices.at (v).age     = 0;
            voices.at (v).active  = true;
        }
        else if (msg.isNoteOff())
        {
            int nn = msg.getNoteNumber();

            for (int i = 0; i < 8; ++i)
            {
                if (voices.at (i).active && voices.at (i).noteNumber == nn)
                {
                    voices.at (i).stage = 3;

                    for (int o = 0; o < 6; ++o)
                        voices.at (i).fstage.at (o) = 3;

                    for (int mq = 0; mq < 10; ++mq)
                        voices.at (i).mstage.at (mq) = 3;
                }
            }
        }
    }

'''
src = src[:a] + midi + src[b:]

# ---------- new oscillator code ----------
dsp = open(os.path.join(HERE, "osc_dsp.cmajor.part")).read()
import subprocess, tempfile
_t = tempfile.NamedTemporaryFile(suffix=".part", delete=False); _t.close()
subprocess.check_call([sys.executable, os.path.join(HERE, "..", "plaits", "build.py"), "part", _t.name])
plaits = open(_t.name).read()
os.unlink(_t.name)
dsp = re.sub(r'    // Plaits slot: filled in.*?\n    \}\n', '', dsp, flags=re.S)
anchor = "    // ---------------- MIDI ----------------"
src = src.replace(anchor, dsp + "\n" + plaits + "\n" + anchor, 1)

open(sys.argv[2], "w").write(src)
print("wrote", sys.argv[2], len(src.splitlines()), "lines")
