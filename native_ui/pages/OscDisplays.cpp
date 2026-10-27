#include "OscDisplays.h"
#include "../NjoPhys.h"
#include <cmath>

namespace njo
{
    using namespace theme;
    using C = std::complex<double>;

    // =============================================================== models (ports of the JS functions)
    namespace oscmodel
    {
        static C svfH (C s, double k, int mode)
        {
            C s2 = s * s, den = s2 + k * s + 1.0, num = 1.0;
            if (mode == 1) num = k * s;
            else if (mode == 2) num = s2;
            else if (mode == 3) num = s2 + 1.0;
            else if (mode == 4) num = s2 - k * s + 1.0;
            if (std::norm (den) < 1e-12) den = 1e-6;
            return num / den;
        }

        static C cpow (C a, int n) { C r = 1.0; for (int i = 0; i < n; ++i) r *= a; return r; }
        static C safeDiv (C a, C b) { if (std::norm (b) < 1e-12) b = 1e-6; return a / b; }

        std::complex<double> filterH (int ft, double fc, double res, double f, double sweep)
        {
            static const double VOWEL_F[5][3] = { { 800, 1150, 2900 }, { 400, 1600, 2700 }, { 350, 1700, 2700 }, { 450, 800, 2830 }, { 325, 700, 2530 } };
            const double pi = juce::MathConstants<double>::pi;
            C s (0.0, f / fc);
            double k = 2.0 - 1.96 * res;
            C one = safeDiv (1.0, 1.0 + s);
            C oneHP = s * one;
            auto lp = [&] (double kk) { return svfH (s, kk, 0); };
            auto hp = [&] (double kk) { return svfH (s, kk, 2); };
            auto bp = [&] (double kk) { return svfH (s, kk, 1); };
            C p1 = 1.0 + s;
            switch (ft)
            {
                case 0: return lp (k) * lp (1.2);
                case 1: return lp (k);
                case 2: return hp (k);
                case 3: return bp (k);
                case 4: return one;
                case 5: return one * lp (k);
                case 6: return oneHP;
                case 7: return oneHP * hp (k);
                case 8: return hp (k) * hp (1.2);
                case 9: return bp (k) * bp (k);
                case 10: return svfH (s, k, 3);
                case 11: return svfH (s, k, 3) * svfH (s, k, 3);
                case 12: return 1.0 + bp (0.6) * (res * 4.0);
                case 13: return 1.0 + lp (1.4) * (res * 3.0);
                case 14: return 1.0 + hp (1.4) * (res * 3.0);
                case 15: return svfH (s, k, 4);
                case 16: { double kr = res * 3.9; return safeDiv (1.0, cpow (p1, 4) + kr) * (1.0 + 0.4 * kr); }
                case 17: { double kr = res * 3.2; return safeDiv (1.0, cpow (p1, 4) + kr) * ((p1 + 1.0) * 0.5); }
                case 18: { double kr = res * 3.6; return safeDiv (1.0, cpow (p1, 3) + kr) * (1.0 + res); }
                case 19: return lp (k) * lp (1.2) * 1.3;
                case 20: case 21: case 28: case 29:
                {
                    double sw = sweep != 0.0 ? sweep : 1.0;
                    double th = 2.0 * pi * f / (fc / sw);
                    double fb = res * ((ft >= 28) ? 0.95 : 0.97) * ((ft == 21 || ft == 29) ? -1.0 : 1.0);
                    return safeDiv (1.0, C (1.0 - fb * std::cos (th), fb * std::sin (th))) * 0.7;
                }
                case 22:
                {
                    C A = cpow (safeDiv (1.0 - s, p1), 4);
                    double w = 2.0 * pi * f / 48000.0, fbk = res * 0.85;
                    C den = 1.0 + (A * C (std::cos (w), -std::sin (w))) * (-fbk);
                    return (1.0 + safeDiv (A, den)) * 0.5;
                }
                case 23:
                {
                    double p = juce::jlimit (0.0, 1.0, std::log (juce::jmax (fc, 100.0) / 100.0) / std::log (30.0)) * 4.0;
                    int v0 = juce::jmin (3, (int) std::floor (p));
                    double vf = p - v0;
                    double kq = 2.0 - 1.96 * juce::jmin (0.98, juce::jmax (0.0, 0.5 + res * 0.45));
                    const double w[3] = { 1.0, 0.7, 0.5 };
                    C acc = 0.0;
                    for (int i = 0; i < 3; ++i)
                    {
                        double fi = VOWEL_F[v0][i] * (1.0 - vf) + VOWEL_F[v0 + 1][i] * vf;
                        acc += svfH (C (0.0, f / fi), kq, 1) * w[i];
                    }
                    return acc * 1.4;
                }
                default:   // 24-27: MG Low 6 / 12 / 18 / 24
                {
                    double kr = res * 3.9; int n = ft - 23;
                    C y4 = safeDiv (1.2, cpow (p1, 4) + kr);
                    return y4 * cpow (p1, 4 - n) * (1.1 * (1.0 + 0.4 * kr));
                }
            }
        }

        float warpPhase (int mode, float amt, float ph)
        {
            if (mode == 1) return std::pow (ph, 1.0f + 3.0f * amt);
            if (mode == 2) return 1.0f - std::pow (1.0f - ph, 1.0f + 3.0f * amt);
            if (mode == 3) { float x = ph * (1.0f + 7.0f * amt); return x - std::floor (x); }
            if (mode == 4) { float w = 0.5f - 0.45f * amt; return ph < w ? ph * 0.5f / w : 0.5f + (ph - w) * 0.5f / (1.0f - w); }
            if (mode == 5) { float x = ph * (1.0f + amt); if (x > 1.0f) x = 2.0f - x; return juce::jlimit (0.0f, 1.0f, x); }
            if (mode == 6) return ph * (1.0f - amt) + (1.0f - ph) * amt;
            return ph;
        }

        float warpAmp (int mode, float amt, float y)
        {
            if (mode == 7) { float s = 2.0f + (1.0f - amt) * 254.0f; return std::floor (y * s + 0.5f) / s; }
            if (mode == 8) return y * (1.0f - amt) + amt * std::sin (y * (1.0f + 4.0f * amt) * 1.5708f);
            return y;
        }

