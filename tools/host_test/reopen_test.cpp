// Close / open test of the real plugin: a sustained note must keep sounding while the editor window is destroyed and created again.
#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_audio_formats/juce_audio_formats.h>
#include "choc/containers/choc_Value.h"
using namespace juce;
static AudioPluginInstance* gInst = nullptr;
static AudioBuffer<float> gBuf (2, 512);
static MidiBuffer gMidi;
static float block() { gInst->processBlock (gBuf, gMidi); gMidi.clear(); return gBuf.getRMSLevel (0, 0, 512); }
static void run (int ms, float* minRms = nullptr, float* maxRms = nullptr)
{
    auto end = Time::getMillisecondCounter() + (uint32) ms;
    while (Time::getMillisecondCounter() < end)
    {
        MessageManager::getInstance()->runDispatchLoopUntil (1);
        float r = block();
        if (minRms) *minRms = jmin (*minRms, r);
        if (maxRms) *maxRms = jmax (*maxRms, r);
        Thread::sleep (8);
    }
}

// the VST3 state is <VST3PluginState><IComponent>size.base64 of the plugin's ValueTree stream</IComponent>...
static MemoryBlock addStoredValue (const MemoryBlock& vst3State, const String& key, const var& value)
{
    auto xml = AudioProcessor::getXmlFromBinary (vst3State.getData(), (int) vst3State.getSize());
    if (! xml) { std::cout << "state is not xml" << std::endl; return vst3State; }
    auto* comp = xml->getChildByName ("IComponent");
    MemoryBlock inner; inner.fromBase64Encoding (comp->getAllSubText().trim());
    auto tree = ValueTree::readFromData (inner.getData(), inner.getSize());
    std::cout << "inner " << inner.getSize() << " tree " << tree.getType().toString() << " children " << tree.getNumChildren() << std::endl;
    auto st = tree.getChildWithName ("STATE");
    if (! st.isValid()) { st = ValueTree ("STATE"); tree.addChild (st, 0, nullptr); }
    auto* dyn = value.getDynamicObject();
    auto cv = choc::value::createObject ("", "name", choc::value::createString (dyn->getProperty ("name").toString().toStdString()),
                                         "total", choc::value::createInt32 ((int) dyn->getProperty ("total")),
                                         "pcm16", choc::value::createString (dyn->getProperty ("pcm16").toString().toStdString()));
    auto ser = cv.serialise();
    ValueTree v ("VALUE"); v.setProperty ("key", key, nullptr); v.setProperty ("value", var (ser.data.data(), ser.data.size()), nullptr);
    st.appendChild (v, nullptr);
    MemoryOutputStream os; tree.writeToStream (os);
    comp->deleteAllTextElements(); comp->addTextElement (MemoryBlock (os.getData(), os.getDataSize()).toBase64Encoding());
    MemoryBlock out; AudioProcessor::copyXmlToBinary (*xml, out);
    return out;
}

int main (int argc, char** argv)
{
    ScopedJuceInitialiser_GUI init;
    AudioPluginFormatManager fm; fm.addFormat (new VST3PluginFormat());
    OwnedArray<PluginDescription> descs; VST3PluginFormat f; f.findAllTypesForFile (descs, argv[1]);
    String err; auto inst = fm.createPluginInstance (*descs[0], 48000, 512, err);
    if (! inst) { std::cout << "ERR " << err << std::endl; return 2; }
    gInst = inst.get();
    inst->prepareToPlay (48000, 512);
    run (3000);
    int bad = 0; float mn = 1e9f, mx = 0;
    // project state with a stored sine wavetable in OSC 1; the plugin must play it without any editor
    {   // baseline: a Plaits slot needs no sample data, so it must sound when the audio path works
        for (auto* p : inst->getParameters()) if (p->getName (100) == "OSC 1 Source") p->setValue (1.0f);
        gMidi.addEvent (MidiMessage::noteOn (1, 64, (uint8) 100), 0);
        float a = 1e9f, b = 0; run (1000, &a, &b);
        std::cout << "baseline (Plaits slot): rms max " << b << std::endl;
        gMidi.addEvent (MidiMessage::allNotesOff (1), 0); run (500);
        for (auto* p : inst->getParameters()) if (p->getName (100) == "OSC 1 Source") p->setValue (0.0f);
    }
    MemoryBlock mb0; inst->getStateInformation (mb0);
    MemoryBlock pcm (2048 * 2);
    for (int i = 0; i < 2048; ++i) { int v = (int) std::lround (std::sin (i * 6.2831853 / 2048.0) * 0.9 * 32767.0); ((uint8*) pcm.getData())[i * 2] = (uint8) (v & 255); ((uint8*) pcm.getData())[i * 2 + 1] = (uint8) ((v >> 8) & 255); }
    auto* o = new DynamicObject(); o->setProperty ("name", "SINE"); o->setProperty ("total", 2048); o->setProperty ("pcm16", Base64::toBase64 (pcm.getData(), pcm.getSize()));
    auto state = addStoredValue (mb0, "njo.mem.osc0.wt", var (o));
    inst.reset();
    AudioPluginFormatManager fm2; fm2.addFormat (new VST3PluginFormat());
    String err2; auto inst2 = fm2.createPluginInstance (*descs[0], 48000, 512, err2);
    gInst = inst2.get();
    inst2->setStateInformation (state.getData(), (int) state.getSize());
    inst2->prepareToPlay (48000, 512);
    run (4000);
    gMidi.addEvent (MidiMessage::noteOn (1, 60, (uint8) 110), 0);
    mn = 1e9f; mx = 0; run (1200, &mn, &mx);
    std::cout << "project loaded, no editor yet: rms min " << mn << " max " << mx << std::endl;
    if (mx < 0.005f) { std::cout << "FAIL stored sound did not reach the DSP without an editor" << std::endl; ++bad; }
    for (int round = 0; round < 3; ++round)
    {
        auto* ed = inst2->createEditorIfNeeded();
        ed->setVisible (true);
        mn = 1e9f; mx = 0; run (1500, &mn, &mx);
        std::cout << "round " << round << " editor open: rms min " << mn << " max " << mx << std::endl;
        if (mn < 0.002f) { std::cout << "FAIL sound cut while the editor was open" << std::endl; ++bad; }
        delete ed;   // closes the window
        inst2->editorBeingDeleted (nullptr);
        mn = 1e9f; mx = 0; run (600, &mn, &mx);
        std::cout << "round " << round << " closed: rms min " << mn << " max " << mx << std::endl;
        if (mn < 0.002f) { std::cout << "FAIL sound cut after closing" << std::endl; ++bad; }
    }
    inst2.reset();
    std::cout << (bad ? "FAILED" : "ALL OK") << std::endl;
    return bad ? 1 : 0;
}
