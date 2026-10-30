#!/usr/bin/env python3
"""Adds the per-oscillator Wavetable "Aliasing" switch (ids 2000 + osc) to patch/Eisenpuls_Synth.cmajor.  Off: band-limited mip levels (default).
On: every note reads the full 2048-sample level, so the harmonics above Nyquist fold back (digital, gritty wavetable sound).  Run after build_kick.py.  Idempotent."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
s = open(PATCH).read()
def block(tag, body, anchor_re, indent="    "):
    global s
    a, z = "%s// ALIAS-%s-BEGIN\n" % (indent, tag), "%s// ALIAS-%s-END\n" % (indent, tag)
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + tag)
    s = s[:m.start()] + a + body + z + s[m.start():]
block("DSP", "    float[6] wtAlias;     // Wavetable Aliasing switch per slot (ids 2000 + slot)\n\n", r"^    // mip level for a note frequency")
block("DECL", "".join('    input event float param%d [[ name: "OSC %d WT Aliasing", min: 0.0, max: 1.0, init: 0.0, step: 1.0 ]];\n' % (2000 + o, o + 1) for o in range(6)), r"^    input event float param1600 ")
block("HAND", "".join("    event param%d (float v) { wtAlias.at (%d) = v; }\n" % (2000 + o, o) for o in range(6)), r"^    event param1600 ")
if "wtAlias.at (o) > 0.5f" not in s:
    old = "        float udr = clamp (opv (o, 28), 0.0f, 1.0f) * 0.007f;\n"
    assert old in s
    s = s.replace(old, "        // Aliasing switch: no band-limiting, always the full level\n        if (wtAlias.at (o) > 0.5f)\n            lvlAll = 0;\n\n" + old, 1)
open(PATCH, "w").write(s)
print("ok")