        int pickFrameIndex (int len)
        {
            if (len % 4096 == 0) return 4;
            if (len % 2048 == 0) return 3;
            if (len >= 2048) return 3;
            for (int i : { 2, 1, 0 }) if (len % frameSizes[i] == 0) return i;
            int k = 0;
            for (int j = 0; j < 5; ++j) if (frameSizes[j] <= len) k = j;
            return k;
        }
    }

    // =============================================================== drawing helpers
    namespace
    {
        void strokeDashed (juce::Graphics& g, const juce::Path& p, float lw, float d0, float d1)
        {
            juce::Path out; const float dash[2] = { d0, d1 };
            juce::PathStrokeType (lw).createDashedStroke (out, p, dash, 2);
            g.fillPath (out);
        }

        // path of a trace with a soft glow underneath
        void glowStroke (juce::Graphics& g, const juce::Path& p, juce::Colour c, float lw, bool glow)
        {
            if (glow) { g.setColour (juce::Colour (0xffff3b30).withAlpha (0.22f)); g.strokePath (p, juce::PathStrokeType (lw + 5.0f, juce::PathStrokeType::curved, juce::PathStrokeType::rounded)); }
            g.setColour (c);
            g.strokePath (p, juce::PathStrokeType (lw, juce::PathStrokeType::curved, juce::PathStrokeType::rounded));
        }

        void cornerBrackets (juce::Graphics& g, float W, float H, float bl)
        {
            const float bm = 3.0f;
            juce::Path p;
            p.startNewSubPath (bm, bm + bl); p.lineTo (bm, bm); p.lineTo (bm + bl, bm);
            p.startNewSubPath (W - bm - bl, bm); p.lineTo (W - bm, bm); p.lineTo (W - bm, bm + bl);
            p.startNewSubPath (bm, H - bm - bl); p.lineTo (bm, H - bm); p.lineTo (bm + bl, H - bm);
            p.startNewSubPath (W - bm - bl, H - bm); p.lineTo (W - bm, H - bm); p.lineTo (W - bm, H - bm - bl);
            g.setColour (juce::Colour (0xffff5042).withAlpha (0.85f));
            g.strokePath (p, juce::PathStrokeType (2.0f));
        }

        // the dark recessed display box shared by both pictures
        void displayBox (juce::Graphics& g, juce::Rectangle<float> r)
        {
            g.setColour (juce::Colour (0xff0d0404)); g.fillRoundedRectangle (r, 4.0f);
        }
        void displayBorder (juce::Graphics& g, juce::Rectangle<float> r)
        {
            // inner shadow + outer glow, then the border
            g.setColour (juce::Colour (0xffff3b30).withAlpha (0.10f)); g.drawRoundedRectangle (r.expanded (1.5f), 5.0f, 2.0f);
            g.setColour (juce::Colours::black.withAlpha (0.55f)); g.drawRoundedRectangle (r.reduced (1.5f), 3.0f, 3.0f);
            g.setColour (juce::Colour (0xff7a1d18)); g.drawRoundedRectangle (r.reduced (0.5f), 4.0f, 1.0f);
        }
    }

    // =============================================================== OscDisplay
    OscDisplay::OscDisplay (Ctx& c, SoundMemory& m, int osc) : ctx (c), mem (m), o (osc)
    {
        ctx.addListener (this);
        mem.addChangeListener (this);
        setInterceptsMouseClicks (false, false);
    }

    OscDisplay::~OscDisplay() { mem.removeChangeListener (this); ctx.removeListener (this); }

    void OscDisplay::paramChanged (int num, float)
    {
        if (num >= phys::PHY_BASE + phys::PHY_STRIDE * o && num < phys::PHY_BASE + phys::PHY_STRIDE * (o + 1)) { repaint(); return; }
        int k = num - oscId (o, 0);
        if (k < 0 || k >= OSC_STRIDE) return;
        for (const char* n : { "type", "pleng", "wpos", "wsize", "w1m", "w1a", "w2m", "w2a", "sstart", "sloop", "root" })
            if (k == oscKey (n)) { repaint(); return; }
    }

