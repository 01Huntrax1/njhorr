#!/usr/bin/env python3
"""Generates the third plugin "Njohrr Modular" from the synth source: patch_mod/Eisenpuls_Synth.cmajor + Njohrr_Modular.cmajorpatch.
Everything of the synth stays (voices, modulation, OSC racks, all pages); only the end of the signal path differs: instead of the fixed Main rack
a patch matrix (parameters 9700.. from tools/modular/build_matrix.py) connects the sources  Synth  and  Audio In  with the 16 effect modules
(the 16 slots of the Main rack, edited on the FX page) and the Out node.  Every node sums its cables (4 per node, each with its own gain).
A module runs the effect of its slot on the sum; no cable = silent module.  A cable from a later module (or the module itself) carries the
previous sample, so feedback loops are possible (outputs are limited to +-8).
Run:  python3 tools/modular/build_modplugin.py      (tools/regen_plugin.sh calls it)"""
import os, json
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = open(os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')).read()
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:80], src.count(old))
    src = src.replace(old, new)
assert 'MODMAT' in src, 'run tools/modular/build_matrix.py first'
rep('    output stream float<2> out;\n', '    output stream float<2> out;\n    input stream float<2> audioIn;   // MOD-PLUGIN: audio input node of the patch matrix\n')
assert 'EURO' in src, 'run tools/modular/build_euro.py first'
eng = open(os.path.join(root, 'tools', 'modular', 'euro_engine.cmajor.txt')).read()
rep('    float[68] mrGain;\n', '    float[68] mrGain;\n    float[320] eS;       // MOD-PLUGIN: Eurorack state, outputs, MIDI\n    float[48]  eOut;\n    bool[128]  eHeld;\n    int        eNLast = 60;\n    int        eNLow = 60;\n    int        eNHigh = 60;\n    int        eCount = 0;\n    float      eVel = 0.0f;\n    float      eBend = 0.0f;\n    float<2>   eAcc;\n    float<2>[19] mrOut;   // MOD-PLUGIN: output of every node (1 Synth, 2 Audio In, 3.. module 1..16)\n')
rep('''            float<2> rack = fxRunRack (0, float<2> (busInL.at (0) + busInL.at (1) + busInL.at (2), busInR.at (0) + busInR.at (1) + busInR.at (2)));   // FX-NOBUS-SUM
''', '''            // ----- MOD-PLUGIN: patch matrix instead of the fixed Main rack -----
            mrOut.at (1) = float<2> (busInL.at (0) + busInL.at (1) + busInL.at (2), busInR.at (0) + busInR.at (1) + busInR.at (2));
            mrOut.at (2) = float<2> (audioIn[0], audioIn[1]);

            for (int mm = 0; mm < 16; ++mm)
            {
                float<2> acc = float<2> (0.0f, 0.0f);
                bool     any = false;

                for (int cc = 0; cc < 4; ++cc)
                {
                    int sIdx = mrSrc.at (mm * 4 + cc);

                    if (sIdx > 0)
                    {
                        acc += mrOut.at (sIdx) * mrGain.at (mm * 4 + cc);
                        any = true;
                    }
                }

                float<2> ym = any ? fxRunSlot (fxG (0, mm), acc) : float<2> (0.0f, 0.0f);
                mrOut.at (3 + mm) = float<2> (clamp (ym[0], -8.0f, 8.0f), clamp (ym[1], -8.0f, 8.0f));
            }

            float<2> rack = float<2> (0.0f, 0.0f);

            for (int cc = 0; cc < 4; ++cc)
            {
                int sIdx = mrSrc.at (64 + cc);

                if (sIdx > 0)
                    rack += mrOut.at (sIdx) * mrGain.at (64 + cc);
            }

            rack += euroStep (mrOut.at (1), mrOut.at (2));   // EURO: Eurorack rack output
''')
rep('    event midiIn (std::midi::Message msg)\n    {\n', eng + '    event midiIn (std::midi::Message msg)\n    {\n        euroMidi (msg);\n\n')
out = os.path.join(root, 'patch_mod'); os.makedirs(out, exist_ok=True)
open(os.path.join(out, 'Eisenpuls_Synth.cmajor'), 'w').write(src)
meta = json.load(open(os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajorpatch')))
meta.update({"ID": "dev.njohrr.modular", "name": "Njohrr Modular", "description": "Njohrr synthesizer with a patchable effect matrix",
             "plugin": {"pluginCode": "NjMD", "manufacturerCode": "Njhr"}})
meta.pop("view", None)
open(os.path.join(out, 'Njohrr_Modular.cmajorpatch'), 'w').write(json.dumps(meta, indent=4))
print('ok')
