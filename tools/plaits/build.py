#!/usr/bin/env python3
"""Assembles the Plaits port.
  build.py part <out.part>                -> the processor-scope code that tools/osc/build_osc.py includes in the synth
  build.py test <outdir>                  -> a stand-alone test patch (outdir/PlaitsTest.cmajor + .cmajorpatch) that renders one engine
Parts: core.part, parts/lib_*.part, parts/eng_NN_*.part (engine NN, files define plInit_N / plRender_N). `//@LUT name` pulls in luts/name.part."""
import glob, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
# index -> post processing gain of plaits/dsp/voice.cc (negative = limiter with that pre gain)
GAIN = [1.0, 0.7, 1.0, 1.0, 1.0, 0.7, 0.8, 0.5, 0.8, 0.7, 0.6, 0.7, 0.8, 0.6, 0.8, -0.7, -3.0, -1.0, -2.0, -1.0, -1.0, 0.8, 0.8, 0.8]
ENGINE_NAMES = ["VA VCF", "Phase distortion", "Six-op A", "Six-op B", "Six-op C", "Wave terrain", "String machine", "Chiptune", "Virtual analog",
    "Waveshaping", "FM", "Grain", "Additive", "Wavetable", "Chord", "Speech", "Swarm", "Noise", "Particle", "String", "Modal", "Bass drum", "Snare drum", "Hi-hat"]

def expand(text, done):
    def rep(m):
        n = m.group(1)
        if n in done: return ""
        done.add(n)
        p = os.path.join(HERE, "luts", n + ".part")
        if not os.path.exists(p):
            subprocess.check_call([sys.executable, os.path.join(HERE, "gen_lut.py"), n], stdout=subprocess.DEVNULL)
        return open(p).read()
    return re.sub(r"^//@LUT\s+(\w+)\s*$", rep, text, flags=re.M)

def engine_parts():
    out = {}
    for f in sorted(glob.glob(os.path.join(HERE, "parts", "eng_*.part"))):
        m = re.match(r"eng_(\d+)_", os.path.basename(f))
        out.setdefault(int(m.group(1)), []).append(f)
    return out

def assemble():
    done = set()
    txt = expand(open(os.path.join(HERE, "core.part")).read(), done)
    for f in sorted(glob.glob(os.path.join(HERE, "parts", "lib_*.part"))):
        txt += "\n" + expand(open(f).read(), done)
    eng = engine_parts()
    for i in sorted(eng):
        for f in eng[i]:
            txt += "\n" + expand(open(f).read(), done)
    # dispatch
    d = []
    d.append("    // ---------------- dispatch ----------------")
    d.append("    void plSilence (int inst) { for (int i = 0; i < 12; ++i) { plOut.at (inst * 12 + i) = 0.0f; plAux.at (inst * 12 + i) = 0.0f; } }")
    d.append("    void plInitEngine (int inst, int eng)\n    {\n        plRng.at (inst) = 33 + inst;\n        plSvfReset (plDummySvf);\n        if (false) {}")
    for i in range(24):
        if i in eng: d.append("        else if (eng == %d) plInit_%d (inst);" % (i, i))
    d.append("    }")
    d.append("    void plRenderEngine (int inst, int eng, int trig, float note, float harm, float timb, float morph, float accent)\n    {\n        if (false) {}")
    for i in range(24):
        if i in eng: d.append("        else if (eng == %d) plRender_%d (inst, trig, note, harm, timb, morph, accent);" % (i, i))
    d.append("        else plSilence (inst);\n    }")
    gains = ", ".join("%sf" % g for g in GAIN)
    d.append("    const float[24] plGains = (%s);" % gains)
    d.append('''
    // engine + post processing of the module (gain, or the limiter for the engines with a negative gain)
    void plRenderBlock (int inst, int eng, int trig, float note, float harm, float timb, float morph, float accent)
    {
        if (plEngine.at (inst) != eng + 1)
        {
            plEngine.at (inst) = eng + 1;
            plLimPeak.at (inst) = 0.5f;
            plInitEngine (inst, eng);
        }

        plRenderEngine (inst, eng, trig, note, harm, timb, morph, accent);

        float g = plGains.at (eng);
        float peak = plLimPeak.at (inst);

        for (int i = 0; i < 12; ++i)
        {
            float s = plOut.at (inst * 12 + i);

            if (g < 0.0f)
            {
                s *= -g;
                float e = abs (s) - peak;
                peak += (e > 0.0f ? 0.05f : 0.00002f) * e;
                float gain = peak <= 1.0f ? 1.0f : 1.0f / peak;
                s = s * gain * 0.8f;
            }
            else
            {
                s *= g;
            }

            plOut.at (inst * 12 + i) = s;
        }

        plLimPeak.at (inst) = peak;
    }''')
    txt += "\n" + "\n".join(d) + "\n"
    return txt

# glue between the synth voice loop and the block based engines
SYNTH_WRAPPER = """
    // Called once per sample by the oscillator slot: plays the rendered block, renders the next one when it is used up.
    // f0 is the oscillator frequency in cycles per sample; pm (phase modulation from the FM matrix) acts as a pitch
    // modulation that is only sampled once per block of 12 samples.
    float plaitsStep (int vi, int o, int eng, float f0, float pm, float harm, float timb, float morph, bool gate)
    {
        int inst = vi * 6 + o;
        int pos  = plPos.at (inst);

        if (pos >= 12)
        {
            float note = 9.0f + 12.0f * log (max (f0, 1.0e-7f) / (plA0 * 0.25f)) / log (2.0f) + clamp (pm, -4.0f, 4.0f) * 12.0f;
            int   trig = plTrigPending.at (inst) + (gate ? 4 : 0);
            plTrigPending.at (inst) = 0;
            plRenderBlock (inst, clamp (eng, 0, 23), trig, note, harm, timb, morph, 0.8f);
            pos = 0;
        }

        plPos.at (inst) = pos + 1;
        return plOut.at (inst * 12 + pos);
    }

    void plaitsNoteOn (int vi, int o)
    {
        int inst = vi * 6 + o;
        plTrigPending.at (inst) = 1;
        plPos.at (inst) = 12;          // render a new block with the trigger right away
    }
"""

STUB_DUMMY = "    PlSvf plDummySvf;\n"

if __name__ == "__main__":
    mode = sys.argv[1]
    body = assemble()
    body = STUB_DUMMY + body
    if mode == "part":
        body += SYNTH_WRAPPER
        open(sys.argv[2], "w").write(body)
    elif mode == "test":
        outdir = sys.argv[2]
        os.makedirs(outdir, exist_ok=True)
        tpl = open(os.path.join(HERE, "test", "PlaitsTest.cmajor.in")).read()
        open(os.path.join(outdir, "PlaitsTest.cmajor"), "w").write(tpl.replace("//@PLAITS@", body))
        open(os.path.join(outdir, "PlaitsTest.cmajorpatch"), "w").write('{ "CmajorVersion": 1, "ID": "test.plaits", "version": "1.0", "name": "PlaitsTest", "source": "PlaitsTest.cmajor" }\n')