    void OscDisplay::paint (juce::Graphics& g)
    {
        auto pic = getLocalBounds().toFloat().withHeight ((float) pictureH);
        displayBox (g, pic);

        const float W = 640.0f, H = 190.0f;
        juce::String info;
        {
            juce::Graphics::ScopedSaveState ss (g);
            g.reduceClipRegion (pic.toNearestInt());
            g.addTransform (juce::AffineTransform::scale (pic.getWidth() / W, pic.getHeight() / H));   // same stretched 640 x 190 canvas as the web UI
            // grid
            {
                juce::Path grid;
                for (float gx = 0; gx <= W + 0.5f; gx += W / 16.0f) { grid.startNewSubPath (gx, 0); grid.lineTo (gx, H); }
                for (float gy = 0; gy <= H + 0.5f; gy += H / 4.0f) { grid.startNewSubPath (0, gy); grid.lineTo (W, gy); }
                g.setColour (juce::Colour (0xffff3b30).withAlpha (0.10f));
                g.strokePath (grid, juce::PathStrokeType (1.0f));
                g.setColour (juce::Colour (0xffff3b30).withAlpha (0.38f));
                g.drawLine (0, H / 2, W, H / 2, 1.0f);
            }

            const int type = juce::jlimit (0, 4, juce::roundToInt (pv ("type")));
            auto traceOf = [&] (const std::vector<float>& arr)
            {
                juce::Path p;
                for (int x = 0; x < (int) arr.size(); ++x)
                {
                    float y = H / 2 - juce::jlimit (-1.2f, 1.2f, arr[(size_t) x]) * (H / 2 - 4);
                    if (x == 0) p.startNewSubPath ((float) x, y); else p.lineTo ((float) x, y);
                }
                return p;
            };

            if (type == 0)
            {
                auto* s = mem.get (SoundMemory::Wavetable, o);
                const int total = s ? (int) s->data.size() : 0;
                if (s == nullptr || total < 2) info = "NO WAVETABLE LOADED";
                else
                {
                    int fl = juce::jmax (2, juce::jmin (oscmodel::frameSizes[juce::jlimit (0, 4, juce::roundToInt (pv ("wsize")))], total));
                    int nF = juce::jmax (1, total / fl);
                    float p = juce::jlimit (0.0f, 1.0f, pv ("wpos")) * (float) (nF - 1);
                    int fa = juce::jlimit (0, nF - 1, (int) std::floor (p)), fb = juce::jmin (nF - 1, fa + 1);
                    float ff = p - (float) fa;
                    const int Wp = (int) W;
                    std::vector<float> cyc ((size_t) Wp);
                    double mean = 0;
                    for (int x = 0; x < Wp; ++x)
                    {
                        int i = juce::jmin (fl - 1, (int) std::floor ((float) x / W * (float) fl));
                        auto at = [&] (int fr) { size_t ix = (size_t) fr * (size_t) fl + (size_t) i; return ix < s->data.size() ? s->data[ix] : 0.0f; };
                        cyc[(size_t) x] = at (fa) * (1 - ff) + at (fb) * ff;
                        mean += cyc[(size_t) x];
                    }
                    mean /= Wp;
                    for (auto& v : cyc) v -= (float) mean;

                    int m1 = juce::roundToInt (pv ("w1m")), m2 = juce::roundToInt (pv ("w2m"));
                    float a1 = pv ("w1a"), a2 = pv ("w2a");
                    juce::String tag;
                    if (m1 != 0 || m2 != 0)
                    {
                        std::vector<float> w ((size_t) Wp);
                        double wm = 0;
                        for (int x = 0; x < Wp; ++x)
                        {
                            float rp = (float) x / W;
                            if (m1 >= 1 && m1 <= 6) rp = oscmodel::warpPhase (m1, a1, rp);
                            if (m2 >= 1 && m2 <= 6) rp = oscmodel::warpPhase (m2, a2, rp);
                            rp = juce::jlimit (0.0f, 0.99999f, rp);
                            float fi = rp * (float) Wp; int i0 = (int) std::floor (fi); float fr = fi - (float) i0;
                            float y = cyc[(size_t) i0] * (1 - fr) + cyc[(size_t) ((i0 + 1) % Wp)] * fr;
                            if (m1 >= 7) y = oscmodel::warpAmp (m1, a1, y);
                            if (m2 >= 7) y = oscmodel::warpAmp (m2, a2, y);
                            w[(size_t) x] = y; wm += y;
                        }
                        wm /= Wp;
                        for (auto& v : w) v -= (float) wm;
                        juce::StringArray used;
                        if (m1 > 0) used.add (warpModes()[juce::jlimit (0, warpModes().size() - 1, m1)]);
                        if (m2 > 0) used.add (warpModes()[juce::jlimit (0, warpModes().size() - 1, m2)]);
                        if (used.size()) tag = " / WARP " + used.joinIntoString (" + ");
                        glowStroke (g, traceOf (cyc), juce::Colour (0xffff968c).withAlpha (0.40f), 1.0f, false);
                        glowStroke (g, traceOf (w), juce::Colour (0xffff7a45), 2.0f, true);
                    }
                    else glowStroke (g, traceOf (cyc), juce::Colour (0xffff3b30), 2.0f, true);
                    info = s->name + " / FRAME " + juce::String (p + 1.0f, 1) + " OF " + juce::String (nF) + tag;
                }
            }
            else if (type == 1)
            {
                auto* s = mem.get (SoundMemory::Sample, o);
                if (s == nullptr || s->data.empty()) info = "NO SAMPLE LOADED";
                else
                {
                    const int n = (int) s->data.size(), Wp = (int) W;
                    int step = juce::jmax (1, n / Wp);
                    float start = juce::jlimit (0.0f, 1.0f, pv ("sstart"));
                    g.setColour (juce::Colour (0xffff3b30).withAlpha (0.12f));
                    g.fillRect (0.0f, 0.0f, W * start, H);
                    juce::Path p;
                    for (int x = 0; x < Wp; ++x)
                    {
                        int a = (int) ((double) x / W * n);
                        float mn = 1, mx = -1;
                        for (int i = a; i < juce::jmin (n, a + step); ++i) { float v = s->data[(size_t) i]; mn = juce::jmin (mn, v); mx = juce::jmax (mx, v); }
                        if (mx < mn) mn = mx = 0;
                        p.startNewSubPath ((float) x, H / 2 - mx * (H / 2 - 4)); p.lineTo ((float) x, H / 2 - mn * (H / 2 - 4));
                    }
                    g.setColour (juce::Colour (0xffff3b30));
                    g.strokePath (p, juce::PathStrokeType (1.5f));
                    juce::Path sl; sl.startNewSubPath (W * start, 0); sl.lineTo (W * start, H);
                    g.setColour (juce::Colour (0xffffc8be).withAlpha (0.7f));
                    strokeDashed (g, sl, 1.0f, 4.0f, 4.0f);
                    info = s->name + " / " + juce::String ((double) n / 48000.0, 2) + " S" + (pv ("sloop") > 0.5f ? " / LOOP" : "");
                }
            }
            else if (type == 4)
            {
                // two cycles of the DCO mix (saw + pulse + sub, not band-limited), noise as a level bar
                auto V = [&] (const char* key) { return ctx.get (phys::phyId (o, phys::key (key))); };
                const int range = juce::jlimit (0, 2, juce::roundToInt (V ("jrange")));
                const int stp = juce::jlimit (0, 4, juce::roundToInt (V ("jstype"))), ptp = juce::jlimit (0, 2, juce::roundToInt (V ("jptype"))), btp = juce::jlimit (0, 5, juce::roundToInt (V ("jbtype")));
                const float cv = V ("jcurve") * 4.0f, wd = juce::jlimit (0.05f, 0.95f, V ("jwidth"));
                auto fr = [] (float x) { return x - std::floor (x); };
                auto ramp = [] (float q) { return 2.0f * q - 1.0f; };
                auto sq = [] (float q, float w) { return q < w ? 1.0f : -1.0f; };
                juce::Path p;
                const int Wp = (int) W;
                for (int x = 0; x < Wp; ++x)
                {
                    const float t = (float) x / W * 2.0f, ph = fr (t), q2 = fr (t / 2.0f), q4 = fr (t / 4.0f);
                    float saw;
                    if (stp == 1) saw = (ph < wd ? ramp (ph / wd) : -1.0f) + (1.0f - wd);
                    else if (stp == 2) saw = 0.75f * ramp (ph) + 0.25f * ramp (fr (ph * 2.0f));
                    else if (stp == 3) saw = 0.7f * ramp (ph) + 0.3f * ramp (fr (ph * 3.0f));
                    else { saw = cv > 0.01f ? 2.0f * (std::exp (cv * ph) - 1.0f) / (std::exp (cv) - 1.0f) - 1.0f : ramp (ph); if (stp == 4) saw = std::tanh (1.7f * saw) * 1.12f; }
                    const float pul = sq (ph, ptp == 0 ? wd : (ptp == 1 ? 0.25f : 0.125f));
                    const float subs[6] = { sq (q2, 0.5f), sq (q2, 0.25f), sq (q4, 0.5f), sq (q4, 0.25f), 0.5f * (sq (q2, 0.5f) + sq (q4, 0.5f)), q2 < 0.5f ? 4.0f * q2 - 1.0f : 3.0f - 4.0f * q2 };
                    const float y = (saw * V ("jsaw") + pul * V ("jpulse") + subs[btp] * V ("jsub")) * 0.55f;
                    const float py = H / 2 - juce::jlimit (-1.2f, 1.2f, y) * (H / 2 - 4);
                    if (x == 0) p.startNewSubPath ((float) x, py); else p.lineTo ((float) x, py);
                }
                g.setColour (juce::Colour (0xffff3b30)); g.strokePath (p, juce::PathStrokeType (2.0f));
                const float nz = V ("jnoise") * (H - 12);
                g.setColour (juce::Colour (0xffffa040).withAlpha (0.5f)); g.fillRect (W - 14, H - 6 - nz, 8.0f, nz);
                info = juce::String ("ALPHA JUNO / SAW ") + juce::String (stp + 1) + " + PULSE " + juce::String (ptp + 1) + " + SUB " + juce::String (btp + 1) + " / " + (range == 0 ? "16'" : (range == 1 ? "8'" : "4'")) + " / WIDTH " + juce::String (juce::roundToInt (wd * 100)) + " %"
                       + (V ("jpwm") > 0.0f ? " / PWM " + juce::String (V ("jpwmr"), 1) + " HZ" : juce::String());
            }
            else if (type == 3)
            {
                // mode spectrum of resonator A (red) and B (orange): x = frequency ratio on a log axis, height = amplitude (dimmer for modes that die quickly)
                auto V = [&] (const char* key) { return ctx.get (phys::phyId (o, phys::key (key))); };
                const float bal = V ("phbal"), tune = std::pow (2.0f, V ("phtunB") / 12.0f);
                auto xo = [&] (float r) { return 14.0f + (W - 28.0f) * std::log2 (juce::jmax (r, 0.5f) / 0.5f) / std::log2 (80.0f / 0.5f); };
                g.setFont (font (std::round (H * 0.07f), true));
                for (float f : { 1.0f, 2.0f, 4.0f, 8.0f, 16.0f, 32.0f, 64.0f })
                {
                    g.setColour (juce::Colour (0xffffc8be).withAlpha (0.18f)); g.fillRect (xo (f), 4.0f, 1.0f, H - 18.0f);
                    g.setColour (juce::Colour (0xffffc8be).withAlpha (0.45f)); g.drawText (juce::String ((int) f) + "x", juce::Rectangle<float> (xo (f) - 6.0f, H - 15.0f, 30.0f, 12.0f), juce::Justification::centredLeft, false);
                }
                for (int res = 0; res < 2; ++res)
                {
                    const char* sfx = res == 0 ? "A" : "B";
                    const int md = juce::jlimit (0, 8, juce::roundToInt (V (res == 0 ? "phmodA" : "phmodB")));
                    const float hit = V (res == 0 ? "phhitA" : "phhitB"), inh = V (res == 0 ? "phinhA" : "phinhB"), mat = V (res == 0 ? "phmatA" : "phmatB");
                    const float mul = res == 0 ? 1.0f : tune, vol = res == 0 ? 1.0f - bal : bal;
                    juce::ignoreUnused (sfx);
                    float am[16], sum = 0;
                    for (int i = 0; i < 16; ++i) { am[i] = std::abs (std::sin (juce::MathConstants<float>::pi * hit * (float) (i + 1))) / std::pow ((float) (i + 1), phys::AEXP[md]); sum += am[i] * am[i]; }
                    const float nr = 1.0f / std::sqrt (juce::jmax (sum, 0.05f));
                    g.setColour ((res == 0 ? juce::Colour (0xffff3b30) : juce::Colour (0xffffa040)).withAlpha (0.35f + 0.65f * juce::jmin (1.0f, vol * 1.5f)));
                    for (int i = 0; i < 16; ++i)
                    {
                        const float r = phys::RAT[md][i] * (1.0f + inh * 0.004f * (float) (i * i)) * mul;
                        const float t60 = juce::jmin (1.0f, std::pow (phys::RAT[md][i], -1.6f * (1.0f - mat)));
                        const float h = juce::jmin (1.0f, am[i] * nr * 1.2f) * (H - 24.0f) * (0.35f + 0.65f * t60);
                        g.fillRect (xo (r) - 1.5f + (res == 1 ? 2.0f : 0.0f), H - 16.0f - h, 3.0f, h);
                    }
                }
                auto mname = [&] (const char* key) { return juce::String (phys::model (juce::roundToInt (V (key)))).toUpperCase(); };
                info = "PHYSICAL / A " + mname ("phmodA") + " + B " + mname ("phmodB") + (V ("phser") > 0.5f ? " / SERIAL" : "");
            }
            else
            {
                int eng = juce::jlimit (0, plaitsEngines().size() - 1, juce::roundToInt (pv ("pleng")));
                g.setColour (juce::Colour (0xffff7864).withAlpha (0.85f));
                g.setFont (font (std::round (H * 0.2f), true));
                g.drawText (plaitsEngines()[eng].toUpperCase(), juce::Rectangle<float> (0, H / 2 + H * 0.05f - H * 0.2f, W, H * 0.25f), juce::Justification::centredBottom, false);
                g.setColour (juce::Colour (0xffffc8be).withAlpha (0.5f));
                g.setFont (font (std::round (H * 0.1f), true));
                g.drawText ("PLAITS / " + juce::String (eng + 1) + " OF " + juce::String (plaitsEngines().size()), juce::Rectangle<float> (0, H / 2 + H * 0.25f - H * 0.1f, W, H * 0.13f), juce::Justification::centredBottom, false);
                auto& pp = plaitsParams();
                info = plaitsEngines()[eng] + " / " + (eng < (int) pp.size() ? pp[(size_t) eng].joinIntoString (" - ") : juce::String());
            }
            cornerBrackets (g, W, H, 16.0f);
        }
        displayBorder (g, pic);

        g.setColour (dim);
        g.setFont (mono (8.0f));
        g.drawText (info, getLocalBounds().withTrimmedTop (pictureH + 3).withHeight (12), juce::Justification::centredLeft, true);
    }

