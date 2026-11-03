#!/usr/bin/env python3
"""Writes a small SoundFont 2 file for the parser test (native_ui/test/sf2_test.cpp):  mk_sf2.py out.sf2
Two presets ("PIANO", "OCTAVE UP") of one instrument: low keys play a looped 22.05 kHz sine, high keys a saw (soft) or the sine (loud, +2 semitones), preset 2 adds +12 semitones."""
import math, struct, sys
def chunk(tag, data):
    if len(data) & 1: data += b"\0"
    return tag + struct.pack("<I", len(data)) + data
def lst(kind, *parts): return chunk(b"LIST", kind + b"".join(parts))
def nm(s): return s.encode().ljust(20, b"\0")[:20]
sine = [int(12000 * math.sin(2 * math.pi * i * 440 / 22050)) for i in range(2000)]
saw = [int(9000 * (2 * ((i % 100) / 100.0) - 1)) for i in range(1000)]
smpl = struct.pack("<%dh" % len(sine), *sine) + b"\0" * 92 + struct.pack("<%dh" % len(saw), *saw) + b"\0" * 92
sA, sB = 0, 2000 + 46
shdr = nm("SINE") + struct.pack("<IIIIIBbHH", sA, sA + 2000, sA + 500, sA + 1500, 22050, 69, 0, 0, 1)
shdr += nm("SAW") + struct.pack("<IIIIIBbHH", sB, sB + 1000, sB + 100, sB + 900, 44100, 60, 0, 0, 1)
shdr += nm("EOS") + struct.pack("<IIIIIBbHH", 0, 0, 0, 0, 0, 0, 0, 0, 0)
G = lambda oper, amt: struct.pack("<Hh", oper, amt)
rng = lambda lo, hi: struct.pack("<HBB", 43, lo, hi)
vrng = lambda lo, hi: struct.pack("<HBB", 44, lo, hi)
igen = []; ibag = []
def zone(gens): ibag.append((len(b"".join(igen)) // 4, 0)); igen.append(b"".join(gens))
zone([G(38, -3000)])                                                        # global: release 0.5 s
zone([rng(0, 59), G(54, 1), G(53, 0), G(58, 69)])                           # low: looped sine
zone([rng(60, 127), vrng(0, 63), G(53, 1)])                                 # high soft: saw
zone([rng(60, 127), vrng(64, 127), G(51, 2), G(48, 100), G(17, 250), G(53, 0)])   # high loud: sine +2 semitones, 10 dB... (100 cB), pan right
ibag.append((len(b"".join(igen)) // 4, 0)); igen.append(G(0, 0))
inst = nm("INST") + struct.pack("<H", 0) + nm("EOI") + struct.pack("<H", 4)
pbag = []; pgen = []
def pzone(gens): pbag.append((len(b"".join(pgen)) // 4, 0)); pgen.append(b"".join(gens))
pzone([struct.pack("<Hh", 41, 0)])
pzone([G(51, 12), struct.pack("<Hh", 41, 0)])
pbag.append((len(b"".join(pgen)) // 4, 0)); pgen.append(G(0, 0))
phdr = nm("PIANO") + struct.pack("<HHHIII", 0, 0, 0, 0, 0, 0) + nm("OCTAVE UP") + struct.pack("<HHHIII", 1, 0, 1, 0, 0, 0) + nm("EOP") + struct.pack("<HHHIII", 0, 0, 2, 0, 0, 0)
bag = lambda b: b"".join(struct.pack("<HH", g, m) for g, m in b)
out = b"sfbk" + b"".join([
    lst(b"INFO", chunk(b"ifil", struct.pack("<HH", 2, 1)), chunk(b"isng", b"EMU8000\0"), chunk(b"INAM", b"TEST FONT\0")),
    lst(b"sdta", chunk(b"smpl", smpl)),
    lst(b"pdta", chunk(b"phdr", phdr), chunk(b"pbag", bag(pbag)), chunk(b"pmod", b"\0" * 10), chunk(b"pgen", b"".join(pgen)),
        chunk(b"inst", inst), chunk(b"ibag", bag(ibag)), chunk(b"imod", b"\0" * 10), chunk(b"igen", b"".join(igen)), chunk(b"shdr", shdr))])
open(sys.argv[1], "wb").write(b"RIFF" + struct.pack("<I", len(out)) + out)
