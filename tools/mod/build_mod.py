#!/usr/bin/env python3
"""Mod matrix growth for patch/Eisenpuls_Synth.cmajor: MOD_SLOTS_MAX (256) slots instead of 20 and destinations 258..443 (every Physical / Alpha Juno
parameter).  Run after build_phys.py and build_juno.py.  Idempotent.  Usage: build_mod.py [patch.cmajor]"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "osc"))
import layout as L
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "patch", "Eisenpuls_Synth.cmajor")
N = L.MOD_SLOTS_MAX
DMAX = L.N_DST_TOTAL - 1
s = open(PATCH).read()

for a, b in [("int[32]     mmSrcI;", "int[%d]    mmSrcI;" % N), ("int[32]     mmDstI;", "int[%d]    mmDstI;" % N), ("float[32]   mmAmt;", "float[%d]  mmAmt;" % N),
             ("int[32]     vmodDirty;", "int[%d]    vmodDirty;" % N), ("int[32]     gmodDirty;", "int[%d]    gmodDirty;" % N)]:
    if a in s: s = s.replace(a, b, 1)
if "int         mmTop" not in s:
    s = s.replace("    int         vmodHi; ", "    int         mmTop;      // 1 + the highest mod matrix slot with a source and a destination (set by mmScan)\n    int         gmodHi;     // slots written by the previous computeGlobalMod\n    int         vmodHi; ", 1)

# the 20 original slots: wider destination range, rescan after every change
s = re.sub(r"(event param\d+ \(float v\) \{ mm(?:Src|Dst)I\.at \(\d+\) = clamp \(int \(v \+ 0\.5f\), 0, )(?:257|\d+)(\); )\}",
           lambda m: m.group(1) + (str(DMAX) if "DstI" in m.group(0) else "33") + m.group(2) + "mmScan(); }", s)
s = re.sub(r'(Mod Slot \d+ Dest \()0-257(, see Dest list\)", min: 0.0, max: )257\.0', lambda m: m.group(1) + "0-%d" % DMAX + m.group(2) + "%d.0" % DMAX, s)

def block(tag, body, anchor_re):
    global s
    a, z = "    // MODX-%s-BEGIN\n" % tag, "    // MODX-%s-END\n" % tag
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + tag)
    s = s[:m.start()] + a + body + z + s[m.start():]

SRC = "Off/LFO1-10/Env1-10/Vel/Key/Rand/Freq1-10"
decl = "".join('    input event float param%d [[ name: "Mod Slot %d Source (%s)", min: 0.0, max: 33.0, init: 0.0, step: 1.0 ]];\n'
                '    input event float param%d [[ name: "Mod Slot %d Dest (0-%d, see Dest list)", min: 0.0, max: %d.0, init: 0.0, step: 1.0 ]];\n'
                '    input event float param%d [[ name: "Mod Slot %d Amount", min: -1.0, max: 1.0, init: 0.0 ]];\n'
                % (b, i + 1, SRC, b + 1, i + 1, DMAX, DMAX, b + 2, i + 1)
                for i in range(20, N) for b in [L.mod_slot_base(i)])
hand = "".join("    event param%d (float v) { mmSrcI.at (%d) = clamp (int (v + 0.5f), 0, 33); mmScan(); }\n"
               "    event param%d (float v) { mmDstI.at (%d) = clamp (int (v + 0.5f), 0, %d); mmScan(); }\n"
               "    event param%d (float v) { mmAmt.at (%d)  = v; }\n" % (b, i, b + 1, i, DMAX, b + 2, i)
               for i in range(20, N) for b in [L.mod_slot_base(i)])
block("DECL", decl, r"^    input event float param1600 ")
block("HAND", hand, r"^    event param1600 ")
block("DSP", '''    // highest slot in use (the matrix loops only run that far)
    void mmScan()
    {
        int hi = 0;

        for (int i = 0; i < %d; ++i)
            if (mmDstI.at (i) > 0 && mmSrcI.at (i) > 0)
                hi = i + 1;

        mmTop = hi;
    }

''' % N, r"^    // Sums the matrix for one voice into vmod\[dest\]")

old = s[s.index("    void computeVoiceMod (int vi)"):s.index("    // State-variable filter step for one channel")]
new = '''    void computeVoiceMod (int vi)
    {
        // only the destinations written by the previous call are dirty (0 = nothing: destination 0 is "Off" and never written)
        for (int s = 0; s < vmodHi; ++s)
            vmod.at (vmodDirty.at (s)) = 0.0f;

        bool mat = false;

        for (int s = 0; s < mmHi; ++s)
        {
            int dd = mmDstI.at (s);
            int ss = mmSrcI.at (s);
            vmodDirty.at (s) = 0;
            // Freq modulators only act on the cutoffs (OSC n Cutoff) and the oscillator frequency knobs
            if (ss >= 24 && ! ((dd >= 6 && dd < 60 && (dd - 6) % 9 == 6) || (dd >= 180 && dd < 258)))
                continue;
            if (dd > 0 && ss > 0)
            {
                vmodDirty.at (s) = dd;
                vmod.at (dd) += srcValueVoice (ss, vi) * mmAmt.at (s);
                if ((dd >= 60 && dd < 168) || (dd >= 186 && dd < 258)) mat = true;
            }
        }

        vmodHi = mmHi;
        vmodMat = mat;
    }

    // Sums the matrix for the global (post-voice) destinations into gmod[dest]
    void computeGlobalMod()
    {
        for (int s = 0; s < gmodHi; ++s)
            gmod.at (gmodDirty.at (s)) = 0.0f;

        int top = mmTop;
        int hi  = 0;

        for (int s = 0; s < top; ++s)
        {
            int dd = mmDstI.at (s);
            int ss = mmSrcI.at (s);
            gmodDirty.at (s) = 0;
            if (dd > 0 && dd < 6 && ss > 0)
            {
                hi = s + 1;
                gmodDirty.at (s) = dd;
                gmod.at (dd) += srcValueGlobal (ss) * mmAmt.at (s);
            }
            else if (dd > 0 && ss > 0)
                hi = s + 1;
        }

        gmodHi = top;
        mmHi   = hi;
    }

'''
s = s.replace(old, new, 1)
s = s.replace("            for (int fs = 0; fs < 20; ++fs)\n                if (mmSrcI.at (fs) >= 24", "            for (int fs = 0; fs < mmTop; ++fs)\n                if (mmSrcI.at (fs) >= 24", 1)
open(PATCH, "w").write(s)
print("ok")
