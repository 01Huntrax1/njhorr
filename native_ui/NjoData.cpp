#include "NjoData.h"
#include <cmath>

namespace njo
{
    double Spec::toNorm (double v) const
    {
        if (isLog()) return std::log (juce::jmax (v, min) / min) / std::log (max / min);
        return (v - min) / range();
    }

    double Spec::fromNorm (double n) const
    {
        n = juce::jlimit (0.0, 1.0, n);
        if (isLog()) return min * std::pow (max / min, n);
        return min + n * range();
    }

    int oscKey (const char* name) { auto& m = oscKeys(); auto it = m.find (name); return it == m.end() ? 0 : it->second; }

    const Spec* findSpec (int num)
    {
        static const std::map<int, const Spec*> idx = [] { std::map<int, const Spec*> m; for (auto& s : allSpecs()) m[s.num] = &s; return m; }();
        auto it = idx.find (num);
        return it == idx.end() ? nullptr : it->second;
    }

    FxLoc fxLocate (int num)
    {
        FxLoc r;
        auto& racks = fxRacks();
        for (int rk = 0; rk < (int) racks.size(); ++rk)
        {
            auto& R = racks[(size_t) rk];
            if (num >= R.id && num < R.id + 100) { r.valid = true; r.rk = rk; r.sl = (num - R.id) / 10; r.off = (num - R.id) % 10; r.g = rk * 10 + r.sl; return r; }
            if (num >= R.ord && num < R.ord + 10) { r.valid = true; r.rk = rk; r.ord = num - R.ord; return r; }
        }
        return r;
    }

    static juce::String hzText (double v) { return v >= 1000 ? juce::String (v / 1000, 2) + " kHz" : juce::String (v, v < 10 ? 2 : 0) + " Hz"; }
    static juce::String msText (double v) { return v >= 1000 ? juce::String (v / 1000, 2) + " s" : juce::String (v, v < 10 ? 1 : 0) + " ms"; }
    static juce::String signedText (double v, int dec, const juce::String& unit) { return (v > 0 ? "+" : "") + juce::String (v, dec) + unit; }

    juce::String fxFormatParam (const FxParam::Fmt& f, double n)
    {
        n = juce::jlimit (0.0, 1.0, n);
        juce::String k (f.kind);
        if (k == "lin")   return juce::String (f.a + n * (f.b - f.a), f.dec) + (f.unit.isNotEmpty() ? " " + f.unit : juce::String());
        if (k == "hz")    return hzText (f.a * std::pow (f.b / f.a, n));
        if (k == "ms")    return msText (f.a * std::pow (f.b / f.a, n));
        if (k == "pct")   return juce::String (juce::roundToInt (n * 100)) + "%";
        if (k == "pctof") return juce::String (juce::roundToInt (n * f.a * 100)) + "%";
        if (k == "db")    { double v = f.a + n * (f.b - f.a); return (v > 0 ? "+" : "") + juce::String (v, 1) + " dB"; }
        if (k == "out2x") return juce::String (n * 2, 2) + "x";
        if (k == "bits")  return juce::String (16 - 12 * n, 1) + " bit";
        if (k == "rate")  return "1/" + juce::String (1 + juce::roundToInt (n * 31));
        if (k == "pat")   { auto& pt = fxGatePatterns(); return pt[(size_t) juce::jlimit (0, (int) pt.size() - 1, (int) (n * (double) pt.size()))].first; }
        if (k == "qsc")   return "x" + juce::String (0.25 * std::pow (16.0, n), 2);
        if (k == "predly")return juce::String (juce::roundToInt (n * 100)) + " ms";
        if (k == "midq")  return "Q " + juce::String (0.3 * std::pow (4.0 / 0.3, n), 2);
        if (k == "ratio") return juce::String (1 + 19 * n * n, 1) + ":1";
        return juce::String (n, 2);
    }

    juce::String srcShort (int n)
    {
        if (n >= 1 && n <= 10) return "LFO " + juce::String (n);
        if (n >= 11 && n <= 20) return "ENV " + juce::String (n - 10);
        if (n == 21) return "VEL"; if (n == 22) return "KEY"; if (n == 23) return "RND";
        if (n >= 24 && n <= 33) return "FRQ " + juce::String (n - 23);
        return {};
    }

    juce::Colour srcColour (int n)
    {
        if (n >= 1 && n <= 10) return juce::Colour (0xffff6a4d);
        if (n >= 11 && n <= 20) return juce::Colour (0xff4db8ff);
        if (n >= 24) return juce::Colour (0xffb57bff);
        return juce::Colour (0xffc9c24a);
    }

