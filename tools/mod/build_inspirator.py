#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR-DSP: ports the generative pattern engine "Inspirator" (tools/mod/inspirator_source.cmajor.txt, a stand-alone
Cmajor MIDI processor: Chords / Lead / Bass / Arp / Drums, 9 styles, seeds, bars, swing ...) into the synth as a sequencer.
All names get the prefix ins_, the parameters param1..param128 become 7001..7128, 7000 = Inspirator On.  The engine plays through
voiceNoteOn / voiceNoteOff; the keyboard transposes it (MIDI In: Transpose / Hold) or plays normally (Off); it runs with the host transport
(tempo, time signature and position events) or, while a key is held, free running at the host tempo."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'INSPIRATOR-DSP' in src:
    print('already applied'); sys.exit(0)
ins = open(os.path.join(root, 'tools', 'mod', 'inspirator_source.cmajor.txt')).read().split('\n')
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)

BASE = 7000
# --- parameter declarations (lines 1-143 of the source)
decl = []; specs = []
for ln in ins[:143]:
    m = re.match(r'\s*input event float param(\d+)\s*\[\[(.*)\]\];', ln)
    if not m: continue
    n = int(m.group(1)); a = m.group(2)
    nm = re.search(r'name: "([^"]*)"', a).group(1)
    a2 = a.replace('name: "%s"' % nm, 'name: "Insp %s"' % nm)
    decl.append('    input event float param%d [[ %s, automatable: false ]];' % (BASE + n, a2.strip()))
    g = lambda k: (re.search(r'\b' + k + r':\s*(-?[\d.]+)', a) or [None, None])[1]
    txt = re.search(r'text: "([^"]*)"', a)
    specs.append((BASE + n, nm, float(g('min')), float(g('max')), float(g('init')), txt.group(1).split('|') if txt else None, (re.search(r'unit: "([^"]*)"', a) or [None, ''])[1]))
assert len(decl) == 128
# --- body: state + functions (lines 144-1776), handlers, then own transport / midi / main logic
body = '\n'.join(ins[143:1776])
# drop the UI dump function (patOut) and the position output
body = body.replace('posOut <- float (st);', 'insPos <- st;').replace('patOut <- v;', 'insDump <- v;')
handlers = '\n'.join(ins[1777:1926])
handlers = re.sub(r'event param(\d+)\b', lambda m: 'event param%d' % (BASE + int(m.group(1))), handlers)
pass
# identifiers declared at the top level of the body
names = set()
for ln in body.split('\n'):
    m = re.match(r'^    (?:int|float|float64|bool|void)(?:\[\d+\])? (\w+)\s*(?:\(|=|;)', ln)
    if m: names.add(m.group(1))
names -= {'main'}
def pre(t):
    for nme in sorted(names, key=len, reverse=True):
        t = re.sub(r'\b' + re.escape(nme) + r'\b', 'ins_' + nme, t)
    return t