    namespace oscmodel
    {
        float tblDefault (bool filter, int f, int i)
        {
            const double u = i / 511.0, PI = juce::MathConstants<double>::pi;
            if (filter)
            {
                const double o = (u - 0.5) * 8.0;
                auto sig = [] (double z) { return 1.0 / (1.0 + std::exp (z)); };
                auto ga = [&] (double c) { return std::exp (-(o - c) * (o - c) * 2.0); };
                const double g[16] = { sig (o * 2), sig (o * 6), std::exp (-o * o * 0.5), std::exp (-o * o * 3), sig (-o * 6), sig (-o * 2), 1 - std::exp (-o * o * 3),
                    std::min (1.0, sig (o * 3) + 0.9 * std::exp (-o * o * 8)), 0.5 + 0.5 * std::cos (o * 6.2831853), 0.5 + 0.5 * std::cos (o * 12.566371),
                    std::min (1.0, ga (-1.6) + ga (-0.3)), std::min (1.0, ga (-1.9) + ga (0.7)), std::min (1.0, ga (-2.4) + ga (1.0)), std::min (1.0, ga (-1.5) + ga (-0.6)),
                    std::min (1.0, ga (-2.2) + ga (-0.9)), sig (-o * 0.8) };
                return (float) (g[juce::jlimit (0, 15, f)] * 2.0 - 1.0);
            }
            const double x = u * 2.0 - 1.0;
            const double v[16] = { x, std::tanh (2 * x) / 0.9640276, std::tanh (5 * x) / 0.9999092, juce::jlimit (-1.0, 1.0, 2 * x), std::sin (x * PI / 2), std::sin (x * 1.5 * PI),
                std::sin (x * 2.5 * PI), std::sin (x * 4.5 * PI), 4 * x * x * x - 3 * x, 16 * std::pow (x, 5) - 20 * x * x * x + 5 * x, 2 * std::abs (x) - 1,
                (std::min (std::floor ((x + 1) * 2), 3.0) + 0.5) * 0.5 - 1, (std::min (std::floor ((x + 1) * 4), 7.0) + 0.5) * 0.25 - 1,
                (std::tanh (2 * x + 0.6) - 0.5370496) / 0.4524, std::sin (x * 2 * PI), std::sin (x * 4 * PI) };
            return (float) juce::jlimit (-1.0, 1.0, v[juce::jlimit (0, 15, f)]);
        }

