#!/usr/bin/env python3
"""Idempotent (marker MXDST-DSP): mod matrix destinations for the TZFM matrix and the XF / FD / XR / CP matrices:
dest 1308 + 36 * m + 6 * source + target, m = 0 TZFM, 1 XF, 2 FD, 3 XR, 4 CP (1308 .. 1487).  Like RM / AM: +-50 % of the range at full amount.
Slot Dest parameters now go to 1487."""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'MXDST-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global src
    assert src.count(old) == n, (old[:70], src.count(old))
    src = src.replace(old, new)
rep('(0-1307, see Dest list)", min: 0.0, max: 1307.0', '(0-1487, see Dest list)", min: 0.0, max: 1487.0', 256)
src, k = __import__('re').subn(r'(mmDstI\.at \(\d+\) = clamp \(int \(v \+ 0\.5f\), 0, )1307\)', r'\g<1>1487)', src)
assert k == 256, k
rep('if ((dd >= 60 && dd < 168) || (dd >= 186 && dd < 258)) mat = true;', 'if ((dd >= 60 && dd < 168) || (dd >= 186 && dd < 258) || dd >= 1308) mat = true;   // MXDST-DSP')
rep('                        float az = tzAmt.at (mi);\n', '                        float az = tzAmt.at (mi);\n                        if (vmodMat)   // MXDST-DSP: TZFM 1308 + n\n                            az = clamp (az + vmod.at (1308 + mi) * 0.5f, 0.0f, 1.0f);\n')
rep('                    if (fmAny)\n                    {\n                        float tzv = tzIn.at (o);', '                    if (fmAny || vmodMat)\n                    {\n                        float tzv = tzIn.at (o);')
rep('                    if (fmAny)\n                    {\n                        for (int xs = 0; xs < 6; ++xs)', '                    if (fmAny || vmodMat)\n                    {\n                        for (int xs = 0; xs < 6; ++xs)')
rep('''                            float acp = mxAmt.at (192 + xi);

''', '''                            float acp = mxAmt.at (192 + xi);

                            if (vmodMat)   // MXDST-DSP: XF 1344 + n, FD 1380 + n, XR 1416 + n, CP 1452 + n
                            {
                                axf = clamp (axf + vmod.at (1344 + xi) * 0.5f, 0.0f, 1.0f);
                                afd = clamp (afd + vmod.at (1380 + xi) * 0.5f, 0.0f, 1.0f);
                                axr = clamp (axr + vmod.at (1416 + xi) * 0.5f, 0.0f, 1.0f);
                                acp = clamp (acp + vmod.at (1452 + xi) * 0.5f, 0.0f, 1.0f);
                            }

''')
open(path, 'w').write(src)
print('ok')
