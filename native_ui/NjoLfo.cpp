// The drawn LFO shapes: point store, 256 value tables for the DSP and the stored state "njo.lfo" (same format as the JS UI).
#include "NjoLfo.h"
#include <cmath>

namespace njo
{
    struct LfoShapes::Impl
    {
        Ctx* ctx = nullptr;
        std::vector<LfoPoint> pts[10];
        bool has[10] = {};
        double lastSend = 0;
    };

    static int lim (int i) { return juce::jlimit (0, 9, i); }

    LfoShapes::LfoShapes (Ctx& c) : impl (new Impl)
    {
        impl->ctx = &c;
        fromVar (c.be.getStored ("njo.lfo"));
    }

    std::vector<LfoPoint>& LfoShapes::points (int i)
    {
        i = lim (i);
        if (! impl->has[i])
        {
            int w = juce::roundToInt (impl->ctx->get (lfoWaveParam (i)));
            impl->pts[i] = builtin (w >= LFO_DRAWN ? 0 : w);
            impl->has[i] = true;
        }
        return impl->pts[i];
    }

    bool LfoShapes::isDrawn (int i) const { return impl->has[lim (i)]; }

    void LfoShapes::setPoints (int i, std::vector<LfoPoint> p) { i = lim (i); impl->pts[i] = std::move (p); impl->has[i] = true; }
    void LfoShapes::reset (int i) { i = lim (i); impl->pts[i].clear(); impl->has[i] = false; }

    static void sendTable (LfoShapes& s, Ctx& c, int i)
    {
        auto t = LfoShapes::table (s.points (i));
        juce::Array<juce::var> d;
        for (float v : t) d.add ((double) v);
        auto* o = new juce::DynamicObject();
        o->setProperty ("lfo", i);
        o->setProperty ("data", juce::var (d));
        c.be.sendEvent ("lfoShapeLoad", juce::var (o));
    }

    void LfoShapes::commit (int i, bool final)
    {
        i = lim (i);
        auto& c = *impl->ctx;
        if (juce::roundToInt (c.get (lfoWaveParam (i))) != LFO_DRAWN) c.set (lfoWaveParam (i), (float) LFO_DRAWN);
        double now = juce::Time::getMillisecondCounterHiRes();
        if (final || now - impl->lastSend > 50.0)
        {
            impl->lastSend = now;
            sendTable (*this, c, i);
        }
        if (final) c.be.setStored ("njo.lfo", toVar());
    }

    void LfoShapes::sendAll()
    {
        for (int i = 0; i < 10; ++i) if (impl->has[i]) sendTable (*this, *impl->ctx, i);
    }

    static double rnd (double v, double k) { return std::floor (v * k + 0.5) / k; }

    juce::var LfoShapes::toVar() const
    {
        juce::Array<juce::var> out;
        for (int i = 0; i < 10; ++i)
        {
            if (! impl->has[i]) { out.add (juce::var()); continue; }
            juce::Array<juce::var> p;
            for (auto& q : impl->pts[i])
            {
                auto* o = new juce::DynamicObject();
                o->setProperty ("x", rnd (q.x, 1e4)); o->setProperty ("y", rnd (q.y, 1e4)); o->setProperty ("c", rnd (q.c, 1e3));
                p.add (juce::var (o));
            }
            out.add (juce::var (p));
        }
        return juce::var (out);
    }

    void LfoShapes::fromVar (const juce::var& v)
    {
        for (int i = 0; i < 10; ++i)
        {
            impl->pts[i].clear(); impl->has[i] = false;
            auto* arr = v.isArray() ? v[i].getArray() : nullptr;
            if (arr == nullptr || arr->size() < 2) continue;
            std::vector<LfoPoint> p; bool ok = true;
            for (auto& q : *arr)
            {
                if (! q.isObject() || ! (q["x"].isDouble() || q["x"].isInt()) || ! (q["y"].isDouble() || q["y"].isInt())) { ok = false; break; }
                p.push_back ({ juce::jlimit (0.0f, 1.0f, (float) (double) q["x"]), juce::jlimit (-1.0f, 1.0f, (float) (double) q["y"]), juce::jlimit (-1.0f, 1.0f, (float) (double) q["c"]) });
            }
            if (! ok) continue;
            impl->pts[i] = std::move (p); impl->has[i] = true;
        }
        sendAll();
    }

    float LfoShapes::curve (float y0, float y1, float c, float t)
    {
        double tt = t;
        if (c > 0.001f) tt = std::pow (tt, 1.0 + 4.0 * c);
        else if (c < -0.001f) tt = 1.0 - std::pow (1.0 - tt, 1.0 - 4.0 * c);
        return (float) (y0 + (y1 - y0) * tt);
    }

    static double curveD (double y0, double y1, double c, double t)
    {
        if (c > 0.001) t = std::pow (t, 1 + 4 * c);
        else if (c < -0.001) t = 1 - std::pow (1 - t, 1 - 4 * c);
        return y0 + (y1 - y0) * t;
    }

    static double sampleD (const std::vector<LfoPoint>& pts, double p)
    {
        p = juce::jlimit (0.0, 1.0, p);
        for (size_t i = 0; i + 1 < pts.size(); ++i)
        {
            auto& a = pts[i]; auto& b = pts[i + 1];
            if (p <= b.x || i + 2 == pts.size())
            {
                double span = (double) b.x - a.x;
                double t = span > 1e-9 ? (p - a.x) / span : 1.0;
                return curveD (a.y, b.y, a.c, juce::jlimit (0.0, 1.0, t));
            }
        }
        return pts.empty() ? 0.0 : (double) pts[0].y;
    }

    float LfoShapes::sampleAt (const std::vector<LfoPoint>& pts, float p) { return (float) sampleD (pts, p); }

    std::vector<float> LfoShapes::table (const std::vector<LfoPoint>& pts)
    {
        std::vector<float> t (256);
        for (int i = 0; i < 256; ++i) t[(size_t) i] = (float) rnd (sampleD (pts, i / 256.0), 1e5);
        return t;
    }

    std::vector<LfoPoint> LfoShapes::builtin (int w)
    {
        std::vector<LfoPoint> p;
        const float pi2 = 6.283185307179586f;
        if (w == 0) { for (int i = 0; i <= 32; ++i) p.push_back ({ i / 32.0f, (float) std::sin (2.0 * 3.141592653589793 * i / 32), 0 }); return p; }
        if (w == 1) return { { 0, 1, 0 }, { 0.5f, -1, 0 }, { 1, 1, 0 } };
        if (w == 2) return { { 0, 1, 0 }, { 0.4985f, 1, 0 }, { 0.5f, -1, 0 }, { 1, -1, 0 } };
        if (w == 3)
        {
            const float v[8] = { 0.55f, -0.4f, 0.8f, -0.75f, 0.1f, 0.9f, -0.2f, -0.9f };
            for (int i = 0; i < 8; ++i) { p.push_back ({ i / 8.0f, v[i], 0 }); p.push_back ({ (i + 1) / 8.0f - 0.0025f, v[i], 0 }); }
            p.back().x = 1;
            return p;
        }
        juce::ignoreUnused (pi2);
        if (w == 4) return { { 0, -1, 0 }, { 1, 1, 0 } };
        return { { 0, 1, 0 }, { 1, -1, 0 } };
    }
}
