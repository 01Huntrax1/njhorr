#include "NjoLfoTable.h"
#include <cmath>
#include <juce_audio_formats/juce_audio_formats.h>

namespace njo
{
    struct LfoTables::Impl
    {
        Ctx* ctx = nullptr;
        std::vector<std::vector<float>> fr[10];
        bool mod[10] = {};
        double lastSend = 0;
    };

    static int lim (int i) { return juce::jlimit (0, 9, i); }

    std::vector<float> LfoTables::defaultFrame (int kind)
    {
        std::vector<float> d (points);
        for (int i = 0; i < points; ++i)
        {
            float p = (float) i / points;
            d[(size_t) i] = kind == 0 ? std::sin (6.2831853f * p) : kind == 1 ? 4.0f * std::abs (p - 0.5f) - 1.0f : kind == 2 ? 2.0f * p - 1.0f : kind == 3 ? (p < 0.5f ? 1.0f : -1.0f) : (p < 0.25f ? 1.0f : -1.0f);
        }
        return d;
    }

    static void defaults (std::vector<std::vector<float>>& f) { f.clear(); for (int k = 0; k < 5; ++k) f.push_back (LfoTables::defaultFrame (k)); }

    LfoTables::LfoTables (Ctx& c) : impl (new Impl)
    {
        impl->ctx = &c;
        for (auto& f : impl->fr) defaults (f);
        fromVar (c.be.getStored ("njo.lfowt"));
    }

    // averages / interpolates one cycle of n samples down (or up) to 256 points
    static void resampleCycle (const float* x, int n, float* out)
    {
        const int P = LfoTables::points;
        for (int i = 0; i < P; ++i)
        {
            if (n >= P)
            {
                // box filter centred on point i (cyclic), so the cycle is not shifted by half a point
                double a = ((double) i - 0.5) * n / P, b = ((double) i + 0.5) * n / P, s = 0;
                for (int k = (int) std::floor (a); k < (int) std::ceil (b); ++k)
                    s += (double) x[((k % n) + n) % n] * (juce::jmin (b, (double) k + 1) - juce::jmax (a, (double) k));   // weight = overlap of sample k with [a, b)
                out[i] = (float) (s / (b - a));
            }
            else
            {
                double pos = (double) i * n / P; int k = (int) pos; double f = pos - k;
                out[i] = (float) (x[k % n] * (1.0 - f) + x[(k + 1) % n] * f);
            }
        }
    }

    bool LfoTables::importFile (int l, const juce::File& file, juce::String& msg)
    {
        juce::AudioFormatManager fm; fm.registerBasicFormats();
        std::unique_ptr<juce::AudioFormatReader> r (fm.createReaderFor (file));
        if (r == nullptr || r->lengthInSamples < 8) { msg = "CANNOT READ " + file.getFileName().toUpperCase(); return false; }
        const int len = (int) juce::jmin<juce::int64> (r->lengthInSamples, 4 * 1024 * 1024);
        juce::AudioBuffer<float> buf (1, len);
        if (! r->read (&buf, 0, len, 0, true, false)) { msg = "CANNOT READ " + file.getFileName().toUpperCase(); return false; }
        const float* x = buf.getReadPointer (0);

        int size = len, frames = 1;   // wavetable files: frames of 2048 / 1024 / 512 / 256 samples; anything else is one cycle
        for (int s : { 2048, 1024, 512, 256 }) if (len >= s && len % s == 0) { size = s; frames = len / s; break; }

        const int use = juce::jmin (frames, maxFrames);
        std::vector<std::vector<float>> out ((size_t) use, std::vector<float> ((size_t) points));
        float peak = 0.0f;
        for (int k = 0; k < use; ++k)
        {
            int src = use == 1 ? 0 : (int) std::lround ((double) k * (frames - 1) / (use - 1));
            resampleCycle (x + (size_t) src * size, size, out[(size_t) k].data());
            for (float v : out[(size_t) k]) peak = juce::jmax (peak, std::abs (v));
        }
        const float g = peak > 1.0e-4f ? 1.0f / peak : 1.0f;
        setCount (l, use);
        for (int k = 0; k < use; ++k)
        {
            auto& fr = frame (l, k);
            for (int i = 0; i < points; ++i) fr[(size_t) i] = juce::jlimit (-1.0f, 1.0f, out[(size_t) k][(size_t) i] * g);
        }
        commitAll (l);
        msg = "IMPORTED " + file.getFileName().toUpperCase() + " (" + juce::String (use) + (use == 1 ? " FRAME)" : " FRAMES)");
        return true;
    }

