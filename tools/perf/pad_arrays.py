#!/usr/bin/env python3
"""Pads processor arrays to a power of two (index wrap becomes a mask instead of a modulo).  Idempotent.  Usage: pad_arrays.py [patch.cmajor]
Only index arithmetic: the arrays are addressed by slot * stride + k, the extra entries stay unused."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
# old size -> padded size (the names are the arrays of the per-sample voice loop)
SIZES = {1088: 2048, 4992: 8192, 13056: 16384, 3264: 4096, 96: 128, 448: 512, 192: 256}   # the Eurorack / matrix arrays (mrSrc, eK ...) are anchors of tools/modular/*.py and stay as they are
NAMES = {1088: None, 4992: ["fxP"], 13056: ["fxD"], 3264: ["fxPh"],
         96: ["oscOrd", "wtP", "smP", "adP", "bpP", "dkP", "grP", "jpP", "kickP", "sfP", "spP", "terP", "wgP", "oscSeq"],
         448: ["sqMl"], 192: ["phyP"]}
s = open(PATCH).read(); n = 0
def sub(m):
    global n
    pre, size, gap, name = m.group(1), int(m.group(2)), m.group(3), m.group(4)
    if size in SIZES and (NAMES[size] is None or name in NAMES[size]):
        n += 1
        return "%s[%d]%s%s" % (pre, SIZES[size], gap, name)
    return m.group(0)
s = re.sub(r"^(    (?:float|int|bool|float64))\[(\d+)\](\s+)(\w+)", sub, s, flags=re.M)
open(PATCH, "w").write(s); print("padded", n)
