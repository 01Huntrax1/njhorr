// Parser test for the SoundFont source: build with native_ui/test/sf2build.sh, run:  sf2_test <file from tools/osc/mk_sf2.py>
#include "../NjoSf2.h"
#include <cstdio>
#include <cmath>
using namespace njo::sf2;
static int fails = 0;
#define CHECK(c, msg) do { bool ok_ = (c); std::printf("%s  %s\n", ok_ ? "ok  " : "FAIL", msg); if (! ok_) ++fails; } while (0)
int main (int argc, char** argv)
{
    juce::String err; File sf;
    CHECK (argc > 1 && sf.open (juce::File (argv[1]), err), "opens the file"); if (err.isNotEmpty()) std::printf ("  error: %s\n", err.toRawUTF8());
    CHECK (sf.presets().size() == 2, "two presets");
    if (sf.presets().size() != 2) return 1;
    CHECK (sf.presets()[0].name == "PIANO" && sf.presets()[1].name == "OCTAVE UP", "preset names");
    CHECK (sf.presets()[1].program == 1, "preset program number");
    CHECK (sf.defaultPreset() == 0, "default preset is bank 0 program 0");
    Built b;
    CHECK (sf.build (0, b, err), "builds preset 0");
    CHECK (b.data[0] == 12345.0f && (int) b.data[1] == 3, "preamble: magic and three zones");
    CHECK ((int) b.data.size() >= kSfHdr + 5000 && b.samples == 5000, "audio: looped sine, saw, unlooped sine (regions differ by loop points)");
    auto Z = [&] (int z, ZoneField f) { return b.data[(size_t) (8 + z * kSfZf + f)]; };
    int lo = -1, hiSoft = -1, hiLoud = -1;
    for (int z = 0; z < 3; ++z)
    {
        if (Z (z, KeyHi) == 59) lo = z;
        else if (Z (z, VelHi) == 63) hiSoft = z; else hiLoud = z;
    }
    CHECK (lo >= 0 && hiSoft >= 0 && hiLoud >= 0, "key / velocity ranges found");
    if (lo < 0 || hiSoft < 0 || hiLoud < 0) return 1;
    CHECK (Z (lo, KeyLo) == 0 && Z (lo, LoopMode) == 1 && Z (lo, Root) == 69, "low zone: looped, root key 69 (override)");
    CHECK (Z (lo, Len) == 2000 && Z (lo, LoopS) == 500 && Z (lo, LoopE) == 1500 && Z (lo, SampleRate) == 22050, "low zone: length, loop points, rate");
    CHECK (Z (hiSoft, Root) == 60 && Z (hiSoft, LoopMode) == 0 && Z (hiSoft, SampleRate) == 44100, "soft zone: saw, root from the sample header, not looped");
    CHECK (std::abs (Z (hiLoud, TuneCents) - 200.0f) < 1 && std::abs (Z (hiLoud, AttenCb) - 100.0f) < 1 && Z (hiLoud, Pan) > 0.4f, "loud zone: +2 semitones, 100 cB, pan right");
    CHECK (std::abs (Z (lo, ReleaseMs) - 1000.0f * std::pow (2.0f, -3000.0f / 1200.0f)) < 2, "global zone release applies to every zone");
    CHECK (Z (hiLoud, Start) != Z (lo, Start) && Z (hiLoud, LoopMode) == 0 && b.data[(size_t) kSfHdr + (size_t) Z (hiLoud, Start) + 7] == b.data[(size_t) kSfHdr + (size_t) Z (lo, Start) + 7], "unlooped copy of the sine carries the same audio");
    Built b2;
    CHECK (sf.build (1, b2, err), "builds preset 1");
    CHECK (std::abs (b2.data[(size_t) (8 + 0 * kSfZf + TuneCents)] - b.data[(size_t) (8 + 0 * kSfZf + TuneCents)] - 1200.0f) < 1, "preset-level generators add (+12 semitones)");
    CHECK (! sf.build (7, b2, err), "rejects a preset number out of range");
    File bad; juce::File tmp = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("njo_bad.sf2");
    tmp.replaceWithText ("this is not a soundfont at all");
    CHECK (! bad.open (tmp, err) && err.isNotEmpty(), "a non-SoundFont file is refused with a message");
    tmp.deleteFile();
    std::printf (fails ? "%d FAILED\n" : "all ok\n", fails);
    return fails ? 1 : 0;
}
