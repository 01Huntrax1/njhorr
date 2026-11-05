// VST3 host of the Njohrr synth plugin (macro NJOHRR_VST3_HOST): one hosted instrument (OSC source "VST3") and one hosted effect (FX type "VST3").
// The wrapper (cmaj_JUCEPlugin.h) renders in chunks of kChunk samples: the instrument is rendered first and enters the DSP as the stream hostSrc, the
// DSP's hostSend goes through the effect and comes back one chunk later as hostRet (kChunk samples of latency + the plugin's own).
// Needs JUCE_PLUGINHOST_VST3=1. Everything the UI needs is in native_ui/NjoVst3Iface.h.
#pragma once
#include <juce_audio_processors/juce_audio_processors.h>
#include "../../../native_ui/NjoVst3Iface.h"

namespace njo
{
    class Vst3Host : public Vst3Control, private juce::Thread
    {
    public:
        static constexpr int kChunk = 64;

        Vst3Host() : juce::Thread ("Njohrr VST3 scan")
        {
            formats.addFormat (new juce::VST3PluginFormat());
            loadKnownCache();
            for (auto& s : slots) { s.ring.assign ((size_t) kRing * 2, 0.0f); s.primeRing(); }
        }

        ~Vst3Host() override
        {
            *aliveFlag = false;
            stopThread (4000);
            for (auto& s : slots) { s.window.reset(); const juce::SpinLock::ScopedLockType sl (s.lock); s.inst.reset(); }
        }

        // ================================================================== audio thread
        void prepare (double sampleRate)
        {
            rate = sampleRate;
            for (int i = 0; i < 2; ++i)
            {
                const juce::SpinLock::ScopedLockType sl (slots[i].lock);
                if (slots[i].inst) slots[i].inst->prepareToPlay (rate, kChunk);
                slots[i].needPrime = true;
            }
        }

        // renders the hosted instrument for n <= kChunk frames; false = nothing loaded (the buffers are cleared)
        bool renderInstrument (juce::MidiBuffer& midi, float* l, float* r, int n)
        {
            auto& s = slots[Instrument];
            juce::FloatVectorOperations::clear (l, n); juce::FloatVectorOperations::clear (r, n);
            const juce::SpinLock::ScopedTryLockType sl (s.lock);
            if (! sl.isLocked() || ! s.inst) return false;
            auto& ch = s.scratch;
            const int nc = juce::jmax (2, s.inst->getTotalNumOutputChannels(), s.inst->getTotalNumInputChannels());
            ch.setSize (nc, kChunk, false, false, true); ch.clear();
            juce::AudioBuffer<float> view (ch.getArrayOfWritePointers(), nc, n);
            s.inst->processBlock (view, midi);
            const int outs = s.inst->getTotalNumOutputChannels();
            juce::FloatVectorOperations::copy (l, ch.getReadPointer (0), n);
            juce::FloatVectorOperations::copy (r, ch.getReadPointer (outs > 1 ? 1 : 0), n);
            return true;
        }

        // the effect, part 1 (before the DSP runs): the answer to what was sent kChunk samples ago
        void fetchReturn (float* rl, float* rr, int n)
        {
            auto& s = slots[Effect];
            if (s.needPrime.exchange (false)) s.primeRing();
            for (int i = 0; i < n; ++i)
            {
                rl[i] = s.ring[(size_t) ((s.rd + i) % kRing) * 2];
                rr[i] = s.ring[(size_t) ((s.rd + i) % kRing) * 2 + 1];
            }
            s.rd = (s.rd + n) % kRing;
        }

        // part 2 (after the DSP): this chunk's send goes through the plugin into the ring (no plugin loaded: it comes back unchanged, a bypass)
        void pushSend (const float* sl, const float* sr, int n)
        {
            auto& s = slots[Effect];
            float tl[kChunk], tr[kChunk];
            juce::FloatVectorOperations::copy (tl, sl, n); juce::FloatVectorOperations::copy (tr, sr, n);
            {
                const juce::SpinLock::ScopedTryLockType lk (s.lock);
                if (! lk.isLocked()) { juce::FloatVectorOperations::clear (tl, n); juce::FloatVectorOperations::clear (tr, n); }   // being loaded / unloaded
                else if (s.inst)
                {
                    auto& ch = s.scratch;
                    const int nc = juce::jmax (2, s.inst->getTotalNumOutputChannels(), s.inst->getTotalNumInputChannels());
                    ch.setSize (nc, kChunk, false, false, true); ch.clear();
                    juce::FloatVectorOperations::copy (ch.getWritePointer (0), tl, n);
                    juce::FloatVectorOperations::copy (ch.getWritePointer (1), tr, n);
                    juce::AudioBuffer<float> view (ch.getArrayOfWritePointers(), nc, n);
                    juce::MidiBuffer none;
                    s.inst->processBlock (view, none);
                    const int outs = s.inst->getTotalNumOutputChannels();
                    juce::FloatVectorOperations::copy (tl, ch.getReadPointer (0), n);
                    juce::FloatVectorOperations::copy (tr, ch.getReadPointer (outs > 1 ? 1 : 0), n);
                }
            }
            for (int i = 0; i < n; ++i)
            {
                s.ring[(size_t) ((s.wr + i) % kRing) * 2]     = tl[i];
                s.ring[(size_t) ((s.wr + i) % kRing) * 2 + 1] = tr[i];
            }
            s.wr = (s.wr + n) % kRing;
        }

