#!/usr/bin/env python3
"""Sampler source (Source type 1) rework, patch/Eisenpuls_Synth.cmajor.  Idempotent.  Usage: build_sm.py [patch.cmajor]
 * sample memory 524288 samples per slot (about 10.9 s at 48 kHz, was 96000) and a second (right) channel: bank 0..5 = left / mono, bank 8..13 = right (events smpBankLoad)
 * every other source that reads the sample memory (Granular, Spectral) still sees the mono sum
 * the sampler itself: cubic (Catmull-Rom) interpolation, sample rate correction (the memory is kept at 48 kHz), End, Loop Start / End, ping-pong, crossfaded loop,
   reverse, slices (one slice per key above the root note), velocity > start, gain and stereo width, a short fade at the end of a one-shot
 * parameters: ids SM_BASE (12300) + 16 * slot + j, see layout SM below"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
SM_BASE, SM_STRIDE, SMN = 12300, 16, 524288
# j, key, label, short, min, max, init, unit, kind, labels
SM = [
 (0, "send",   "Sample End",        "End",        0, 1, 1.0, "", "sld", None),
 (1, "slps",   "Sample Loop Start", "Loop Start", 0, 1, 0.0, "", "sld", None),
 (2, "slpe",   "Sample Loop End",   "Loop End",   0, 1, 1.0, "", "sld", None),
 (3, "spp",    "Sample Loop Mode",  "Loop Mode",  0, 1, 0.0, "", "btn", ["Forward", "Ping-Pong"]),
 (4, "sxf",    "Sample Loop Crossfade", "Crossfade", 0, 1, 0.0, "", "sld", None),
 (5, "srev",   "Sample Reverse",    "Reverse",    0, 1, 0.0, "", "btn", ["Off", "On"]),
 (6, "sint",   "Sample Interpolation", "Interp",  0, 1, 1.0, "", "btn", ["Linear", "Cubic"]),
 (7, "sgain",  "Sample Gain",       "Gain",     -24, 12, 0.0, "dB", "sld", None),
 (8, "svst",   "Sample Vel Start",  "Vel > Start",0, 1, 0.0, "", "sld", None),
 (9, "sslice", "Sample Slices",     "Slices",     1, 64, 1.0, "", "stp", None),
 (10, "swid",  "Sample Width",      "Width",      0, 2, 1.0, "", "sld", None),
]
def sm_id(o, j): return SM_BASE + SM_STRIDE * o + j

DSP = r'''    // ---------------- Sampler source (tools/osc/build_sm.py) ----------------
    float[96]   smP;       // slot * 16 + parameter
    float[64]   smDir;     // voice * 8 + slot: +1 / -1 playing direction, 0 = a one-shot has ended
    float[64]   smSl;      // voice * 8 + slot: slice number (-1 = no slice mode)
    float[@TOT@] smBufR;   // right channel (stereo samples), slot * @SMN@
    bool[8]     smSt;      // the slot holds a stereo sample

    float smq (int o, int j)
    {
        return smP.at (o * 16 + j);
    }

    // mono sum of the memory (Granular, Spectral)
    float smMono (int o, int idx)
    {
        int i = o * @SMN@ + clamp (idx, 0, @SMN@ - 1);
        if (smSt.at (o))
            return (smpBuf.at (i) + smBufR.at (i)) * 0.5f;
        return smpBuf.at (i);
    }

    // interpolated stereo read at a position of the slot
    float<2> smGet (int o, float64 pos, bool cubic)
    {
        int   len  = smpLen.at (o);
        int   last = max (len - 1, 0);
        int   i1   = clamp (int (pos), 0, last);
        float t    = float (pos - float64 (i1));
        int   i2   = min (i1 + 1, last);
        int   base = o * @SMN@;
        float aL = smpBuf.at (base + i1);
        float bL = smpBuf.at (base + i2);
        float aR = aL;
        float bR = bL;
        bool  st = smSt.at (o);

        if (st)
        {
            aR = smBufR.at (base + i1);
            bR = smBufR.at (base + i2);
        }

        if (! cubic)
            return float<2> (aL + (bL - aL) * t, aR + (bR - aR) * t);

        int i0 = max (i1 - 1, 0);
        int i3 = min (i1 + 2, last);
        float y0 = smpBuf.at (base + i0);
        float y3 = smpBuf.at (base + i3);
        float oL = ((((-0.5f * y0 + 1.5f * aL - 1.5f * bL + 0.5f * y3) * t) + (y0 - 2.5f * aL + 2.0f * bL - 0.5f * y3)) * t + (-0.5f * y0 + 0.5f * bL)) * t + aL;
        float oR = oL;

        if (st)
        {
            float z0 = smBufR.at (base + i0);
            float z3 = smBufR.at (base + i3);
            oR = ((((-0.5f * z0 + 1.5f * aR - 1.5f * bR + 0.5f * z3) * t) + (z0 - 2.5f * aR + 2.0f * bR - 0.5f * z3)) * t + (-0.5f * z0 + 0.5f * bR)) * t + aR;
        }

        return float<2> (oL, oR);
    }

    // play region (start, end) and loop region (start, end) of a voice, in samples
    float<4> smRegion (int o, int vi)
    {
        float fl = float (smpLen.at (o));
        float rs = clamp (opv (o, 22), 0.0f, 1.0f) * fl;
        float re = fl;
        float sl = smSl.at (vi * 8 + o);

        if (sl >= 0.0f)
        {
            float n = float (clamp (int (smq (o, 9) + 0.5f), 1, 64));
            rs = fl * sl / n;
            re = fl * (sl + 1.0f) / n;
        }
        else
            re = clamp (smq (o, 0), 0.0f, 1.0f) * fl;

        re = clamp (max (re, rs + 8.0f), 0.0f, fl);
        rs = min (rs, re - 8.0f);
        float span = re - rs;
        float ls   = rs + clamp (smq (o, 1), 0.0f, 1.0f) * span;
        float le   = rs + clamp (smq (o, 2), 0.0f, 1.0f) * span;
        le = clamp (max (le, ls + 8.0f), 0.0f, re);
        ls = min (ls, le - 8.0f);
        return float<4> (rs, re, ls, le);
    }

    // note on: starting position (and direction) of the slot's voice
    float64 smNoteOn (int v, int o, int nn, float vel, int oldStart)
    {
        int len = smpLen.at (o);

        if (len < 2)
            return float64 (oldStart);

        int n = clamp (int (smq (o, 9) + 0.5f), 1, 64);
        smSl.at (v * 8 + o) = n > 1 ? float (clamp (nn - int (opv (o, 12) + 0.5f), 0, n - 1)) : -1.0f;
        float<4> r = smRegion (o, v);
        float dir  = smq (o, 5) > 0.5f ? -1.0f : 1.0f;
        smDir.at (v * 8 + o) = dir;
        float off = clamp (smq (o, 8), 0.0f, 1.0f) * clamp (vel, 0.0f, 1.0f) * (r[1] - r[0]) * 0.9f;

        if (dir > 0.0f)
            return float64 (r[0] + off);

        return float64 (r[1] - 1.0f - off);
    }

    // one step of the sampler slot o: stereo sample at the read position, then the position advances
    float<2> smpStep2 (int o, int vi, float freq, float curFreq, float pm, float st)
    {
        float sr  = float (processor.frequency);
        int   len = smpLen.at (o);
        float64 sp = voices.at (vi).synPos.at (o);
        float dir  = smDir.at (vi * 8 + o);
        float<4> rg = smRegion (o, vi);
        float rs = rg[0];
        float re = rg[1];
        float ls = rg[2];
        float le = rg[3];
        bool  lpOn  = opv (o, 23) > 0.5f;
        bool  pp    = smq (o, 3) > 0.5f;
        bool  cubic = smq (o, 6) > 0.5f;
        bool  slice = smSl.at (vi * 8 + o) >= 0.0f;

        float rate = 1.0f;
        if (! slice && opv (o, 7) > 0.5f)
            rate = curFreq / max (float (std::notes::noteToFrequency (int (opv (o, 12) + 0.5f))), 1.0f);
        rate = clamp (rate * float (pow (2.0f, st)) * (48000.0f / sr), 0.0f, 16.0f);

        float<2> out = float<2> (0.0f, 0.0f);

        if (dir != 0.0f)
        {
            float64 rp = sp;

            if (pm != 0.0f)
            {
                rp = sp + float64 (pm * rate * sr / max (freq, 20.0f));
                rp = clamp (rp, 0.0, float64 (len - 1));
            }

            out = smGet (o, rp, cubic);
            float xf = lpOn && ! pp && dir > 0.0f ? clamp (smq (o, 4), 0.0f, 1.0f) * 0.5f * (le - ls) : 0.0f;

            if (xf > 2.0f && float (sp) > le - xf)
            {
                float w  = clamp ((float (sp) - (le - xf)) / xf, 0.0f, 1.0f);
                float<2> o2 = smGet (o, sp - float64 (le - ls - xf), cubic);
                out = out * float (cos (w * 1.5707964f)) + o2 * float (sin (w * 1.5707964f));
            }

            if (! lpOn)   // declick: fade out over the last 48 samples
            {
                float fd = dir > 0.0f ? (re - float (sp)) : (float (sp) - rs);
                out = out * clamp (fd / 48.0f, 0.0f, 1.0f);
            }

            sp += float64 (dir * rate);

            if (lpOn)
            {
                if (pp)
                {
                    if (sp >= float64 (le))       { sp = float64 (2.0f * le) - sp; dir = -1.0f; }
                    else if (sp < float64 (ls))   { sp = float64 (2.0f * ls) - sp; dir = 1.0f; }
                }
                else if (dir > 0.0f)
                {
                    if (sp >= float64 (le))       sp -= float64 (le - ls - xf);
                }
                else if (sp < float64 (ls))
                    sp += float64 (le - ls);

                sp = clamp (sp, 0.0, float64 (len - 1));
            }
            else if ((dir > 0.0f && sp >= float64 (re)) || (dir < 0.0f && sp <= float64 (rs)))
                dir = 0.0f;

            voices.at (vi).synPos.at (o) = sp;
            smDir.at (vi * 8 + o) = dir;
        }

        float g   = float (pow (10.0f, smq (o, 7) / 20.0f));
        float wd  = smq (o, 10);

        if (wd != 1.0f && smSt.at (o))
        {
            float m = (out[0] + out[1]) * 0.5f;
            float s = (out[0] - out[1]) * 0.5f * wd;
            out = float<2> (m + s, m - s);
        }

        return out * g;
    }

'''.replace("@SMN@", str(SMN)).replace("@TOT@", str(SMN * 8))

s = open(PATCH).read()
def block(t, body, anchor_re, indent="    "):
    global s
    a, z = "%s// SM-%s-BEGIN\n" % (indent, t), "%s// SM-%s-END\n" % (indent, t)
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + t)
    s = s[:m.start()] + a + body + z + s[m.start():]
def rep(old, new):
    global s
    if new in s: return
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)
decl = "".join('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s%s ]];\n' % (sm_id(o, p[0]), o + 1, p[2], repr(float(p[4])), repr(float(p[5])), repr(float(p[6])), ", step: 1.0" if p[8] in ("sel", "btn", "stp") else "") for o in range(6) for p in SM)
hand = "".join("    event param%d (float v) { smP.at (%d) = v; }\n" % (sm_id(o, p[0]), o * 16 + p[0]) for o in range(6) for p in SM)
init = "".join("            smP.at (io * 16 + %d) = %sf;\n" % (p[0], repr(float(p[6]))) for p in SM)
block("DSP", DSP, r"^    // PHYS-DSP-BEGIN")
block("DECL", decl, r"^    input event float param1600 ")
block("HAND", hand, r"^    event param1600 ")
block("INIT", init, r"^            op\.at \(io \* 64 \+ 11\) = 3\.0f;\n", "            ")
# memory: 524288 samples per slot, stereo, left = bank 0..5, right = bank 8..13
rep("    float[1048576] smpBuf;\n", "    float[%d] smpBuf;\n" % (SMN * 8))
old_loader = s[s.index("    event smpBankLoad (BankChunk c)"):s.index("    // ---------------- wavetable unison ----------------")]
new_loader = '''    event smpBankLoad (BankChunk c)
    {
        bool right = c.bank >= 8;
        int  o     = clamp (right ? c.bank - 8 : c.bank, 0, 5);
        int  base  = o * %(N)d;

        if (c.total <= 0)
        {
            if (! right)
            {
                smpHas.at (o) = false;
                smpLen.at (o) = 0;
            }

            smSt.at (o) = false;
            return;
        }

        if (c.offset == 0)
        {
            if (right)  smSt.at (o) = false;
            else        smpHas.at (o) = false;
        }

        int cnt = clamp (c.count, 0, 256);

        for (int i = 0; i < cnt; ++i)
        {
            int pos = c.offset + i;
            if (pos >= 0 && pos < %(N)d)
            {
                if (right)  smBufR.at (base + pos) = c.data.at (i);
                else        smpBuf.at (base + pos) = c.data.at (i);
            }
        }

        if (c.offset + cnt >= c.total)
        {
            if (right)
                smSt.at (o) = smpHas.at (o) && clamp (c.total, 1, %(N)d) == smpLen.at (o);
            else
            {
                smpLen.at (o) = clamp (c.total, 1, %(N)d);
                smpHas.at (o) = true;
                smSt.at (o) = false;
                spInvalidate (o);   // SP: the spectral analysis cache
            }
        }
    }

''' % {"N": SMN}
if "bool right = c.bank >= 8;" not in s:
    s = s.replace(old_loader, new_loader)
# the mono read of the other sources
new_rd = '''    // linear-interpolated sample read (mono sum of the memory: Granular, Spectral)
    float smpRead (int o, float64 pos)
    {
        int   i0 = int (pos);
        float fr = float (pos - float64 (i0));
        int   i1 = i0 + 1;
        int   len  = smpLen.at (o);
        if (i1 >= len) i1 = i0;
        return smMono (o, i0) * (1.0f - fr) + smMono (o, i1) * fr;
    }

'''
if "smMono (o, i0)" not in s:
    old_rd = s[s.index("    // linear-interpolated sample read\n"):s.index("    // one step of the sampler slot o; returns the sample")]
    s = s.replace(old_rd, new_rd)
rep("            spRe.at (i) = p < len ? smpBuf.at (sb + p) * w : 0.0f;\n", "            spRe.at (i) = p < len ? smMono (o, p) * w : 0.0f;\n")
rep("        int   sb    = o * 96000;\n", "        int   sb    = o * %d;\n" % SMN)
rep("                            sL = smpStep (o, i, freq, cf, pm + pdPm, sExp);\n                            sR = sL;\n",
    "                            float<2> smw = smpStep2 (o, i, freq, cf, pm + pdPm, sExp);   // SM\n                            sL = smw[0];\n                            sR = smw[1];\n                            stereo = smSt.at (o);\n")
rep("                voices.at (v).synPos.at (o) = float64 (sStart);\n", "                voices.at (v).synPos.at (o) = smNoteOn (v, o, nn, vel, sStart);   // SM\n")
open(PATCH, "w").write(s)
print("ok")
