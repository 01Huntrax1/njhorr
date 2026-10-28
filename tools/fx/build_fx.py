import re
#!/usr/bin/env python3
"""Idempotent: inserts the convolution reverb (FX type 12) into patch/Eisenpuls_Synth.cmajor."""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if '// FX-CONV' in src:
    print('already applied'); sys.exit(0)
part = open(os.path.join(root, 'tools', 'fx', 'conv_dsp.cmajor.part')).read()

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (old, src.count(old))
    src = src.replace(old, new)

rep('    input event BankChunk tblLoad;', '    input event BankChunk irLoad;        // convolution reverb impulse response (bank = rack 0..2)  // FX-CONV\n    input event BankChunk tblLoad;')
rep('        fxInit();\n', '        fxInit();\n        cvInit();\n')
rep('        int nt = clamp (t, 0, 11);\n\n        if (nt != fxType.at (s))\n        {\n            fxType.at (s) = nt;\n            fxResetSlot (s);\n        }\n\n        fxDirty.at (s) = true;',
    '        int nt = clamp (t, 0, 12);\n\n        if (nt != fxType.at (s))\n        {\n            fxType.at (s) = nt;\n            fxResetSlot (s);\n        }\n\n        fxDirty.at (s) = true;\n        cvUpdateOwner (s / 10);')
rep('    // ---------------- one function per effect', part + '    // ---------------- one function per effect')
rep('''        else if (ty == 11)
        {
            // compressor''', '''        else if (ty == 12)
        {
            // convolution reverb: size, decay, damp (rebuild the IR when they or the mode change), pre-delay, width, tone filters
            fxD.at (db)     = p1;
            fxD.at (db + 1) = p2;
            fxD.at (db + 2) = p3;
            fxD.at (db + 3) = float (int (p4 * 0.2f * sr));
            fxD.at (db + 4) = p5 * 2.0f;

            float p6  = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
            float lpf = p6 < 0.5f ? fxExpMap (p6 * 2.0f, 800.0f, 20000.0f) : 20000.0f;
            float hpf = p6 > 0.5f ? fxExpMap ((p6 - 0.5f) * 2.0f, 20.0f, 2000.0f) : 20.0f;
            fxD.at (db + 5) = clamp (1.0f - float (exp (-float (twoPi) * lpf * dt)), 0.0f, 1.0f);
            fxD.at (db + 6) = clamp (1.0f - float (exp (-float (twoPi) * hpf * dt)), 0.0f, 1.0f);

            int rk = s / 10;

            if (cvOwner.at (rk) == s)
            {
                int ee = rk * 32;
                int md = clamp (fxMode.at (s), 0, 8);

                if (cvF.at (ee + 14) != p1 || cvF.at (ee + 15) != p2 || cvF.at (ee + 16) != p3 || cvI.at (ee + 13) != md || cvF.at (ee + 17) < 0.0f)
                {
                    cvF.at (ee + 14) = p1;
                    cvF.at (ee + 15) = p2;
                    cvF.at (ee + 16) = p3;
                    cvF.at (ee + 17) = 0.0f;
                    cvI.at (ee + 13) = md;
                    cvI.at (ee + 9)  = int (0.15f * sr);
                }
            }
        }
        else if (ty == 11)
        {
            // compressor''')
rep('        else if (ty == 11) y = fxComp   (s, x);\n', '        else if (ty == 11) y = fxComp   (s, x);\n        else if (ty == 12) y = fxConv   (s, x);\n')
rep('    event tblLoad (BankChunk c)\n', '    event irLoad (BankChunk c)\n    {\n        cvUserChunk (clamp (c.bank, 0, 2), c.offset, c.count, c.total, c);\n    }\n\n    event tblLoad (BankChunk c)\n')
# the effect type parameters must reach the new type (12 = Convolution), otherwise the host clamps it to the compressor
src = re.sub(r'(FX \d+ Type",\s*min: 0\.0, max: )11\.0', r'\g<1>12.0', src)
open(path, 'w').write(src)
print('ok')
