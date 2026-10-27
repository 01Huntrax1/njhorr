// Parameter specs and tables of the Njohrr UI (the data part is generated from patch/index.js by tools/nativeui/gen_data.js).
#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include <map>
#include <vector>

namespace njo
{
    // ---- layout constants (same as the JS UI) ----
    constexpr int OSC_N = 6, OSC_BASE = 1000, OSC_STRIDE = 64, FM_BASE = 1400, FRQ_BASE = 1600, PM_BASE = 1440, PD_BASE = 1480, RM_BASE = 1520, AM_BASE = 1560, MOD_SLOTS = 256, MODX_BASE = 4000;   // 256 matrix slots: 1-10 at 307.., 11-20 at 472.., 21-256 at MODX_BASE + 3 * (slot - 20)
    constexpr int BASE_W = 1180, BASE_H = 760;
    constexpr int MAX_SMP = 96000, CHUNK = 256;
    constexpr int MAX_WT = 262144, MAX_WT_FRAMES = 128;   // wavetables: up to 128 frames of 2048 samples (Vital style)
    inline int oscId (int o, int k) { return OSC_BASE + OSC_STRIDE * o + k; }
    inline int fmId (int s, int d) { return FM_BASE + 6 * s + d; }
    inline int pmId (int s, int d) { return PM_BASE + 6 * s + d; }
    inline int pdId (int s, int d) { return PD_BASE + 6 * s + d; }
    inline int rmId (int s, int d) { return RM_BASE + 6 * s + d; }
    inline int amId (int s, int d) { return AM_BASE + 6 * s + d; }
    inline bool isModSlotParam (int n) { return (n >= 307 && n <= 336) || (n >= 472 && n <= 501) || (n >= MODX_BASE && n < MODX_BASE + 3 * (MOD_SLOTS - 20)); }
    inline int slotBase (int s) { return s < 10 ? 307 + 3 * s : (s < 20 ? 472 + 3 * (s - 10) : MODX_BASE + 3 * (s - 20)); }   // first (source) parameter of a matrix slot
    const std::map<juce::String, int>& oscKeys();
    int oscKey (const char* name);   // OSC_K["wpos"] ...

    struct Spec
    {
        int num;
        juce::String label;
        double min, max, init;
        juce::String unit, kind;           // kind: sld knb btn sel stp
        juce::StringArray labels;
        int big;
        juce::String shortName;            // "" when the JS spec had none (use label)
        std::vector<std::pair<int, juce::String>> groups;   // option group headers for dropdowns: { first option index, title }

        juce::String name() const { return shortName.isNotEmpty() ? shortName : label; }
        bool isLog() const { return unit == "Hz" && min > 0; }
        double range() const { return max > min ? max - min : 1.0; }
        double toNorm (double v) const;      // 0..1 (log taper for Hz parameters)
        double fromNorm (double n) const;
    };

    const std::vector<Spec>& allSpecs();
    const Spec* findSpec (int num);          // nullptr if unknown

    const juce::StringArray& filterTypes();  const std::vector<std::pair<int, juce::String>>& filterGroups();
    const juce::StringArray& syncDivs();     const juce::StringArray& modWaves();
    const juce::StringArray& modSrc();       const std::vector<std::pair<int, juce::String>>& modSrcGroups();
    const juce::StringArray& modDst();       const std::vector<std::pair<int, juce::String>>& modDstGroups();
    const juce::StringArray& plaitsEngines();const std::vector<std::pair<int, juce::String>>& plaitsGroups();
    const std::vector<juce::StringArray>& plaitsParams();   // per engine: names of Harmonics / Timbre / Morph
    const juce::StringArray& distTypes();    const juce::StringArray& oscOuts();
    const juce::StringArray& uniStyles();    const juce::StringArray& warpModes();
    const juce::StringArray& lfoModes();     const juce::StringArray& srcTypes();
    const juce::StringArray& noteNames();
    // parameter number -> { matrix destination index, default amount } used by drag and drop modulation
    const std::map<int, std::pair<int, float>>& modTarget();

    // ---- FX rack ----
    struct FxParam { juce::String name; struct Fmt { const char* kind; double a, b; int dec; juce::String unit; } fmt; float def; };
    struct FxType  { juce::String name; float mix; juce::StringArray modes; std::vector<std::pair<int, juce::String>> groups; std::vector<FxParam> params; };
    struct FxRack  { juce::String name; int id, ord; };
    const std::vector<FxType>& fxTypes();
    const std::vector<FxRack>& fxRacks();
    struct FxLoc { int rk = 0, sl = 0, off = 0, g = 0, ord = -1; bool valid = false; };   // ord >= 0: a processing order parameter
    FxLoc fxLocate (int num);
    juce::String fxFormatParam (const FxParam::Fmt&, double n);

    struct LfoPoint { float x, y, c; };
    struct LfoPreset { juce::String name; int wave; std::vector<LfoPoint> pts; };   // wave >= 0: built-in shape, else points
    const std::vector<LfoPreset>& lfoPresets();

    constexpr int LFO_DRAWN = 6;
    inline int lfoWaveParam (int i) { return 247 + 2 * i; }
    inline int lfoRateParam (int i) { return 248 + 2 * i; }
    inline int lfoSyncParam (int i) { return 502 + 2 * i; }
    inline int lfoDivParam (int i) { return 503 + 2 * i; }
    inline int lfoModeParam (int i) { return 882 + 5 * i; }       // +1 delay +2 rise +3 smooth +4 phase
    inline int envParam (int i) { return 267 + 4 * i; }           // +0 attack +1 decay +2 sustain +3 release
    inline int frqParam (int i) { return FRQ_BASE + 4 * i; }      // Freq modulator i: +0 rate (ms) +1 transpose (st) +2 retrig +3 loop
    bool modSourceAllowed (int src, int paramNum);                 // Freq modulators (24..33) only reach the cutoff and Frequency knobs
    juce::String srcShort (int n);           // "LFO 3", "ENV 2", "VEL" ...
    juce::Colour srcColour (int n);

    // value -> display text, identical to fmt() of the JS UI. fxTypes: the effect type held by each of the 30 rack slots.
    juce::String formatValue (const Spec&, double v, const int* fxSlotTypes = nullptr);
}