body = pre(body); handlers = pre(handlers)
# the original's midiIn / transportIn / main replaced by the synth side below
core = '''
    // ---- INSPIRATOR-DSP: glue to the synth ----
    void ins_position (float64 ppq, float64 barStart)
    {
        ins_hostPpq = ppq;
        if (barStart <= ppq + 0.001 && ppq - barStart < 40.0 && ins_barTicks > 0)
        {
            int bst = ins_floorTick (barStart + 0.0026);
            int bi = ins_floorDiv (bst + ins_barTicks / 2, ins_barTicks);
            ins_originOff = bst - bi * ins_barTicks;
        }
    }

    // returns true when the message is consumed (the keyboard transposes the pattern)
    bool ins_midi (std::midi::Message msg)
    {
        if (ins_pInMode == 2)
            return false;

        bool noteOn = msg.isNoteOn() && msg.getVelocity() > 0;
        bool noteOff = msg.isNoteOff() || (msg.isNoteOn() && msg.getVelocity() == 0);

        if (noteOn)
        {
            ins_heldCount += 1;
            if (ins_pMode != 4)
            {
                int tr = ins_posMod (msg.getNoteNumber() - ins_pKey, 12);
                if (tr > 6) tr -= 12;
                ins_transpose = tr;
            }
            return true;
        }

        if (noteOff)
        {
            ins_heldCount = ins_maxi (0, ins_heldCount - 1);
            if (ins_heldCount == 0 && ins_pInMode == 1) ins_allOff();
            return true;
        }

        return false;
    }

    void ins_flush()
    {
        if (ins_qCount > 0)
        {
            int st = ins_qS.at (ins_qHead);
            int nn = ins_qA.at (ins_qHead);
            int vv = ins_qB.at (ins_qHead);
            ins_qHead = (ins_qHead + 1) % 256;
            ins_qCount -= 1;

            if (st == 0x90) voiceNoteOn (nn, float (vv) / 127.0f);
            else            voiceNoteOff (nn);
        }
    }

    // called once per sample from main(): the original loop body without the UI dump
    void ins_frame()
    {
        if (ins_cooldown > 0) ins_cooldown -= 1;
        if (ins_dirty && ins_cooldown == 0)
        {
            ins_regenerate();
            ins_cooldown = 256;
        }

        ins_dumpTimer += 1;
        if (ins_dumpIdx >= 0 && ins_dumpTimer >= 16)
        {
            ins_dumpTimer = 0;
            ins_emitDump();
        }

        ins_redump += 1;
        if (ins_redump > int (processor.frequency * 1.5))
        {
            ins_redump = 0;
            if (ins_dumpIdx < 0) ins_dumpIdx = 0;
        }

        if (insOn < 0.5f)
        {
            if (ins_runState != 0)
            {
                ins_allOff();
                ins_runState = 0;
                ins_lastTick = -1000000;
                ins_lastStep = -1;
                insPos <- -1;
            }
            ins_flush();
            return;
        }

        int want = 0;
        if (ins_transportSeen && ins_transportPlaying) want = 1;
        else if (ins_heldCount > 0 && ins_pInMode != 2) want = 2;

        if (want != ins_runState)
        {
            ins_allOff();
            ins_lastTick = -1000000;
            ins_lastStep = -1;
            if (want == 2)
            {
                ins_freePpq = 0.0;
                ins_originOff = 0;
            }
            if (want == 0) insPos <- -1;
            ins_runState = want;
        }

        if (ins_runState != 0)
        {
            ins_bpm = syncBpmOver > 1.0f ? syncBpmOver : hostBpm;
            float64 ppq = ins_freePpq;
            if (ins_runState == 1) ppq = ins_hostPpq - float64 (ins_pOffsetMs) * float64 (ins_bpm) / 60000.0;
            int t = ins_floorTick (ppq);
            bool emit = (ins_pInMode != 1) || (ins_heldCount > 0);

            if (t != ins_lastTick)
            {
                int d = t - ins_lastTick;
                if (d > 0 && d <= 8)
                {
                    for (int k = ins_lastTick + 1; k <= t; ++k)
                        ins_processTick (k, emit);
                    ins_lastTick = t;
                }
                else if (d > 0 || d < -3)
                {
                    ins_allOff();
                    ins_processTick (t, emit);
                    ins_lastTick = t;
                }
            }

            float64 inc = float64 (ins_bpm) / 60.0 * processor.period;
            if (ins_runState == 1) ins_hostPpq += inc;
            else                   ins_freePpq += inc;
        }

        ins_flush();
    }

    event param7000 (float v) { insOn = v; }

    event timeSigIn (std::timeline::TimeSignature ts)
    {
        int den = ts.denominator;
        if (ts.numerator >= 1 && ts.numerator <= 32 && (den == 2 || den == 4 || den == 8 || den == 16))
        {
            if (ts.numerator != ins_tsNum || den != ins_tsDen)
            {
                ins_tsNum = ts.numerator;
                ins_tsDen = den;
                ins_dirty = true;
            }
        }
    }

    event transportStateIn (std::timeline::TransportState ts)
    {
        ins_transportSeen = true;
        ins_transportPlaying = ts.isPlaying();
    }
'''
# --- insert into the synth
rep('    input event std::timeline::Position positionIn;   // FX-SYNC\n',
    '    input event std::timeline::Position positionIn;   // FX-SYNC\n    input event std::timeline::TimeSignature timeSigIn;   // INSPIRATOR-DSP\n    input event std::timeline::TransportState transportStateIn;\n    output event float insDump;\n    output event int insPos;\n    input event float param7000 [[ name: "Inspirator On", min: 0.0, max: 1.0, init: 0.0, step: 1.0, automatable: false ]];\n' + '\n'.join(decl) + '\n')
rep('    event positionIn (std::timeline::Position p) { fxBeat = p.quarterNote; }\n',
    '    event positionIn (std::timeline::Position p) { fxBeat = p.quarterNote; ins_position (p.quarterNote, p.barStartQuarterNote); }\n')
rep('    float64       fxBeat = 0.0;', '    float         insOn = 0.0f;\n    float64       fxBeat = 0.0;')
# state + functions go before voiceNoteOn's users? Cmajor allows any order inside a processor
rep('    // ---------------- AUDIO ----------------\n    void main()\n', '    // INSPIRATOR-DSP: engine (tools/mod/inspirator_source.cmajor.txt)\n' + body + '\n' + handlers + '\n' + core.replace('insOn', 'insOn') + '\n    // ---------------- AUDIO ----------------\n    void main()\n')
rep('        fxGateInit();\n', '        fxGateInit();\n        ins_setupTables();   // INSPIRATOR-DSP\n')
rep('            arpTick (dt);   // MOD-ARP\n', '            arpTick (dt);   // MOD-ARP\n            ins_frame();    // INSPIRATOR-DSP\n')
rep('''    event midiIn (std::midi::Message msg)
    {
        if (msg.isNoteOn())
        {
            if (arpOn > 0.5f)''','''    event midiIn (std::midi::Message msg)
    {
        if (insOn > 0.5f && ins_midi (msg))   // INSPIRATOR-DSP
            return;

        if (msg.isNoteOn())
        {
            if (arpOn > 0.5f)''')
open(path, 'w').write(src)
# specs for index.js
import json
def short(n):
    for pf in ('Chords ', 'Lead ', 'Bass ', 'Arp ', 'Drums '):
        if n.startswith(pf) and len(n) > len(pf): n = n[len(pf):]
    return n
out = ['    [7000, "Inspirator On", 0, 1, 0, "", "btn", ["Off", "On"], 1, "On", null],']
for (i, nm, lo, hi, ini, txt, unit) in specs:
    kind = 'sel' if txt else 'knb'
    opt = json.dumps(txt) if txt else 'null'
    fm = lambda v: ('%d' % v) if v == int(v) else repr(v)
    out.append('    [%d, %s, %s, %s, %s, %s, "%s", %s, 1, %s, null],' % (i, json.dumps('Insp ' + nm), fm(lo), fm(hi), fm(ini), json.dumps(unit), kind, opt, json.dumps(short(nm))))
js = open(os.path.join(root, 'patch', 'index.js')).read()
anchor = '    [1045, "OSC 1 Pre-Matrix Order"'
assert js.count(anchor) == 1
js = js.replace(anchor, '\n'.join(out) + '\n' + anchor)
open(os.path.join(root, 'patch', 'index.js'), 'w').write(js)
print('ok', len(names), 'names')
