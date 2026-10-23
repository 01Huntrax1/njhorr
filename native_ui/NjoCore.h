// Shared editor context: backend access, per-slot FX types, the modulation matrix model and the status / LCD hooks.
#pragma once
#include "NjoBackend.h"
#include "NjoData.h"
#include "NjoTheme.h"
#include <functional>
#include <memory>

namespace njo
{
    class LfoShapes;
    class FreqShapes;
    struct ModSlot { int s = 0, src = 0, dst = 0; float amt = 0; };

    class Ctx : private Backend::Listener
    {
    public:
        explicit Ctx (Backend& b);
        ~Ctx() override;

        Backend& be;

        float get (int num) const { return be.getParam (num); }
        void  set (int num, float v);                       // user edit (clamped to the spec range)
        void  begin (int num) { be.beginGesture (num); }
        void  end (int num)   { be.endGesture (num); }

        // effect type held by each of the 30 rack slots (for the value text of the P1..P6 knobs)
        const int* fxSlotTypes() const { return fxTypes; }

        // ---- modulation matrix ----
        std::vector<ModSlot> modSlots() const;
        std::vector<ModSlot> modsFor (int dst) const;       // active slots (source > 0) that point at dst
        int  modAssign (int src, int dst, float amt);       // slot index, or -1 when the matrix is full
        void modClear (int slot);
        bool isModTarget (int num) const { return modTarget().count (num) > 0; }

        // ---- listeners (parameter changes after the context updated its own caches) ----
        struct Listener { virtual ~Listener() = default; virtual void paramChanged (int num, float v) = 0; };
        void addListener (Listener* l) { listeners.add (l); }
        void removeListener (Listener* l) { listeners.remove (l); }
        void touchAll();                                    // re-send every parameter to the listeners (after a preset load)

        // ---- feedback to the shell ----
        std::function<void (const juce::String& name, const juce::String& value)> onLcd;
        std::function<void (const juce::String& text)> onStatus;
        void lcd (const juce::String& n, const juce::String& v) { if (onLcd) onLcd (n, v); }
        void status (const juce::String& t) { if (onStatus) onStatus (t); }

        // set by the shell: open the Sound Vault for the given kind (SoundMemory::Kind as int) and oscillator slot
        std::function<void (int kind, int osc)> onOpenVault;

        // the selected LFO / envelope in the editors (shared by the strip and the modulation page)
        int selectedLfo = 0, selectedEnv = 0;

        // drawn LFO shapes (implemented with the modulation editors; created lazily by the first user)
        std::shared_ptr<LfoShapes> lfoShapes;

        // Freq modulators: the selected one and the drawn curves
        int selectedFrq = 0;
        std::shared_ptr<FreqShapes> freqShapes;

    private:
        void paramChanged (int num, float v) override;
        int fxTypes[30] = {};
        juce::ListenerList<Listener> listeners;
    };
}
