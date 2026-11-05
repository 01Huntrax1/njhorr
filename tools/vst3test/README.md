Runtime test of the VST3 host (include/cmajor/helpers/NjoVst3Host.h) with two tiny plugins: TestGain (effect, gain 0.5) and TestSine (instrument).

    cmake -S tools/vst3test -B /tmp/vsttest -DJUCE_PATH=/path/to/JUCE -DCMAKE_BUILD_TYPE=Release
    cmake --build /tmp/vsttest -j4
    mkdir /tmp/vsttest/plugins && ln -s /tmp/vsttest/TestGain_artefacts/Release/VST3/TestGain.vst3 /tmp/vsttest/TestSine_artefacts/Release/VST3/TestSine.vst3 /tmp/vsttest/plugins/
    /tmp/vsttest/HostTest_artefacts/Release/HostTest /tmp/vsttest/plugins

Checks: loading (an instrument is refused as an effect and the other way round), 64-sample return latency and the effect's output, the instrument's MIDI and audio, saving / restoring the state, bypass without a plugin.