        // ================================================================== Vst3Control (message thread)
        juce::String name (int slot) const override { return slots[slot].name; }
        juce::String status (int slot) const override { return slots[slot].status; }
        juce::StringArray known (int slot) override
        {
            juce::StringArray out; rows[slot].clear();
            for (auto& d : list.getTypes())
                if (d.pluginFormatName == "VST3" && d.isInstrument == (slot == Instrument)) { out.add (d.name + (d.manufacturerName.isNotEmpty() ? "  (" + d.manufacturerName + ")" : juce::String())); rows[slot].push_back (d); }
            return out;
        }
        bool scanning() const override { return isThreadRunning(); }
        void rescan() override { if (! isThreadRunning()) startThread(); }
        void loadKnown (int slot, int index) override
        {
            if (index >= 0 && index < (int) rows[slot].size()) load (slot, rows[slot][(size_t) index], {});
        }
        void loadFile (int slot, const juce::File& f) override
        {
            juce::OwnedArray<juce::PluginDescription> found;
            if (auto* fmt = formats.getFormat (0)) fmt->findAllTypesForFile (found, f.getFullPathName());
            if (found.isEmpty()) { setStatus (slot, "Not a VST3 plugin: " + f.getFileName()); return; }
            juce::PluginDescription* pick = found[0];
            for (auto* d : found) if (d->isInstrument == (slot == Instrument)) { pick = d; break; }
            if (pick->isInstrument != (slot == Instrument)) { setStatus (slot, juce::String (slot == Instrument ? "This is an effect, not an instrument: " : "This is an instrument, not an effect: ") + pick->name); return; }
            load (slot, *pick, {});
        }
        void unload (int slot) override
        {
            auto& s = slots[slot];
            s.window.reset();
            { const juce::SpinLock::ScopedLockType sl (s.lock); s.inst.reset(); s.needPrime = true; }
            s.name = {}; s.status = {}; s.desc = {}; s.state = {};
            changed();
        }
        bool hasEditor (int slot) const override { return slots[slot].inst != nullptr && slots[slot].inst->hasEditor(); }
        void openEditor (int slot) override
        {
            auto& s = slots[slot];
            if (! s.inst) return;
            if (s.window) { s.window->toFront (true); return; }
            if (auto* ed = s.inst->createEditorIfNeeded())
            {
                s.window = std::make_unique<Window> (s.name, ed, [this, slot] { slots[slot].window.reset(); });
            }
        }
        int latencySamples (int slot) const override { return kChunk * (slot == Effect ? 1 : 0) + (slots[slot].inst ? slots[slot].inst->getLatencySamples() : 0); }

        // ================================================================== project state
        // one child per slot: the plugin description and its state (base64)
        juce::ValueTree saveState()
        {
            juce::ValueTree t ("NJV3");
            for (int i = 0; i < 2; ++i)
            {
                auto& s = slots[i];
                if (! s.inst) continue;
                juce::MemoryBlock mb; s.inst->getStateInformation (mb);
                juce::ValueTree c ("SLOT");
                c.setProperty ("slot", i, nullptr);
                c.setProperty ("desc", s.desc.createXml()->toString (juce::XmlElement::TextFormat().singleLine()), nullptr);
                c.setProperty ("state", mb.toBase64Encoding(), nullptr);
                t.appendChild (c, nullptr);
            }
            return t;
        }
        void restoreState (const juce::ValueTree& t)
        {
            for (int i = 0; i < 2; ++i) if (! t.getChildWithProperty ("slot", i).isValid()) { if (slots[i].inst) unload (i); }
            for (auto c : t)
            {
                const int i = (int) c.getProperty ("slot", -1);
                if (i < 0 || i > 1) continue;
                juce::PluginDescription d;
                if (auto xml = juce::XmlDocument::parse (c.getProperty ("desc").toString())) d.loadFromXml (*xml); else continue;
                juce::MemoryBlock mb; mb.fromBase64Encoding (c.getProperty ("state").toString());
                if (slots[i].inst && slots[i].desc.uniqueId == d.uniqueId && slots[i].desc.fileOrIdentifier == d.fileOrIdentifier)
                {
                    if (mb.getSize() > 0) slots[i].inst->setStateInformation (mb.getData(), (int) mb.getSize());
                    continue;
                }
                load (i, d, mb);
            }
        }

