#include "OscDisplays.h"
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

            const int type = juce::jlimit (0, 2, juce::roundToInt (pv ("type")));
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

    // =============================================================== FilterDisplay
    FilterDisplay::FilterDisplay (Ctx& c, int osc) : ctx (c), o (osc) { ctx.addListener (this); setInterceptsMouseClicks (false, false); }
    FilterDisplay::~FilterDisplay() { ctx.removeListener (this); }

    void FilterDisplay::paramChanged (int num, float)
    {
        int k = num - oscId (o, 0);
        if (k >= oscKey ("fon") && k <= oscKey ("fkey")) repaint();
    }

    void FilterDisplay::paint (juce::Graphics& g)
    {
        auto box = getLocalBounds().toFloat();
        displayBox (g, box);
        const float W = 600.0f, H = 200.0f;
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
            auto curve = [&] (double sweep, bool fill, juce::Colour col, float lw, bool glow)
            {
                juce::Path p;
                for (int i = 0; i < N; ++i)
                {
                    double f = 20.0 * std::pow (1000.0, (double) i / (N - 1));
                    double mag = std::abs (oscmodel::filterH (ft, fc, res, f, sweep));
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
}