        void tblFrame (const std::vector<float>* loaded, bool filter, float pos, float* out)
        {
            const int nF = loaded ? juce::jlimit (1, 64, (int) loaded->size() / 512) : 16;
            const float fp = juce::jlimit (0.0f, 1.0f, pos) * (float) (nF - 1);
            const int f0 = (int) fp, f1 = juce::jmin (f0 + 1, nF - 1); const float ff = fp - (float) f0;
            auto at = [&] (int f, int i) { return loaded ? juce::jlimit (-1.0f, 1.0f, (*loaded)[(size_t) (f * 512 + i)]) : tblDefault (filter, f, i); };
            for (int i = 0; i < 512; ++i) { float a = at (f0, i); out[i] = a + (at (f1, i) - a) * ff; }
        }
    }

    // =============================================================== FilterDisplay
    FilterDisplay::FilterDisplay (Ctx& c, SoundMemory& m, int osc) : ctx (c), mem (m), o (osc) { ctx.addListener (this); mem.addChangeListener (this); setInterceptsMouseClicks (false, false); }
    FilterDisplay::~FilterDisplay() { mem.removeChangeListener (this); ctx.removeListener (this); }

    void FilterDisplay::paramChanged (int num, float)
    {
        int k = num - oscId (o, 0);
        if ((k >= oscKey ("fon") && k <= oscKey ("fkey")) || k == oscKey ("wfpos") || (k >= oscKey ("wfmix") && k <= oscKey ("wflaw"))) repaint();
    }

