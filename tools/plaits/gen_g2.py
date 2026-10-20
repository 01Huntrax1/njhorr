#!/usr/bin/env python3
"""Generates the tables needed by the six-op FM and wave terrain engines (luts/syx_banks.part, luts/wav_integrated_waves.part, luts/fm_algos.part)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_lut
SRC = gen_lut.SRC; HERE = gen_lut.HERE
def chunk(vals):
    return ",\n".join("        " + ", ".join(vals[i:i+16]) for i in range(0, len(vals), 16))
def nums(name):
    ty, body = gen_lut.find(name)
    body = re.sub(r"//[^\n]*", "", body)
    return [str(int(v, 0)) for v in body.replace("\n", " ").split(",") if v.strip()]
# syx banks
allv = []
for b in range(3): allv += nums("syx_bank_%d" % b)
assert len(allv) == 12288
open(HERE + "/luts/syx_banks.part", "w").write("    const int[12288] plSyx =\n    (\n%s\n    );\n" % chunk(allv))
w = nums("wav_integrated_waves"); assert len(w) == 25344
open(HERE + "/luts/wav_integrated_waves.part", "w").write("    const int[25344] plWavInt =\n    (\n%s\n    );\n" % chunk(w))
# algorithms
t = open(SRC + "/plaits/dsp/fm/algorithms.cc").read()
i = t.index("Algorithms<6>::opcodes_[32][6]"); j = t.index("#define INSTANTIATE_RENDERER")
blk = re.sub(r"//[^\n]*", "", t[i:j]); blk = blk[blk.index("{") :]
ent = [e.strip() for e in re.sub(r"[{}\n;]", " ", blk).split(",") if e.strip()]
def MOD(n): return n << 4
def ADD(n): return n | 4
def OUT(n): return n
FB_SRC = 0x40; FB_DST = MOD(3); FB = FB_SRC | FB_DST; NO_MOD = 0; OUTPUT = ADD(0)
ops = [eval(e) for e in ent]; assert len(ops) == 192, len(ops)
renderers = {(1,-2,False),(1,-2,True),(1,-1,False),(1,-1,True),(1,0,False),(1,0,True),(3,2,True),(2,1,True)}
tab = []; ismod = []
for a in range(32):
    oc = ops[a*6:a*6+6]; calls = [(0,0,0,0,0)]*6
    for k in range(6): ismod.append(1 if oc[k] & 3 else 0)
    i = 0
    while i < 6:
        opcode = oc[i]; n = 1
        while i + n < 6:
            frm = oc[i+n-1]; to = (oc[i+n] & 0x30) >> 4
            if (frm & 4) or (frm & 3) != to:
                if to == (opcode & 3): n = 1
                break
            n += 1
        found = False
        for attempt in range(2):
            out_op = oc[i+n-1]; add = bool(out_op & 4); ms = -3
            if not (opcode & 0x30): ms = -1
            elif (opcode & 0x30) != 0x30: ms = -2
            else:
                for jj in range(n):
                    if oc[i+jj] & 0x40: ms = jj
            if (n, ms, add) in renderers:
                calls[i] = (n, ms, int(add), (opcode & 0x30) >> 4, out_op & 3); found = True; break
            elif n != 1: n = 1
        assert found, (a, i)
        i += n
    for c in calls: tab += [str(x) for x in c]
open(HERE + "/luts/fm_algos.part", "w").write("    const int[960] plFmCalls =\n    (\n%s\n    );\n    const int[192] plFmIsMod =\n    (\n%s\n    );\n" % (chunk(tab), chunk([str(x) for x in ismod])))
print("ok")
