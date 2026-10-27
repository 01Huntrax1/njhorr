#!/usr/bin/env python3
"""Adds the per-slot Resonator stage (the modal resonators of the Physical source as an effect) and the pre-matrix chain order
(Filter / Distortion / Resonator in any order) to patch/Eisenpuls_Synth.cmajor.  Run after build_phys.py (needs phyRat / phyAmpExp).  Idempotent."""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "osc"))
import layout as L
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "patch", "Eisenpuls_Synth.cmajor")
s = open(PATCH).read()
RK = [p for p in L.PARAMS if 56 <= p[0] <= 63]

DSP = r'''    // ---------------- per-slot resonator stage (tools/phys/build_reso.py) ----------------
    // The 16 modal resonators of the Physical source used as an effect on the slot signal (after the source, in the pre-matrix chain). Tuned to the played key
    // (plus Tune), peak gain 1 per mode, so a mode only rings up what the input has at its frequency. State: Voice.phs 1056 + slot * 116:
    // +0..31 left states (y1, y2 per mode), +32..63 right states, +64 c1 / +80 c2 / +96 gain, +112 counter, +113 signature, +114 pitch.
    void resNoteOn (int vi, int o)
    {
        int b = 1056 + o * 116;

        for (int i = 0; i < 64; ++i)
            voices.at (vi).phs.at (b + i) = 0.0f;

        voices.at (vi).phs.at (b + 112) = 0.0f;
        voices.at (vi).phs.at (b + 113) = -1.0f;
    }

    void resCoefs (int vi, int cb, float f0, int model, float dec, float mat, float hit, float inh)
    {
        float sr    = float (processor.frequency);
        float damp  = 1.6f * (1.0f - mat);
        float aex   = phyAmpExp.at (model);
        float amax  = 0.0001f;

        for (int i = 0; i < 16; ++i)
        {
            float r  = phyRat.at (model * 16 + i) * (1.0f + inh * 0.004f * float (i * i));
            float f  = f0 * r;
            float g  = 0.0f;
            float c1 = 0.0f;
            float c2 = 0.0f;

            if (f < sr * 0.45f)
            {
                float w   = 6.2831853f * f / sr;
                float t60 = max (dec * float (pow (r, -damp)), 0.004f);
                float rr  = float (exp (-6.9078f / (t60 * sr)));
                float am  = abs (float (sin (3.14159265f * hit * float (i + 1)))) / float (pow (float (i + 1), aex));
                c1 = 2.0f * rr * float (cos (w));
                c2 = rr * rr;
                // peak gain of the two-pole section at its own frequency is 1 / ((1 - rr) * |1 - rr e^(-2jw)|)
                g  = am * (1.0f - rr) * float (sqrt (max (1.0f - 2.0f * rr * float (cos (2.0f * w)) + rr * rr, 1.0e-6f)));
                amax = max (amax, am);
            }

            voices.at (vi).phs.at (cb + i)      = c1;
            voices.at (vi).phs.at (cb + 16 + i) = c2;
            voices.at (vi).phs.at (cb + 32 + i) = g;
        }

        // the strongest mode keeps gain 1; the others follow their relative amplitude (set above through am)
        float nrm = 1.0f / amax;

        for (int i = 0; i < 16; ++i)
            voices.at (vi).phs.at (cb + 32 + i) = voices.at (vi).phs.at (cb + 32 + i) * nrm;
    }

    // one stereo sample through the resonator of slot o; returns the wet / dry mix
    float<2> resStep (int vi, int o, float xl, float xr, bool stereo, float f0)
    {
        int   ob  = o * 64;
        int   b   = 1056 + o * 116;
        float mix = op.at (ob + 63);

        float cnt = voices.at (vi).phs.at (b + 112);

        if (cnt <= 0.0f)
        {
            voices.at (vi).phs.at (b + 112) = 64.0f;
            int   mdl = clamp (int (op.at (ob + 57) + 0.5f), 0, 8);
            float fr  = f0 * float (pow (2.0f, op.at (ob + 62) / 12.0f));
            float sig = float (mdl) * 3.7f + op.at (ob + 58) * 0.77f + op.at (ob + 59) * 5.3f + op.at (ob + 60) * 7.1f + op.at (ob + 61) * 11.3f;

            if (voices.at (vi).phs.at (b + 113) != sig || abs (voices.at (vi).phs.at (b + 114) - fr) > fr * 0.0004f)
            {
                voices.at (vi).phs.at (b + 113) = sig;
                voices.at (vi).phs.at (b + 114) = fr;
                resCoefs (vi, b + 64, fr, mdl, op.at (ob + 58), op.at (ob + 59), op.at (ob + 60), op.at (ob + 61));
            }
        }
        else
            voices.at (vi).phs.at (b + 112) = cnt - 1.0f;

        float yl = 0.0f;
        float yr = 0.0f;

        for (int i = 0; i < 16; ++i)
        {
            float g = voices.at (vi).phs.at (b + 96 + i);

            if (g != 0.0f)
            {
                float c1 = voices.at (vi).phs.at (b + 64 + i);
                float c2 = voices.at (vi).phs.at (b + 80 + i);
                float l1 = voices.at (vi).phs.at (b + 2 * i);
                float l2 = voices.at (vi).phs.at (b + 2 * i + 1);
                float l0 = c1 * l1 - c2 * l2 + g * xl;
                voices.at (vi).phs.at (b + 2 * i)     = abs (l0) < 1.0e-20f ? 0.0f : l0;
                voices.at (vi).phs.at (b + 2 * i + 1) = l1;
                yl += l0;

                if (stereo)
                {
                    float r1 = voices.at (vi).phs.at (b + 32 + 2 * i);
                    float r2 = voices.at (vi).phs.at (b + 32 + 2 * i + 1);
                    float r0 = c1 * r1 - c2 * r2 + g * xr;
                    voices.at (vi).phs.at (b + 32 + 2 * i)     = abs (r0) < 1.0e-20f ? 0.0f : r0;
                    voices.at (vi).phs.at (b + 32 + 2 * i + 1) = r1;
                    yr += r0;
                }
            }
        }

        if (! stereo)
            yr = yl;

        // soft limit the wet signal (high Q modes add up at the key frequency)
        yl = yl / (1.0f + 0.5f * abs (yl));
        yr = yr / (1.0f + 0.5f * abs (yr));
        float<2> r;
        r.at (0) = xl + (yl - xl) * mix;
        r.at (1) = xr + (yr - xr) * mix;
        return r;
    }

'''
DECL = "".join('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s%s ]];\n' % (
    1000 + 64 * o + p[0], o + 1, p[2], repr(float(p[4])), repr(float(p[5])), repr(float(p[6])), ", step: 1.0" if p[8] in ("btn", "sel") else "")
    for o in range(6) for p in RK)
