#!/usr/bin/env python3
"""Modulated FM / PM / PD / TZFM / RM / AM / XF / FD / XR / CP matrices: CPU.  Idempotent.  python3 tools/osc/build_matfast.py [patch.cmajor]
Before: one modulated matrix cell (or even a Bagpipe destination, dest >= 1308 caught 1488..1583) switched the matrix mode on for the whole voice, and in that
mode silent oscillators were no longer skipped (every oscillator ran its full chain) and every cell of the six matrices did a clamp.
Now: * the mode is only on for dest 60..167, 186..257 and 1308..1487
     * silent oscillators are only computed when they are the source of a modulated cell (bit mask from computeVoiceMod), like for unmodulated amounts
     * a cell without modulation keeps its amount (no clamp, same value)"""
import os, re, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, "patch", "Eisenpuls_Synth.cmajor"); s = open(P).read()
if "MATFAST2" in s: print("already patched"); raise SystemExit
def rep(a, b):
    global s
    if b in s and a not in s: return   # this edit is already in (a stage 1 patched file gets stage 2 only)
    assert s.count(a) == 1, (a[:70], s.count(a)); s = s.replace(a, b)
rep("    bool        vmodMat;    // some mod slot targets an FM / PM / PD matrix cell (dest 60..167)\n", "    bool        vmodMat;    // some mod slot targets an FM / PM / PD matrix cell (dest 60..167)\n    int         vmodSrc;    // MATFAST: bit o = oscillator o is the source of a modulated matrix cell\n")
rep("    // Sums the matrix for one voice into vmod[dest]\n", '''    // MATFAST: the source oscillator of a modulated matrix cell (FM / PM / PD 60.., RM / AM 186.., TZFM / XF / FD / XR / CP 1308..: 36 cells each, source * 6 + destination)
    int matSrcBit (int dd)
    {
        int n = dd < 168 ? dd - 60 : (dd < 258 ? dd - 186 : dd - 1308);
        return 1 << ((n % 36) / 6);
    }

    // Sums the matrix for one voice into vmod[dest]
''')
rep("        bool mat = false;\n\n        for (int s = 0; s < mmHi; ++s)", "        bool mat = false;\n        int  srcMask = 0;\n\n        for (int s = 0; s < mmHi; ++s)")
rep("                if ((dd >= 60 && dd < 168) || (dd >= 186 && dd < 258) || dd >= 1308) mat = true;   // MXDST-DSP\n",
    "                if ((dd >= 60 && dd < 168) || (dd >= 186 && dd < 258) || (dd >= 1308 && dd < 1488))   // MXDST-DSP, MATFAST\n                {\n                    mat = true;\n                    srcMask |= matSrcBit (dd);\n                }\n")
rep("        vmodMat = mat;\n", "        vmodMat = mat;\n        vmodSrc = srcMask;\n")
rep("if (lvl <= 0.0005f && ! fmUsed.at (o) && ! vmodMat)", "if (lvl <= 0.0005f && ! fmUsed.at (o) && (vmodSrc & (1 << o)) == 0)   // MATFAST")
pat = re.compile(r"^( *)(am|ap|ad|az|ar|aa|axf|afd|axr|acp) = clamp \(\2 \+ (vmod\.at \([^()]*\)) \* 0\.5f, ([\d.]+f), ([\d.]+f)\);(.*)$", re.M)
n = len(pat.findall(s)); assert n in (0, 10), n
s = pat.sub(lambda m: "%sif (%s != 0.0f)\n%s    %s = clamp (%s + %s * 0.5f, %s, %s);%s" % (m.group(1), m.group(3), m.group(1), m.group(2), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)), s)

# stage 2: a source row of a matrix is skipped when nothing feeds from that oscillator (no amount set in any matrix, no modulated cell)
rep("                    for (int fs = 0; fs < 6; ++fs)\n                    {\n                        int   mi = fs * 6 + fd;\n", "                    for (int fs = 0; fs < 6; ++fs)\n                    {\n                        if (! fmUsed.at (fs) && (vmodSrc & (1 << fs)) == 0)   // MATFAST2\n                            continue;\n\n                        int   mi = fs * 6 + fd;\n")
rep("                    {\n                        int   ri = rs * 6 + o;\n", "                    {\n                        if (! fmUsed.at (rs) && (vmodSrc & (1 << rs)) == 0)   // MATFAST2\n                            continue;\n\n                        int   ri = rs * 6 + o;\n")
rep("                        {\n                            int   xi = xs * 6 + o;\n", "                        {\n                            if (! fmUsed.at (xs) && (vmodSrc & (1 << xs)) == 0)   // MATFAST2\n                                continue;\n\n                            int   xi = xs * 6 + o;\n")
open(P, "w").write(s); print("patched")