    void FilterDisplay::paint (juce::Graphics& g)
    {
        auto box = getLocalBounds().toFloat();
        displayBox (g, box);
        const float W = 600.0f, H = W * box.getHeight() / juce::jmax (1.0f, box.getWidth());   // uniform scale: the picture keeps its proportions at any size
        {
            juce::Graphics::ScopedSaveState ss (g);
            g.reduceClipRegion (getLocalBounds());
            g.addTransform (juce::AffineTransform::scale (box.getWidth() / W, box.getHeight() / H));
            auto yOf = [&] (double db) { return (float) (H * (1.0 - (juce::jlimit (-48.0, 24.0, db) + 48.0) / 72.0)); };
            auto xOf = [&] (double f) { return (float) (W * std::log (f / 20.0) / std::log (1000.0)); };
            juce::Path grid;
            for (double fx : { 100.0, 1000.0, 10000.0 }) { grid.startNewSubPath (xOf (fx), 0); grid.lineTo (xOf (fx), H); }
            for (double d : { -36.0, -24.0, -12.0, 12.0 }) { grid.startNewSubPath (0, yOf (d)); grid.lineTo (W, yOf (d)); }
            g.setColour (juce::Colour (0xffff3b30).withAlpha (0.10f)); g.strokePath (grid, juce::PathStrokeType (1.0f));
            g.setColour (juce::Colour (0xffff3b30).withAlpha (0.40f)); g.drawLine (0, yOf (0), W, yOf (0), 1.0f);
            g.setColour (juce::Colour (0xffff7864).withAlpha (0.55f));
            g.setFont (font (15.0f, true));
            auto txt = [&] (const juce::String& t, float x, float baseY) { g.drawText (t, juce::Rectangle<float> (x, baseY - 15, 80, 18), juce::Justification::bottomLeft, false); };
            txt ("100", xOf (100) + 4, H - 6); txt ("1k", xOf (1000) + 4, H - 6); txt ("10k", xOf (10000) + 4, H - 6);
            txt ("0 dB", 6, yOf (0) - 5);
            cornerBrackets (g, W, H, 14.0f);

            const int N = 220;
            const int ft = juce::roundToInt (ctx.get (oscId (o, oscKey ("ftype"))));
            const double fc = ctx.get (oscId (o, oscKey ("fcut"))), res = ctx.get (oscId (o, oscKey ("fres")));
            float tbl[512];
            if (ft >= 30)
            {
                auto* sl = mem.get (SoundMemory::FilterTable, o);
                oscmodel::tblFrame (sl ? &sl->data : nullptr, true, ctx.get (oscId (o, oscKey ("wfpos"))), tbl);
            }
            auto curve = [&] (double sweep, bool fill, juce::Colour col, float lw, bool glow)
            {
                juce::Path p;
                for (int i = 0; i < N; ++i)
                {
                    double f = 20.0 * std::pow (1000.0, (double) i / (N - 1));
                    double mag;
                    if (ft >= 30)   // Wavefilter: the table frame along Range octaves around the cutoff, with Warp / Law / Contrast / Tilt / Mix
                    {
                        auto P = [&] (const char* key) { return (double) ctx.get (oscId (o, oscKey (key))); };
                        const double W2 = juce::jlimit (2.0, 14.0, P ("wfrange")), pw = std::pow (2.0, juce::jlimit (-1.0, 1.0, P ("wfwarp")));
                        const double ex = std::pow (2.0, 1.5 * juce::jlimit (-1.0, 1.0, P ("wfcont"))), tilt = juce::jlimit (-1.0, 1.0, P ("wftilt"));
                        const int law = juce::jlimit (0, 2, juce::roundToInt (P ("wflaw")));
                        const double mix = juce::jlimit (0.0, 1.0, P ("wfmix"));
                        const double r = std::log2 (f / juce::jmax (20.0, fc));
                        const double t = juce::jlimit (-1.0, 1.0, 2.0 * r / W2);
                        const double u = 0.5 + (t < 0 ? -0.5 : 0.5) * std::pow (std::abs (t), pw), x = u * 511.0;
                        int i0 = (int) x, i1 = juce::jmin (i0 + 1, 511);
                        const double v = tbl[i0] + (tbl[i1] - tbl[i0]) * (x - i0);
                        double gn = law == 0 ? v * 0.5 + 0.5 : law == 1 ? v : std::pow (10.0, (v - 1.0) * 1.5);
                        if (ex != 1.0) gn = (gn < 0 ? -1.0 : 1.0) * std::pow (std::abs (gn), ex);
                        if (tilt != 0.0) gn = juce::jmin (gn * std::pow (2.0, tilt * r), 4.0);
                        mag = std::abs (1.0 + (gn - 1.0) * mix);
                    }
                    else mag = std::abs (oscmodel::filterH (ft, fc, res, f, sweep));
                    float x = W * (float) i / (N - 1), y = yOf (20.0 * std::log10 (juce::jmax (1e-5, mag)));
                    if (i == 0) p.startNewSubPath (x, y); else p.lineTo (x, y);
                }
                if (fill)
                {
                    juce::Path a (p); a.lineTo (W, H); a.lineTo (0, H); a.closeSubPath ();
                    g.setGradientFill (juce::ColourGradient (juce::Colour (0xffff3b30).withAlpha (0.38f), 0, 0, juce::Colour (0xffff3b30).withAlpha (0.02f), 0, H, false));
                    g.fillPath (a);
                }
                glowStroke (g, p, col, lw, glow);
            };
            if (ctx.get (oscId (o, oscKey ("fon"))) < 0.5f)
                curve (1.0, false, juce::Colour (0xffb4aaa5).withAlpha (0.45f), 1.5f, false);
            else
            {
                if (ft == 28 || ft == 29)
                {
                    curve (0.5, false, juce::Colour (0xffff9682).withAlpha (0.35f), 1.0f, false);
                    curve (1.5, false, juce::Colour (0xffff9682).withAlpha (0.35f), 1.0f, false);
                }
                curve (1.0, true, juce::Colour (0xffff3b30), 2.5f, true);
                float x = xOf (juce::jmax (20.0, fc));
                juce::Path m; m.startNewSubPath (x, 0); m.lineTo (x, H);
                g.setColour (juce::Colour (0xffffc8be).withAlpha (0.55f));
                strokeDashed (g, m, 1.0f, 4.0f, 4.0f);
            }
        }
        displayBorder (g, box);
    }

    // =============================================================== DistDisplay
    DistDisplay::DistDisplay (Ctx& c, SoundMemory& m, int osc) : ctx (c), mem (m), o (osc) { ctx.addListener (this); mem.addChangeListener (this); setInterceptsMouseClicks (false, false); }
    DistDisplay::~DistDisplay() { mem.removeChangeListener (this); ctx.removeListener (this); }