    int LfoTables::count (int l) const { return (int) impl->fr[lim (l)].size(); }
    std::vector<float>& LfoTables::frame (int l, int f) { auto& v = impl->fr[lim (l)]; return v[(size_t) juce::jlimit (0, (int) v.size() - 1, f)]; }
    bool LfoTables::modified (int l) const { return impl->mod[lim (l)]; }

    void LfoTables::setCount (int l, int n)
    {
        l = lim (l); n = juce::jlimit (1, maxFrames, n); auto& v = impl->fr[l];
        while ((int) v.size() > n) v.pop_back();
        while ((int) v.size() < n) v.push_back (v.back());
        impl->mod[l] = true;
    }

    void LfoTables::insertCopy (int l, int after)
    {
        l = lim (l); auto& v = impl->fr[l];
        if ((int) v.size() >= maxFrames) return;
        auto c = v[(size_t) juce::jlimit (0, (int) v.size() - 1, after)];
        v.insert (v.begin() + juce::jlimit (0, (int) v.size() - 1, after) + 1, c);
        impl->mod[l] = true;
    }

    void LfoTables::erase (int l, int f)
    {
        l = lim (l); auto& v = impl->fr[l];
        if (v.size() <= 1) return;
        v.erase (v.begin() + juce::jlimit (0, (int) v.size() - 1, f));
        impl->mod[l] = true;
    }

    void LfoTables::reset (int l)
    {
        l = lim (l); defaults (impl->fr[l]); impl->mod[l] = false;
        commitAll (l);
        impl->mod[l] = false;
        impl->ctx->be.setStored ("njo.lfowt", toVar());
    }

    static void sendFrame (LfoTables& t, Ctx& c, int l, int f)
    {
        juce::Array<juce::var> d;
        for (float v : t.frame (l, f)) d.add ((double) v);
        auto* o = new juce::DynamicObject();
        o->setProperty ("lfo", l); o->setProperty ("frame", f); o->setProperty ("frames", t.count (l)); o->setProperty ("data", juce::var (d));
        c.be.sendEvent ("lfoTableLoad", juce::var (o));
    }

    void LfoTables::commitFrame (int l, int f, bool final)
    {
        l = lim (l); impl->mod[l] = true;
        double now = juce::Time::getMillisecondCounterHiRes();
        if (final || now - impl->lastSend > 40.0) { impl->lastSend = now; sendFrame (*this, *impl->ctx, l, f); }
        if (final) impl->ctx->be.setStored ("njo.lfowt", toVar());
    }

    void LfoTables::commitAll (int l)
    {
        l = lim (l); impl->mod[l] = true;
        for (int f = 0; f < count (l); ++f) sendFrame (*this, *impl->ctx, l, f);
        impl->ctx->be.setStored ("njo.lfowt", toVar());
    }

    void LfoTables::sendAll()
    {
        for (int l = 0; l < 10; ++l) if (impl->mod[l]) for (int f = 0; f < count (l); ++f) sendFrame (*this, *impl->ctx, l, f);
    }

    juce::var LfoTables::toVar() const
    {
        juce::Array<juce::var> out;
        for (int l = 0; l < 10; ++l)
        {
            if (! impl->mod[l]) { out.add (juce::var()); continue; }
            juce::Array<juce::var> frames;
            for (auto& f : impl->fr[l])
            {
                std::vector<juce::int16> q (points);
                for (int i = 0; i < points; ++i) q[(size_t) i] = (juce::int16) juce::roundToInt (juce::jlimit (-1.0f, 1.0f, f[(size_t) i]) * 32000.0f);
                frames.add (juce::Base64::toBase64 (q.data(), q.size() * sizeof (juce::int16)));
            }
            out.add (juce::var (frames));
        }
        return juce::var (out);
    }

    void LfoTables::fromVar (const juce::var& v)
    {
        for (int l = 0; l < 10; ++l)
        {
            defaults (impl->fr[l]); impl->mod[l] = false;
            auto* arr = v.isArray() ? v[l].getArray() : nullptr;
            if (arr == nullptr || arr->isEmpty()) continue;
            std::vector<std::vector<float>> fs;
            for (auto& s : *arr)
            {
                juce::MemoryOutputStream mo; if (! juce::Base64::convertFromBase64 (mo, s.toString()) || mo.getDataSize() != (size_t) points * sizeof (juce::int16)) { fs.clear(); break; }
                auto* q = static_cast<const juce::int16*> (mo.getData()); std::vector<float> d (points);
                for (int i = 0; i < points; ++i) d[(size_t) i] = (float) q[i] / 32000.0f;
                fs.push_back (std::move (d)); if ((int) fs.size() >= maxFrames) break;
            }
            if (fs.empty()) continue;
            impl->fr[l] = std::move (fs); impl->mod[l] = true;
        }
        sendAll();
    }
}
