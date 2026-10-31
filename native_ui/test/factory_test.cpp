// Factory wavetables: the C++ generator must match tools/wavetables/build_factory.py (wavetables/Factory/*.wav) and the installer must run once.
//   g++ ... native_ui/NjoFactory.cpp native_ui/test/factory_test.cpp <juce objects> && ./a.out wavetables/Factory
#include "../NjoFactory.h"
#include <juce_audio_formats/juce_audio_formats.h>
#include <cstdio>

static int fails = 0;
#define CHECK(c) do { if (! (c)) { std::printf ("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)

int main (int argc, char** argv)
{
    juce::File ref (argc > 1 ? argv[1] : "wavetables/Factory");
    auto tables = njo::makeFactoryWavetables();
    CHECK (tables.size() == 14);
    juce::AudioFormatManager fm; fm.registerBasicFormats();
    for (auto& t : tables)
    {
        std::unique_ptr<juce::AudioFormatReader> r (fm.createReaderFor (ref.getChildFile (t.name + ".wav")));
        CHECK (r != nullptr);
        if (! r) continue;
        CHECK ((size_t) r->lengthInSamples == t.samples.size());
        CHECK (t.samples.size() % 2048 == 0 && t.samples.size() / 2048 <= 128);
        juce::AudioBuffer<float> b (1, (int) r->lengthInSamples);
        r->read (&b, 0, (int) r->lengthInSamples, 0, true, false);
        double worst = 0;
        for (size_t i = 0; i < t.samples.size(); ++i) worst = std::max (worst, (double) std::abs (b.getSample (0, (int) i) - t.samples[i]));
        std::printf ("%-18s frames %3d  max diff vs python %.6f\n", t.name.toRawUTF8(), (int) (t.samples.size() / 2048), worst);
        CHECK (worst < 4.0 / 32768);   // 16 bit rounding
    }

    auto root = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("njo_factory_test_" + juce::String (juce::Random::getSystemRandom().nextInt()));
    CHECK (njo::installFactoryWavetables (root) == 14);
    auto dir = root.getChildFile ("Wavetables/Factory");
    CHECK (dir.getChildFile ("PWM.wav").existsAsFile() && dir.getChildFile ("Vowels.wav").getSize() == 33 * 2048 * 2 + 44);
    dir.getChildFile ("PWM.wav").deleteFile();
    CHECK (njo::installFactoryWavetables (root) == 0 && ! dir.getChildFile ("PWM.wav").existsAsFile());   // a deleted file stays deleted
    root.deleteRecursively();
    std::printf (fails ? "FAILED\n" : "ALL OK\n");
    return fails ? 1 : 0;
}
