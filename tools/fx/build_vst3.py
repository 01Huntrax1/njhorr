#!/usr/bin/env python3
"""Idempotent: DSP side of the VST3 host, marker VST3-HOST.
Three audio streams between the DSP and the plugin wrapper (which hosts the VST3 plugins, see include/cmajor/helpers/NjoVst3Host.h):
  input  hostSrc   stereo output of the hosted instrument (OSC source type 13 "VST3")
  input  hostRet   stereo return of the hosted effect
  output hostSend  stereo send to the hosted effect (sum of all FX slots of type 19 "VST3")
The wrapper works in chunks of 64 samples, the hosted effect therefore answers one chunk late: VST_CHUNK = 64 samples of latency. The dry signal of the
slot is delayed by the same amount (per slot) so the Mix control stays phase-correct.
The source feeds the lowest active voice only (the instrument is polyphonic itself); the voice's amp envelope and the slot's filter / distortion / pan act on it."""
import os, sys, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'VST3-HOST' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, cnt=1):
    global src
    assert src.count(old) == cnt, (old[:70], src.count(old))
    src = src.replace(old, new)
rep('    output stream float<2> out;\n', '    output stream float<2> out;\n'
    '    input stream float<2> hostSrc;     // VST3-EP: hosted instrument (VST3-HOST)\n'
    '    input stream float<2> hostRet;     // VST3-EP: return of the hosted effect\n'
    '    output stream float<2> hostSend;   // VST3-EP: send to the hosted effect\n')
# types
rep('max: 12.0, init: 0.0, step: 1.0 ]];', 'max: 13.0, init: 0.0, step: 1.0 ]];', 0) if False else None
n = len(re.findall(r'name: "OSC \d Source", min: 0.0, max: 12.0', src)); assert n == 6, n
src = re.sub(r'(name: "OSC \d Source", min: 0.0, max: )12\.0', r'\g<1>13.0', src)
n = len(re.findall(r'FX \d+ Type",\s+min: 0.0, max: 18.0', src)); assert n == 30, n
src = re.sub(r'(FX \d+ Type",\s+min: 0.0, max: )18\.0', r'\g<1>19.0', src)
rep('int nt = clamp (t, 0, 18);', 'int nt = clamp (t, 0, 19);')
# state
rep('    Voice[8] voices;', '    Voice[8] voices;\n\n'
    '    // VST3-HOST: streams from / to the plugin wrapper, per-slot dry delay (64 samples)\n'
    '    float<2>    hostSrcS;\n    float<2>    hostRetS;\n    float<2>    hostSendAcc;\n    float<2>    hostXd;\n'
    '    float[3840] hostDry;\n    int         hostDryPos;\n    int         hostVoice;\n')
# FX slot
rep('        else if (ty == 18) y = fxFb     (s, x);\n', '        else if (ty == 18) y = fxFb     (s, x);\n        else if (ty == 19) y = fxHost   (s, x);   // VST3-HOST\n')
rep('        float mix = clamp (fxMix.at (s), 0.0f, 1.0f);\n        return x + (y - x) * mix;',
    '        float mix = clamp (fxMix.at (s), 0.0f, 1.0f);\n        if (ty == 19)\n            return hostXd + (y - hostXd) * mix;   // VST3-HOST: the dry signal is delayed like the return\n        return x + (y - x) * mix;')
rep('    // One slot: dry/wet mix of the selected effect; empty and bypassed slots pass the signal through untouched\n',
    '    // VST3-HOST: send to the hosted effect, the return arrives one chunk late; the dry signal is delayed by the same 64 samples\n'
    '    float<2> fxHost (int s, float<2> x)\n    {\n'
    '        int p = (s * 64 + hostDryPos) * 2;\n'
    '        hostXd = float<2> (hostDry.at (p), hostDry.at (p + 1));\n'
    '        hostDry.at (p)     = x[0];\n        hostDry.at (p + 1) = x[1];\n'
    '        hostSendAcc += x;\n'
    '        return hostRetS;\n    }\n\n'
    '    // One slot: dry/wet mix of the selected effect; empty and bypassed slots pass the signal through untouched\n')
# main loop
rep('            float sr = float (processor.frequency);\n\n            flfPhase',
    '            float sr = float (processor.frequency);\n\n'
    '            hostSrcS = hostSrc;   // VST3-IN\n            hostRetS = hostRet;   // VST3-IN\n'
    '            hostVoice = -1;\n            for (int hv = 0; hv < 8; ++hv)\n                if (voices.at (hv).active) { hostVoice = hv; break; }\n\n            flfPhase')
rep('                    if (ty != 0 && ty != 4 && uniCnt', '                    else if (ty == 13)   // VST3-HOST: hosted instrument, carried by the lowest active voice\n                    {\n                        if (i == hostVoice)\n                        {\n                            sL = hostSrcS[0];\n                            sR = hostSrcS[1];\n                        }\n                        stereo = true;\n                    }\n\n                    if (ty != 0 && ty != 4 && ty != 13 && uniCnt')
rep('            out <- float<2> (outL, outR);\n',
    '            out <- float<2> (outL, outR);\n'
    '            hostSend <- hostSendAcc;   // VST3-OUT\n            hostSendAcc = float<2> (0.0f);\n            hostDryPos = (hostDryPos + 1) & 63;\n')
open(P, 'w').write(src)
print('ok')