    void DistDisplay::paramChanged (int num, float)
    {
        int k = num - oscId (o, 0);
        for (const char* n : { "dtype", "ddrv", "dmix", "wdpos" }) if (k == oscKey (n)) { repaint(); return; }
    }

    float DistDisplay::transfer (float x) const
    {
        const int ty = juce::roundToInt (ctx.get (oscId (o, oscKey ("dtype"))));
        const float d = ctx.get (oscId (o, oscKey ("ddrv"))), mix = ctx.get (oscId (o, oscKey ("dmix")));
        if (ty <= 0 || mix <= 0.0005f) return x;
        float y;
        if (ty >= 7)
        {
            float tbl[512];
            auto* sl = mem.get (SoundMemory::ShaperTable, o);
            oscmodel::tblFrame (sl ? &sl->data : nullptr, false, ctx.get (oscId (o, oscKey ("wdpos"))), tbl);
            float u = (juce::jlimit (-1.0f, 1.0f, x * (1.0f + d * 3.0f)) * 0.5f + 0.5f) * 511.0f;
            int i0 = (int) u, i1 = juce::jmin (i0 + 1, 511);
            y = tbl[i0] + (tbl[i1] - tbl[i0]) * (u - (float) i0);
        }
        else   // mirror of shapeSigAlg in the DSP
        {
            const int al = ty - 1; const float xx = x * (1.0f + d * 8.0f);
            y = xx / (1.0f + std::abs (xx));
            if (al == 1) { float bias = 0.3f * d, yb = xx + bias; y = yb / (1.0f + std::abs (yb)) - bias / (1.0f + std::abs (bias)); }
            else if (al == 2) y = juce::jlimit (-0.9f, 0.9f, xx);
            else if (al == 3) y = std::sin (xx * 1.5f) * 0.8f;
            else if (al == 4) y = std::sin (juce::jlimit (-1.5708f, 1.5708f, xx));
            else if (al == 5) { float lv = 6.0f + (1.0f - d) * 26.0f; y = std::round (y * lv) / lv; }
            y *= 1.0f + d * 0.5f;
        }
        return x * (1.0f - mix) + y * mix;
    }

    void DistDisplay::paint (juce::Graphics& g)
    {
        auto box = getLocalBounds().toFloat();
        displayBox (g, box);
        {
            juce::Graphics::ScopedSaveState ss (g);
            g.reduceClipRegion (getLocalBounds());
            const float W = box.getWidth(), H = box.getHeight();
            g.setColour (juce::Colour (0xffff3b30).withAlpha (0.10f));
            g.drawLine (0, H / 2, W, H / 2, 1.0f); g.drawLine (W / 2, 0, W / 2, H, 1.0f);
            g.setColour (juce::Colour (0xffffc8be).withAlpha (0.22f)); g.drawLine (0, H, W, 0, 1.0f);
            cornerBrackets (g, W, H, 14.0f);
            const bool on = juce::roundToInt (ctx.get (oscId (o, oscKey ("dtype")))) > 0;
            juce::Path p; const int N = juce::jmax (2, (int) W);
            for (int i = 0; i < N; ++i)
            {
                float x = (float) i / (N - 1) * 2.0f - 1.0f, y = juce::jlimit (-1.2f, 1.2f, transfer (x));
                float px = (float) i * W / (N - 1), py = H * 0.5f - y * (H * 0.5f - 4.0f);
                if (i == 0) p.startNewSubPath (px, py); else p.lineTo (px, py);
            }
            glowStroke (g, p, on ? juce::Colour (0xffff3b30) : juce::Colour (0xffb4aaa5).withAlpha (0.45f), 2.5f, on);
        }
        displayBorder (g, box);
    }

    // =============================================================== ResoDisplay
    ResoDisplay::ResoDisplay (Ctx& c, int osc) : ctx (c), o (osc) { ctx.addListener (this); setInterceptsMouseClicks (false, false); }
    ResoDisplay::~ResoDisplay() { ctx.removeListener (this); }

    void ResoDisplay::paramChanged (int num, float)
    {
        int k = num - oscId (o, 0);
        for (const char* n : { "rson", "rsmod", "rsdec", "rsmat", "rshit", "rsinh", "rstune", "rsmix" }) if (k == oscKey (n)) { repaint(); return; }
    }