    private:
        static constexpr int kRing = 4096;

        struct Window : juce::DocumentWindow
        {
            Window (const juce::String& n, juce::AudioProcessorEditor* ed, std::function<void()> onClose)
                : juce::DocumentWindow (n, juce::Colours::black, juce::DocumentWindow::closeButton), closeFn (std::move (onClose))
            {
                setUsingNativeTitleBar (true);
                setContentOwned (ed, true);
                setResizable (ed->isResizable(), false);
                centreWithSize (getWidth(), getHeight());
                setVisible (true);
                toFront (true);
            }
            void closeButtonPressed() override { auto f = closeFn; juce::MessageManager::callAsync (f); }
            std::function<void()> closeFn;
        };

        struct Slot
        {
            std::unique_ptr<juce::AudioPluginInstance> inst;
            juce::PluginDescription desc; juce::String name, status; juce::MemoryBlock state;
            juce::SpinLock lock; juce::AudioBuffer<float> scratch { 2, kChunk };
            std::unique_ptr<Window> window;
            std::vector<float> ring; int rd = 0, wr = 0; std::atomic<bool> needPrime { false };   // ring: audio thread only; a reset is requested through needPrime
            void primeRing() { std::fill (ring.begin(), ring.end(), 0.0f); rd = 0; wr = kChunk; }   // kChunk zero frames of delay
        };

        void changed() { if (onChanged) onChanged(); }
        void setStatus (int slot, const juce::String& s) { slots[slot].status = s; changed(); }

        void load (int slot, const juce::PluginDescription& d, const juce::MemoryBlock& state)
        {
            slots[slot].status = "Loading " + d.name + " ...";
            changed();
            auto alive = aliveFlag;
            formats.createPluginInstanceAsync (d, rate, kChunk, [this, alive, slot, d, state] (std::unique_ptr<juce::AudioPluginInstance> p, const juce::String& err)
            {
                if (! *alive) return;
                auto& s = slots[slot];
                if (! p) { s.status = err.isNotEmpty() ? err : "Could not load " + d.name; changed(); return; }
                // buses: an instrument has a stereo output only, an effect a stereo input and output
                juce::AudioProcessor::BusesLayout lay;
                const auto st = juce::AudioChannelSet::stereo();
                if (slot == Effect) lay.inputBuses.add (st);
                lay.outputBuses.add (st);
                if (! p->setBusesLayout (lay))
                {
                    juce::AudioProcessor::BusesLayout l2 = p->getBusesLayout();   // keep what the plugin accepts (mono, multi out ...)
                    p->setBusesLayout (l2);
                }
                p->setPlayConfigDetails (p->getTotalNumInputChannels(), p->getTotalNumOutputChannels(), rate, kChunk);
                p->prepareToPlay (rate, kChunk);
                if (state.getSize() > 0) p->setStateInformation (state.getData(), (int) state.getSize());
                s.window.reset();
                {
                    const juce::SpinLock::ScopedLockType sl (s.lock);
                    s.inst = std::move (p); s.desc = d; s.needPrime = true;
                }
                s.name = d.name; s.status = {};
                changed();
            });
        }

        // the known plugins are kept between sessions
        juce::File cacheFile() const { return juce::File::getSpecialLocation (juce::File::userApplicationDataDirectory).getChildFile ("Njohrr").getChildFile ("vst3_known.xml"); }
        void loadKnownCache() { if (auto x = juce::XmlDocument::parse (cacheFile())) list.recreateFromXml (*x); }
        void run() override
        {
            auto* fmt = formats.getFormat (0);
            if (fmt == nullptr) return;
            auto dead = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("njohrr_vst3_scan_dead.txt");
            juce::PluginDirectoryScanner scanner (list, *fmt, fmt->getDefaultLocationsToSearch(), true, dead, false);
            juce::String n;
            while (! threadShouldExit() && scanner.scanNextFile (true, n)) {}
            if (auto x = list.createXml()) { cacheFile().getParentDirectory().createDirectory(); x->writeTo (cacheFile()); }
            juce::MessageManager::callAsync ([this] { changed(); });
        }

        juce::AudioPluginFormatManager formats;
        juce::KnownPluginList list;
        std::array<Slot, 2> slots;
        std::vector<juce::PluginDescription> rows[2];
        double rate = 44100.0;
        std::shared_ptr<bool> aliveFlag = std::make_shared<bool> (true);
    };
}