    bool modSourceAllowed (int src, int num)
    {
        if (src < 24) return true;
        if (num < OSC_BASE || num >= OSC_BASE + OSC_STRIDE * OSC_N) return false;
        int k = (num - OSC_BASE) % OSC_STRIDE;
        return k == oscKey ("fcut") || k == oscKey ("freq");
    }

    juce::String formatValue (const Spec& s, double v, const int* fxSlotTypes)
    {
        auto loc = fxLocate (s.num);
        if (loc.valid)
        {
            if (loc.ord >= 0) return juce::String (juce::roundToInt (v) + 1);
            auto& types = fxTypes();
            int ty = fxSlotTypes ? fxSlotTypes[loc.g] : 0;
            auto& t = types[(size_t) juce::jlimit (0, (int) types.size() - 1, ty)];
            if (loc.off == 0) return types[(size_t) juce::jlimit (0, (int) types.size() - 1, juce::roundToInt (v))].name;
            if (loc.off == 1) return v > 0.5 ? "On" : "Off";
            if (loc.off == 2) return juce::String (juce::roundToInt (v * 100)) + "%";
            if (loc.off == 3) { if (t.modes.isEmpty()) return "-"; return t.modes[juce::jlimit (0, t.modes.size() - 1, juce::roundToInt (v))]; }
            int pi = loc.off - 4;
            if (pi >= 0 && pi < (int) t.params.size()) return fxFormatParam (t.params[(size_t) pi].fmt, v);
            return "-";
        }
        if (s.num == 880 || s.num == 881) return juce::String (juce::roundToInt (v * 100)) + "%";
        if (s.num == 522) return v < 1 ? juce::String ("HOST") : juce::String (juce::roundToInt (v)) + " BPM";
        if (s.num >= FM_BASE && s.num < AM_BASE + 36) return juce::String (juce::roundToInt (v)) + "%";
        if (s.num >= OSC_BASE && s.num < OSC_BASE + OSC_STRIDE * OSC_N)
        {
            int k = (s.num - OSC_BASE) % OSC_STRIDE;
            if (k == oscKey ("pan")) { int p = juce::roundToInt (v * 50); return p == 0 ? juce::String ("C") : (p < 0 ? "L" + juce::String (-p) : "R" + juce::String (p)); }
            if (k == oscKey ("freq")) { if (v < 0.001) return "Off"; double f = 20.0 * std::pow (1000.0, v); return f >= 1000 ? juce::String (f / 1000, 2) + " kHz" : juce::String (f, f < 100 ? 1 : 0) + " Hz"; }
            if (k == oscKey ("phase")) return juce::String (juce::roundToInt (v * 360)) + juce::String (juce::CharPointer_UTF8 ("\xc2\xb0"));
            if (k == oscKey ("root")) { int n = juce::roundToInt (v); return noteNames()[n % 12] + juce::String (n / 12 - 1); }
            if (k == oscKey ("uvox")) { int n = juce::roundToInt (v); return juce::String (n) + (n == 1 ? " voice" : " voices"); }
            if (k == oscKey ("udet")) return juce::String (juce::CharPointer_UTF8 ("\xc2\xb1")) + juce::String (juce::roundToInt (v * 50)) + " ct";
            if (k == oscKey ("semi")) return (v > 0 ? "+" : "") + juce::String (juce::roundToInt (v)) + " st";
        }
        if (s.labels.size()) return s.labels[juce::jlimit (0, s.labels.size() - 1, juce::roundToInt (v - s.min))];
        if (s.unit == "oct") { int o = juce::roundToInt (v); return (o > 0 ? "+" : "") + juce::String (o) + " oct"; }
        if (s.unit == "Hz") return hzText (v);
        if (s.unit == "s") return juce::String (v, v < 10 ? 2 : 1) + " s";
        if (s.unit == "ms") return v >= 1000 ? juce::String (v / 1000, 2) + " s" : juce::String (v, 0) + " ms";
        if (s.unit == "st") return signedText (v, s.kind == "stp" ? 0 : 1, " st");
        if (s.unit == "ct") return signedText (v, 0, " ct");
        if (s.unit == "dB") return signedText (v, 1, " dB");
        if (s.unit == "x") return juce::String (v, 2) + "x";
        if (s.unit == "bit") return juce::String (v, 0) + " bit";
        if (s.kind == "knb") return juce::String (v, 2);
        if (s.min >= -1 && s.max <= 1) return juce::String (juce::roundToInt (v * 100)) + "%";
        return juce::String (v, 2);
    }
}