    void ResoDisplay::paint (juce::Graphics& g)
    {
        auto box = getLocalBounds().toFloat();
        displayBox (g, box);
        {
            juce::Graphics::ScopedSaveState ss (g);
            g.reduceClipRegion (getLocalBounds());
            const float W = box.getWidth(), H = box.getHeight();
            auto pv = [this] (const char* k) { return ctx.get (oscId (o, oscKey (k))); };
            const bool on = pv ("rson") > 0.5f;
            const int model = juce::jlimit (0, 8, juce::roundToInt (pv ("rsmod")));
            const float dec = pv ("rsdec"), mat = pv ("rsmat"), hit = pv ("rshit"), inh = pv ("rsinh"), mix = pv ("rsmix");
            const float f0 = 220.0f * std::pow (2.0f, pv ("rstune") / 12.0f);
            const float fLo = 30.0f, fHi = 16000.0f;
            auto xOf = [&] (float f) { return std::log (f / fLo) / std::log (fHi / fLo) * W; };
            // grid: octaves of 100 Hz .. 10 kHz
            g.setColour (juce::Colour (0xffff3b30).withAlpha (0.08f));
            for (float f : { 100.0f, 1000.0f, 10000.0f }) g.drawLine (xOf (f), 0, xOf (f), H, 1.0f);
            for (int d = 1; d < 4; ++d) g.drawLine (0, H * d / 4.0f, W, H * d / 4.0f, 1.0f);
            cornerBrackets (g, W, H, 14.0f);
            // modes: frequency, gain, bandwidth (a 2-pole resonator with the mode's decay time)
            struct Mode { float f, a, bw; } m[16]; float amax = 1.0e-4f;
            const float aex = phys::AEXP[model], damp = 1.6f * (1.0f - mat);
            for (int i = 0; i < 16; ++i)
            {
                float r = phys::RAT[model][i] * (1.0f + inh * 0.004f * (float) (i * i));
                float t60 = juce::jmax (dec * std::pow (r, -damp), 0.004f);
                m[i].f = f0 * r;
                m[i].a = std::abs (std::sin (3.14159265f * hit * (float) (i + 1))) / std::pow ((float) (i + 1), aex);
                m[i].bw = 6.9078f / (6.2831853f * t60);
                amax = juce::jmax (amax, m[i].a);
            }
            juce::Path p; const int N = juce::jmax (2, (int) W);
            for (int i = 0; i < N; ++i)
            {
                float f = fLo * std::pow (fHi / fLo, (float) i / (N - 1)), s = 0.0f;
                for (auto& q : m)
                {
                    if (q.f > 20000.0f) continue;
                    float d = (f - q.f) / juce::jmax (q.bw, 0.5f);
                    s += q.a / amax / std::sqrt (1.0f + d * d);
                }
                float db = 20.0f * std::log10 (juce::jmax (s * 3.0f, 0.003f) * mix + (1.0f - mix));
                float y = H - 6.0f - juce::jlimit (0.0f, 1.0f, (db + 18.0f) / 40.0f) * (H - 14.0f);
                if (i == 0) p.startNewSubPath (0.0f, y); else p.lineTo ((float) i * W / (N - 1), y);
            }
            glowStroke (g, p, on ? juce::Colour (0xffff3b30) : juce::Colour (0xffb4aaa5).withAlpha (0.45f), 2.5f, on);
            g.setColour (juce::Colour (0xffffc8be).withAlpha (0.55f)); g.setFont (mono (8.5f, false));
            g.drawText ("modes tuned to A3 (220 Hz) + Tune", getLocalBounds().reduced (8, 4), juce::Justification::topRight);
        }
        displayBorder (g, box);
    }

    // =============================================================== TableDisplay
    TableDisplay::TableDisplay (Ctx& c, SoundMemory& m, int osc, bool filter) : ctx (c), mem (m), o (osc), isFilter (filter) { ctx.addListener (this); mem.addChangeListener (this); setInterceptsMouseClicks (false, false); }
    TableDisplay::~TableDisplay() { mem.removeChangeListener (this); ctx.removeListener (this); }

    void TableDisplay::paramChanged (int num, float)
    {
        int k = num - oscId (o, 0);
        if (k == oscKey (isFilter ? "wfpos" : "wdpos") || k == oscKey (isFilter ? "ftype" : "dtype")) repaint();
    }

    void TableDisplay::paint (juce::Graphics& g)
    {
        auto all = getLocalBounds().toFloat();
        auto box = all.withTrimmedBottom ((float) infoH);
        displayBox (g, box);
        auto* sl = mem.get (isFilter ? SoundMemory::FilterTable : SoundMemory::ShaperTable, o);
        const std::vector<float>* data = sl ? &sl->data : nullptr;
        const int nF = data ? juce::jlimit (1, 64, (int) data->size() / 512) : 16;
        const float pos = juce::jlimit (0.0f, 1.0f, ctx.get (oscId (o, oscKey (isFilter ? "wfpos" : "wdpos"))));
        const bool on = juce::roundToInt (ctx.get (oscId (o, oscKey (isFilter ? "ftype" : "dtype")))) >= (isFilter ? 30 : 7);
        {
            juce::Graphics::ScopedSaveState ss (g);
            g.reduceClipRegion (box.toNearestInt());
            const float W = box.getWidth(), H = box.getHeight();
            const float dx = W * 0.16f, dy = H * 0.42f, pw = W - dx - 6.0f, ph = H - dy - 8.0f;
            auto at = [&] (int f, int i) { return data ? juce::jlimit (-1.0f, 1.0f, (*data)[(size_t) (f * 512 + i)]) : oscmodel::tblDefault (isFilter, f, i); };
            auto curve = [&] (std::function<float (int)> v, float t)
            {
                juce::Path p; const float ox = 3.0f + dx * t, oy = 4.0f + dy * (1.0f - t);
                for (int i = 0; i < 128; ++i)
                {
                    float x = ox + pw * (float) i / 127.0f, y = oy + ph * (0.5f - v (juce::jmin (511, juce::roundToInt ((float) i * 511.0f / 127.0f))) * 0.5f);
                    if (i == 0) p.startNewSubPath (x, y); else p.lineTo (x, y);
                }
                return p;
            };
            const int show = juce::jmin (nF, 24);
            for (int k = show - 1; k >= 0; --k)
            {
                int f = show == 1 ? 0 : juce::roundToInt ((float) k * (float) (nF - 1) / (float) (show - 1));
                float t = nF == 1 ? 0.0f : (float) f / (float) (nF - 1);
                auto col = on ? juce::Colour (0xffff7864).withAlpha (0.18f + 0.30f * (1.0f - (float) k / (float) show)) : juce::Colour (0xffa0968f).withAlpha (0.22f);
                g.setColour (col); g.strokePath (curve ([&] (int i) { return at (f, i); }, t), juce::PathStrokeType (1.0f));
            }
            float cur[512]; oscmodel::tblFrame (data, isFilter, pos, cur);
            glowStroke (g, curve ([&] (int i) { return cur[i]; }, pos), on ? juce::Colour (0xffff3b30) : juce::Colour (0xffc8beb9).withAlpha (0.6f), 2.5f, on);
            cornerBrackets (g, W, H, 14.0f);
        }
        displayBorder (g, box);
        g.setColour (dim); g.setFont (mono (8.0f, false));
        juce::String t = (sl ? sl->name : juce::String ("BUILT-IN TABLE")).toUpperCase() + " / FRAME " + juce::String (pos * (float) (nF - 1) + 1.0f, 1) + " OF " + juce::String (nF) + (on ? "" : " / NOT ACTIVE");
        g.drawText (t, all.withTrimmedTop (box.getHeight() + 2.0f).toNearestInt(), juce::Justification::centredLeft, true);
    }
}
