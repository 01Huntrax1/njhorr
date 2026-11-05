#include "Vst3Panel.h"
#include "../NjoTheme.h"

namespace njo
{
    using namespace theme;

    struct Vst3Panel::Impl : private juce::Timer
    {
        struct Btn : juce::Component
        {
            juce::String text; std::function<void()> click; bool enabled = true;
            void paint (juce::Graphics& g) override
            {
                paintButton (g, getLocalBounds().toFloat(), false, isMouseOver() && enabled, false, 3.0f);
                g.setColour (enabled ? ink : dim.withAlpha (0.5f)); g.setFont (font (9.0f, true));
                g.drawText (text, getLocalBounds(), juce::Justification::centred);
            }
            void mouseDown (const juce::MouseEvent&) override { if (enabled && click) click(); }
            void mouseEnter (const juce::MouseEvent&) override { repaint(); }
            void mouseExit (const juce::MouseEvent&) override { repaint(); }
        };

        Ctx& ctx; int slot; Vst3Panel& owner;
        Btn load, edit, unload;
        std::shared_ptr<juce::FileChooser> chooser;
        juce::Rectangle<int> nameBox, noteBox;

        Impl (Ctx& c, int s, Vst3Panel& o) : ctx (c), slot (s), owner (o)
        {
            load.text = "LOAD..."; edit.text = "EDIT"; unload.text = "UNLOAD";
            load.click = [this] { showMenu(); };
            edit.click = [this] { if (auto* v = ctl()) v->openEditor (slot); };
            unload.click = [this] { if (auto* v = ctl()) v->unload (slot); };
            for (auto* b : { &load, &edit, &unload }) owner.addAndMakeVisible (*b);
            startTimerHz (4);
        }
        void timerCallback() override { owner.refresh(); }
        Vst3Control* ctl() const { auto* v = ctx.be.vst3(); return v != nullptr && v->isAvailable() ? v : nullptr; }

        void showMenu()
        {
            auto* v = ctl(); if (v == nullptr) return;
            if (v->known (slot).isEmpty() && ! v->scanning()) v->rescan();
            juce::PopupMenu m;
            auto names = v->known (slot);
            if (v->scanning()) m.addItem (-1, "Scanning ...", false);
            for (int i = 0; i < names.size(); ++i) m.addItem (100 + i, names[i]);
            if (names.isEmpty() && ! v->scanning()) m.addItem (-1, "No plugins found", false);
            m.addSeparator();
            m.addItem (1, "Browse for a .vst3 file...");
            m.addItem (2, "Rescan the plugin folders");
            juce::Component::SafePointer<Vst3Panel> safe (&owner);
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (&load), [this, safe] (int r)
            {
                if (safe == nullptr || r <= 0) return;
                auto* v2 = ctl(); if (v2 == nullptr) return;
                if (r == 2) v2->rescan();
                else if (r == 1)
                {
                    chooser = std::make_shared<juce::FileChooser> (slot == 0 ? "Load a VST3 instrument" : "Load a VST3 effect", juce::File(), "*.vst3");
                    chooser->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles | juce::FileBrowserComponent::canSelectDirectories,
                                          [this, safe] (const juce::FileChooser& fc)
                    {
                        if (safe == nullptr) return;
                        auto f = fc.getResult();
                        if (f != juce::File() && ctl() != nullptr) ctl()->loadFile (slot, f);
                    });
                }
                else v2->loadKnown (slot, r - 100);
            });
        }
    };

    Vst3Panel::Vst3Panel (Ctx& c, int slot) : impl (new Impl (c, slot, *this)) {}
    Vst3Panel::~Vst3Panel() = default;

    void Vst3Panel::refresh()
    {
        auto* v = impl->ctl();
        impl->edit.enabled = v != nullptr && v->hasEditor (impl->slot);
        impl->unload.enabled = v != nullptr && v->name (impl->slot).isNotEmpty();
        impl->load.enabled = v != nullptr;
        for (auto* b : { &impl->load, &impl->edit, &impl->unload }) b->repaint();
        repaint();
    }

    void Vst3Panel::resized()
    {
        auto b = getLocalBounds();
        b.removeFromTop (14);
        impl->nameBox = b.removeFromTop (34); b.removeFromTop (6);
        auto row = b.removeFromTop (26);
        const int w = (row.getWidth() - 12) / 3;
        impl->load.setBounds (row.removeFromLeft (w)); row.removeFromLeft (6);
        impl->edit.setBounds (row.removeFromLeft (w)); row.removeFromLeft (6);
        impl->unload.setBounds (row);
        b.removeFromTop (8);
        impl->noteBox = b;
        refresh();
    }

    void Vst3Panel::paint (juce::Graphics& g)
    {
        auto& I = *impl;
        auto* v = I.ctl();
        const bool inst = I.slot == 0;
        g.setColour (orange); g.setFont (font (8.0f, true).withExtraKerningFactor (0.2f));
        g.drawText (inst ? "VST3 INSTRUMENT" : "VST3 EFFECT", 0, 0, getWidth(), 12, juce::Justification::centredLeft);

        g.setColour (juce::Colour (0xff0b0405)); g.fillRoundedRectangle (I.nameBox.toFloat(), 2.0f);
        g.setColour (line); g.drawRoundedRectangle (I.nameBox.toFloat().reduced (0.5f), 2.0f, 1.0f);
        juce::String nm = v != nullptr ? v->name (I.slot) : juce::String(), st = v != nullptr ? v->status (I.slot) : juce::String();
        auto tb = I.nameBox.reduced (8, 3);
        g.setFont (font (11.0f, true));
        g.setColour (nm.isNotEmpty() ? ink : dim);
        g.drawText (nm.isNotEmpty() ? nm : juce::String (v != nullptr ? "No plugin loaded" : "Not available here"), tb.removeFromTop (16), juce::Justification::centredLeft, true);
        g.setFont (font (8.5f)); g.setColour (st.isNotEmpty() ? orange : dim);
        juce::String sub = st;
        if (sub.isEmpty() && nm.isNotEmpty() && v != nullptr && ! inst) sub = "latency " + juce::String (v->latencySamples (I.slot)) + " samples";
        g.drawText (sub, tb, juce::Justification::centredLeft, true);

        g.setColour (dim); g.setFont (font (8.5f));
        juce::String note = v == nullptr ? "The VST3 host is part of the Njohrr synth plugin."
            : inst ? "Plays on every MIDI note. Its sound goes through this slot's filter, distortion and pan; the amp envelope shapes it (set a long Release for tails)."
                   : "Send and return through the plugin. The effect adds 64 samples of latency (dry and wet stay aligned). One effect plugin for all VST3 slots; Mix blends dry and wet.";
        g.drawFittedText (note, I.noteBox, juce::Justification::topLeft, 5);
    }
}
