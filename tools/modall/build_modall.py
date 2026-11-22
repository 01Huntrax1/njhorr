#!/usr/bin/env python3
"""All slider parameters as modulation destinations (dest 1584 + k).  Idempotent.  Usage: build_modall.py
 * the eligible parameters (kind "sld" with a one-line handler) are listed once in tools/modall/ids.json
 * handler `event paramN (float v) { BODY }` becomes `void modpK (float v) { BODY }` + an event that stores the base value and applies base + modulation
 * genUpdate() runs every 32 samples: sums the matrix slots with dest >= 1584 (global sources), applies changed values, restores the base of unrouted ones
 * modulation amount: amount * source * range * 0.5 (same scale as the other destinations)"""
import os, re, json, sys
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, "..", "..")
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, "patch", "Eisenpuls_Synth.cmajor")
IDS = os.path.join(HERE, "ids.json"); OLDMAX = 1583; FIRST = 1584
s = open(PATCH).read()
if "// MODALL-BEGIN" in s and os.path.exists(IDS):
    print("already patched"); sys.exit(0)
if os.path.exists(IDS):
    ids = json.load(open(IDS))
else:
    g = open(os.path.join(R, "native_ui", "NjoData.gen.cpp")).read()
    spec = {}
    for m in re.finditer(r'Spec \{ (\d+), NJ_S\("([^"]*)"\), (-?[\d.e+-]+), (-?[\d.e+-]+), (-?[\d.e+-]+), NJ_S\("([^"]*)"\), NJ_S\("([^"]*)"\)', g):
        spec[int(m.group(1))] = (m.group(2), float(m.group(3)), float(m.group(4)), m.group(7))
    ids = []
    for m in re.finditer(r'^( *)event param(\d+) \(float v\) \{(.*)\}\s*$', s, re.M):
        i = int(m.group(2)); b = m.group(3).strip()
        if i in spec and spec[i][3] == "sld" and b and "mm" not in b and "return" not in b and 4000 > i or (i in spec and i >= 4300 and spec[i][3] == "sld" and b and "mm" not in b and "return" not in b):
            ids.append([i, spec[i][0], spec[i][1], spec[i][2]])
    ids.sort(); json.dump(ids, open(IDS, "w"))
N = len(ids); idx = {r[0]: k for k, r in enumerate(ids)}
funcs = []; cnt = 0
def rep(m):
    global cnt
    i = int(m.group(2))
    if i not in idx: return m.group(0)
    k = idx[i]; lo, hi = ids[k][2], ids[k][3]; body = m.group(3).strip(); cnt += 1
    funcs.append("    void modp%d (float v) { %s }" % (k, body))
    return "%sevent param%d (float v) { genBase.at (%d) = v; genSet.at (%d) = 1; modp%d (clamp (v + genNorm.at (%d) * %s, %s, %s)); }" % (
        m.group(1), i, k, k, k, k, repr(round((hi - lo) * 0.5, 6)) + "f", repr(lo) + "f", repr(hi) + "f")
s = re.sub(r'^( *)event param(\d+) \(float v\) \{(.*)\}[ \t]*$', rep, s, flags=re.M)
assert cnt == N, (cnt, N)
def tree(a, b, ind):   # binary search over the parameter index (Cmajor has no switch)
    p = " " * ind
    if b - a == 1:
        lo, hi = ids[a][2], ids[a][3]
        return "%smodp%d (clamp (b + n * %sf, %sf, %sf));\n" % (p, a, repr(round((hi - lo) * 0.5, 6)), repr(lo), repr(hi))
    mid = (a + b) // 2
    return "%sif (k < %d)\n%s{\n%s%s}\n%selse\n%s{\n%s%s}\n" % (p, mid, p, tree(a, mid, ind + 4), p, p, p, tree(mid, b, ind + 4), p)
cases = [tree(0, N, 8)]
BLOCK = '''    // MODALL-BEGIN
    float[%(N)d] genBase;      // value set by the host / UI
    int[%(N)d]   genSet;       // 1 = genBase is valid
    float[%(N)d] genNorm;      // applied modulation (amount * source summed, 1 = half the range)
    float[%(N)d] genAcc;
    int[%(N)d]   genMark;
    int[%(N)d]   genIn;
    int[512]     genList;
    int          genN;
    int          genStamp;
    int          genTick;

%(funcs)s

    // applies base + modulation of generic destination k
    void genApply (int k)
    {
        float b = genBase.at (k);
        float n = genNorm.at (k);

        if (genSet.at (k) == 0)
            return;

%(cases)s    }

    // sums the slots whose destination is a generic parameter (dest >= %(F)d) and applies the changes
    void genUpdate()
    {
        if (genN == 0 && mmTop == 0)
            return;

        genStamp++;

        for (int i = 0; i < genN; ++i)
            genAcc.at (genList.at (i)) = 0.0f;

        int n = genN;

        for (int s = 0; s < mmTop; ++s)
        {
            int dd = mmDstI.at (s);
            int ss = mmSrcI.at (s);

            if (dd >= %(F)d && ss > 0)
            {
                int k = dd - %(F)d;

                if (k >= %(N)d)
                    continue;

                if (genMark.at (k) != genStamp)
                {
                    genMark.at (k) = genStamp;

                    if (genIn.at (k) == 0)
                    {
                        genIn.at (k) = 1;
                        genAcc.at (k) = 0.0f;
                        genList.at (n) = k;
                        ++n;
                    }
                }

                genAcc.at (k) += srcValueGlobal (ss) * mmAmt.at (s);
            }
        }

        int m = 0;

        for (int i = 0; i < n; ++i)
        {
            int   k = genList.at (i);
            float t = genAcc.at (k);

            if (abs (t - genNorm.at (k)) > 0.0005f)
            {
                genNorm.at (k) = t;
                genApply (k);
            }

            if (genMark.at (k) == genStamp)
            {
                genList.at (m) = k;
                ++m;
            }
            else
            {
                genIn.at (k)  = 0;
                genAcc.at (k) = 0.0f;
            }
        }

        genN = m;
    }
    // MODALL-END

''' % dict(N=N, funcs="\n".join(funcs), cases="".join(cases), F=FIRST)
a = "    // MODX-DSP-BEGIN\n"; assert s.count(a) == 1
s = s.replace(a, BLOCK + a)
a = "            if (dd > 0 && ss > 0)\n            {\n                vmodDirty.at (s) = dd;"; assert s.count(a) == 1
s = s.replace(a, a.replace("dd > 0 && ss", "dd > 0 && dd < %d && ss" % FIRST))
a = "            computeGlobalMod();\n"; assert s.count(a) == 1
s = s.replace(a, a + "            if ((++genTick & 31) == 0)\n                genUpdate();\n")
top = FIRST + N - 1
s = s.replace("clamp (int (v + 0.5f), 0, %d)" % OLDMAX, "clamp (int (v + 0.5f), 0, %d)" % top)
s = re.sub(r'(Dest \(0-)%d(, see Dest list\)", min: 0.0, max: )%d\.0' % (OLDMAX, OLDMAX), lambda m: "%s%d%s%d.0" % (m.group(1), top, m.group(2), top), s)
open(PATCH, "w").write(s); print("patched", N, "parameters, dest 1584 ..", top)
