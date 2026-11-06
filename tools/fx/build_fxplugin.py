#!/usr/bin/env python3
"""Generates the effects-only plugin "Njohrr FX" from the synth source: patch_fx/Eisenpuls_Synth.cmajor + Njohrr_FX.cmajorpatch.
Same processor, same parameter ids (presets of the FX racks load in both plugins), but an audio input stream instead of the synth voices:
  * the input feeds the three bus inputs (Main, Bus 1, Bus 2) through the pan / Drive stage; the synth Master level is not applied (unity gain);
  * Drive is a blend (0 = clean input) and defaults to 0, Bus 1 / Bus 2 return levels default to 0 (the buses are parallel racks);
  * the output limit is +-8 instead of +-1 (a hard clip at 0 dBFS has no place in an effect).
Run:  python3 tools/fx/build_fxplugin.py      (tools/regen_plugin.sh calls it)"""
import os, re, json
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = open(os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')).read()
def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (old[:80], src.count(old))
    src = src.replace(old, new)
# the VST3 host streams belong to the synth plugin only
src = ''.join(l for l in src.splitlines(True) if not any(k in l for k in ('VST3-EP', 'VST3-IN', 'VST3-OUT')))
rep('    output stream float<2> out;\n', '    output stream float<2> out;\n    input stream float<2> audioIn;   // FX-PLUGIN: the signal the racks process\n')
rep('                float rawL = shapeSig (mixSynthL.at (bg) * 0.35f, driveEff) * gPanL;\n                float rawR = shapeSig (mixSynthR.at (bg) * 0.35f, driveEff) * gPanR;\n',
    '                float xinL = audioIn[0];\n                float xinR = audioIn[1];\n'
    '                float rawL = (xinL + driveEff * (shapeSig (xinL, driveEff) - xinL)) * gPanL;   // FX-PLUGIN: Drive blends the shaped input in\n'
    '                float rawR = (xinR + driveEff * (shapeSig (xinR, driveEff) - xinR)) * gPanR;\n')
rep('                busInL.at (bg) = dcL * masterLevel;\n                busInR.at (bg) = dcR * masterLevel;\n', '                busInL.at (bg) = dcL;\n                busInR.at (bg) = dcR;\n')
rep('            outL = clamp (outL, -1.0f, 1.0f);\n            outR = clamp (outR, -1.0f, 1.0f);\n', '            outL = clamp (outL, -8.0f, 8.0f);\n            outR = clamp (outR, -8.0f, 8.0f);\n')
rep('    float driveAmt     = 0.1f;\n', '    float driveAmt     = 0.0f;\n')
rep('    input event float param28 [[ name: "Drive",                        min: 0.0,   max: 1.0,    init: 0.1   ]];', '    input event float param28 [[ name: "Drive",                        min: 0.0,   max: 1.0,    init: 0.0   ]];')
# the input feeds the Main rack only (the Bus racks are gone)
rep('float<2> (busInL.at (0) + busInL.at (1) + busInL.at (2), busInR.at (0) + busInR.at (1) + busInR.at (2)));   // FX-NOBUS-SUM', 'float<2> (busInL.at (0), busInR.at (0)));')
out = os.path.join(root, 'patch_fx'); os.makedirs(out, exist_ok=True)
open(os.path.join(out, 'Eisenpuls_Synth.cmajor'), 'w').write(src)
meta = json.load(open(os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajorpatch')))
meta.update({"ID": "dev.njohrr.fx", "name": "Njohrr FX", "description": "Njohrr effects", "category": "fx", "isInstrument": False,
             "plugin": {"pluginCode": "NjFX", "manufacturerCode": "Njhr"}})
meta.pop("view", None)
open(os.path.join(out, 'Njohrr_FX.cmajorpatch'), 'w').write(json.dumps(meta, indent=4))
print('ok')
