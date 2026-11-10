#!/usr/bin/env python3
"""Idempotent (marker MXRANGE-DSP): more modulation strength.
* FM / PM / TZFM matrix cells go from 0..100 % to 0..400 % (PD, RM, AM, XF, FD, XR, CP stay at 100 %: they saturate there); the exponential FM and TZFM
  clamps move from +-2 to +-8 (at 400 % and a full scale modulator FM reaches the frequency limits), the mod matrix destinations of these cells clamp at 4.
* Mod matrix slot Amount goes from -1..1 to -4..4 (+-400 %); the destinations scale with it as before (a full +-100 % still means the old range),
  so existing presets sound the same."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'MXRANGE-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global src
    assert src.count(old) == n, (old[:70], src.count(old), n)
    src = src.replace(old, new)
src, k = re.subn(r'(name: "(?:FM|PM|TZFM) \d to \d", min: 0\.0, max: )100\.0', r'\g<1>400.0', src)
assert k == 108, k
rep('am = clamp (am + vmod.at (60 + mi) * 0.5f, 0.0f, 1.0f);', 'am = clamp (am + vmod.at (60 + mi) * 0.5f, 0.0f, 4.0f);   // MXRANGE-DSP: FM / PM / TZFM go to 400 %')
rep('ap = clamp (ap + vmod.at (96 + mi) * 0.5f, 0.0f, 1.0f);', 'ap = clamp (ap + vmod.at (96 + mi) * 0.5f, 0.0f, 4.0f);')
rep('az = clamp (az + vmod.at (1308 + mi) * 0.5f, 0.0f, 1.0f);', 'az = clamp (az + vmod.at (1308 + mi) * 0.5f, 0.0f, 4.0f);')
rep('sExp += clamp (fmx, -2.0f, 2.0f) * 4.0f;', 'sExp += clamp (fmx, -8.0f, 8.0f) * 4.0f;')
rep('tzp += clamp (tzv, -2.0f, 2.0f) * 4.0f * freq / sr;', 'tzp += clamp (tzv, -8.0f, 8.0f) * 4.0f * freq / sr;')
src, k = re.subn(r'(Mod Slot \d+ Amount", min: )-1\.0(, max: )1\.0', r'\g<1>-4.0\g<2>4.0', src)
assert k == 256, k
open(path, 'w').write(src)
print('ok')