HAND = "".join("    event param%d (float v) { opSet (%d, %d, v); }\n" % (1000 + 64 * o + p[0], o, p[0]) for o in range(6) for p in RK)
INIT = "".join("            op.at (io * 64 + %d) = %sf;\n" % (p[0], repr(float(p[6]))) for p in RK)

def block(tag, body, anchor_re, indent="    "):
    global s
    a, z = indent + "// RESO-%s-BEGIN\n" % tag, indent + "// RESO-%s-END\n" % tag
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + tag)
    s = s[:m.start()] + a + body + z + s[m.start():]
block("DSP", DSP, r"^    // ---------------- MIDI ----------------")
block("DECL", DECL, r"^    input event float param1600 ")
block("HAND", HAND, r"^    event param1600 ")
block("INIT", INIT, r"^            // PHYS-INIT-BEGIN\n", indent="            ")

# the order parameter (id 1045 + 64 * o): 0..5 instead of Post / Pre
s = re.sub(r'(param10\d\d \[\[ name: "OSC \d )Distortion Position(", min: 0\.0, max: )1\.0(, init: 0\.0, step: 1\.0)', lambda m: m.group(1) + "Pre-Matrix Order (0-5, see Order list)" + m.group(2) + "5.0" + m.group(3), s)

# note on: clear the resonator states of every slot
if "resNoteOn (v, o);" not in s:
    assert "                    phyNoteOn (v, o);\n" in s
    s = s.replace("                    phyNoteOn (v, o);\n", "                    phyNoteOn (v, o);\n                    resNoteOn (v, o);\n", 1)

# the chain
if "RESO-CHAIN" not in s:
    a = s.index("                    // signal flow per slot: source -> filter -> distortion")
    z = s.index("                    // ----- ring modulation (carrier x modulator)")
    old = s[a:z]
    # pieces of the old code
    i_f0 = old.index("                    // ----- filter -----")
    i_f1 = old.index("                    // ----- distortion after the filter -----")
    filt = old[i_f0:i_f1]
    head_end = old.index("                    // ----- distortion before the filter -----")
    head = old[:head_end]
    head = head.replace("                    bool  dPre = op.at (ob + 45) > 0.5f;\n", "                    int   chOrd = clamp (int (op.at (ob + 45) + 0.5f), 0, 5);   // RESO-CHAIN\n")
    head = head.replace("(the \"Distortion Position\" switch puts the distortion before the filter instead)", "(the Order parameter puts filter, distortion and resonator in any order)")
    head = head.replace("source -> filter -> distortion -> FM / PM matrix and output", "source -> filter / distortion / resonator in the chosen order -> FM / PM matrix and output")
    filt = filt.replace("                    if (op.at (ob + 30) > 0.5f)\n", "                        if (chStage == 0 && op.at (ob + 30) > 0.5f)\n", 1)
    # indent the filter block one level (inside the stage loop)
    filt = "\n".join(("    " + ln if ln.strip() else ln) for ln in filt.split("\n"))
    filt = filt.replace("                        if (chStage == 0 && op.at (ob + 30) > 0.5f)", "                        if (chStage == 0 && op.at (ob + 30) > 0.5f)")
    dist = '''                        if (chStage == 1 && dty > 0)
                        {
                            sL = oscDist (sL, dty, dd, dx, o, dwp);
                            sR = stereo ? oscDist (sR, dty, dd, dx, o, dwp) : sL;
                        }

                        if (chStage == 2 && op.at (ob + 56) > 0.5f)
                        {
                            float<2> rz = resStep (i, o, sL, sR, stereo, freq);
                            sL = rz.at (0);
                            sR = stereo ? rz.at (1) : sL;
                        }
                    }

'''
    new = head + "                    for (int chSt = 0; chSt < 3; ++chSt)\n                    {\n                        int chStage = chainOrder.at (chOrd * 3 + chSt);\n\n" + filt.rstrip() + "\n\n" + dist
    s = s[:a] + new + s[z:]
    # the table of stage orders (0 filter, 1 distortion, 2 resonator)
    anchor = "    // ---------------- MIDI ----------------"
    s = s.replace(anchor, "    const int[18] chainOrder = (0, 1, 2,  1, 0, 2,  0, 2, 1,  2, 0, 1,  1, 2, 0,  2, 1, 0);   // rows = Order 0..5\n\n" + anchor, 1)
open(PATCH, "w").write(s)
print("ok")
