#!/usr/bin/env python3
"""Decodes the LPC word banks of the Plaits speech engine at build time (same bit stream decoder as
LPCSpeechSynthWordBank::LoadNextWord) and writes luts/lpc_data.part (frames, word boundaries, phoneme frames)."""
import os, re
SRC = os.environ.get("PLAITS_SRC", "/tmp/claude-0/-home-claude/c011a536-b544-58c8-a399-01d9f993fa60/scratchpad/eurorack")
HERE = os.path.dirname(os.path.abspath(__file__))
ctl = open(SRC + "/plaits/dsp/speech/lpc_speech_synth_controller.cc").read()
words = open(SRC + "/plaits/dsp/speech/lpc_speech_synth_words.cc").read()
phon = open(SRC + "/plaits/dsp/speech/lpc_speech_synth_phonemes.cc").read()

def nums(body):
    body = re.sub(r"//[^\n]*", "", body)
    return [int(x, 0) for x in re.findall(r"-?0x[0-9a-fA-F]+|-?\d+", body)]

def lut(name):
    m = re.search(name + r"\[\d+\]\s*=\s*\{(.*?)\};", ctl, re.S)
    return nums(m.group(1))

L = {n: lut(n) for n in ["energy_lut_", "period_lut_", "k0_lut_", "k1_lut_", "k2_lut_", "k3_lut_", "k4_lut_", "k5_lut_", "k6_lut_", "k7_lut_", "k8_lut_", "k9_lut_"]}

def reverse(b):
    b = ((b >> 4) | (b << 4)) & 0xff
    b = ((b & 0xcc) >> 2) | ((b & 0x33) << 2)
    b = ((b & 0xaa) >> 1) | ((b & 0x55) << 1)
    return b

class Bits:
    def __init__(self, data, p): self.d, self.p, self.avail, self.bits = data, p, 0, 0
    def get(self, n):
        shift = n
        if n > self.avail:
            self.bits = (self.bits << self.avail) & 0xffff
            shift -= self.avail
            self.bits |= reverse(self.d[self.p]); self.p += 1
            self.avail += 8
        self.bits = (self.bits << shift) & 0xffff
        r = (self.bits >> 8) & 0xff
        self.bits &= 0xff
        self.avail -= n
        return r
    def flush(self):
        while self.avail: self.get(1)

def bank_bytes(i):
    m = re.search(r"bank_%d\[\]\s*=\s*\{(.*?)\};" % i, words, re.S)
    return nums(m.group(1))

frames_all, bank_base, bank_nf, bank_nw, bounds = [], [], [], [], []
for b in range(5):
    data = bank_bytes(b)
    pos, frames, wb = 0, [], []
    f = [0] * 12   # energy, period, k0..k9
    while pos < len(data):
        wb.append(len(frames))
        bs = Bits(data, pos)
        f = [0] * 12
        while True:
            e = bs.get(4)
            if e == 0: f[0] = 0
            elif e == 0xf:
                bs.flush(); break
            else:
                f[0] = L["energy_lut_"][e]
                rep = bs.get(1)
                f[1] = L["period_lut_"][bs.get(6)]
                if not rep:
                    f[2] = L["k0_lut_"][bs.get(5)]; f[3] = L["k1_lut_"][bs.get(5)]
                    f[4] = L["k2_lut_"][bs.get(4)]; f[5] = L["k3_lut_"][bs.get(4)]
                    if f[1]:
                        f[6] = L["k4_lut_"][bs.get(4)]; f[7] = L["k5_lut_"][bs.get(4)]; f[8] = L["k6_lut_"][bs.get(4)]
                        f[9] = L["k7_lut_"][bs.get(3)]; f[10] = L["k8_lut_"][bs.get(3)]; f[11] = L["k9_lut_"][bs.get(3)]
            frames.append(list(f))
        pos = bs.p
    wb.append(len(frames))
    assert len(frames) <= 1024 and len(wb) <= 33
    bank_base.append(len(frames_all)); bank_nf.append(len(frames)); bank_nw.append(len(wb) - 1)
    frames_all += frames
    bounds += wb + [0] * (33 - len(wb))

m = re.search(r"phonemes_\[kLPCSpeechSynthNumPhonemes\]\s*=\s*\{(.*)\};", phon, re.S)
ph = nums(m.group(1))
assert len(ph) == 180, len(ph)

nv = open(SRC + "/plaits/dsp/speech/naive_speech_synth.cc").read()
m = re.search(r"phonemes_\[\]\[kNaiveSpeechNumRegisters\]\s*=\s*\{(.*?)\n\};", nv, re.S)
naive = nums(m.group(1))
assert len(naive) == 250, len(naive)
sv = open(SRC + "/plaits/dsp/speech/sam_speech_synth.cc").read()
m = re.search(r"phonemes_\[\]\s*=\s*\{(.*?)\n\};", sv, re.S)
sam = nums(re.sub(r"//[^\n]*", "", m.group(1)))
assert len(sam) == 18 * 6, len(sam)

def arr(name, ty, vals, per=12):
    s = "    const %s[%d] %s =\n    (\n" % (ty, len(vals), name)
    s += ",\n".join("        " + ", ".join(str(v) for v in vals[i:i + per]) for i in range(0, len(vals), per))
    return s + "\n    );\n"

out = arr("lpcFrames", "int", [v for f in frames_all for v in f])
out += arr("lpcBankBase", "int", bank_base) + arr("lpcBankNumFrames", "int", bank_nf) + arr("lpcBankNumWords", "int", bank_nw)
out += arr("spNaivePhonemes", "int", naive, 10) + arr("spSamPhonemes", "int", sam, 6)
out += arr("lpcWordBounds", "int", bounds, 33) + arr("lpcPhonemes", "int", ph)
os.makedirs(HERE + "/luts", exist_ok=True)
open(HERE + "/luts/lpc_data.part", "w").write(out)
print("frames", bank_nf, "words", bank_nw)
