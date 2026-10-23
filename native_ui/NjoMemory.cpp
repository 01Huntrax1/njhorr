// Sample / wavetable memory: decoding (JUCE formats + AU + headerless 16 bit dumps), persistence in the instance's stored state
// (keys njo.mem.osc{o}.{wt|sm} = { name, total, pcm16 (base64 LE int16) }) and streaming into the DSP banks in 256 sample chunks.
#include "NjoMemory.h"
#include <juce_audio_formats/juce_audio_formats.h>
#include <cmath>

namespace njo
{
    namespace
    {
        constexpr double kRate = 48000.0;          // the memories are kept at this rate (the web UI used the AudioContext rate)
        constexpr int kChunksPerTick = 6, kTickMs = 6, kStaggerMs = 150;

        constexpr int kTblFl = 512, kTblMaxFr = 64;   // Wavefilter / Wavedistortion tables: 512 points per frame, up to 64 frames
        bool isTable (SoundMemory::Kind k) { return k == SoundMemory::FilterTable || k == SoundMemory::ShaperTable; }
        juce::String keyFor (SoundMemory::Kind k, int o)
        {
            static const char* ext[] = { ".wt", ".sm", ".ft", ".sh" };
            return "njo.mem.osc" + juce::String (o) + ext[(int) k];
        }
        const char* endpointFor (SoundMemory::Kind k) { return isTable (k) ? "tblLoad" : k == SoundMemory::Wavetable ? "wtBankLoad" : "smpBankLoad"; }
        int bankFor (SoundMemory::Kind k, int o) { return k == SoundMemory::ShaperTable ? OSC_N + o : o; }

        // a wavetable file cut into frames (4096 / 2048 samples; shorter files are one frame), every frame reduced to 512 points
        std::vector<float> tableFromMono (const std::vector<float>& mono)
        {
            const int n = (int) mono.size();
            const int fl = n % 4096 == 0 ? 4096 : (n >= 2048 ? 2048 : n);
            const int nF = juce::jmax (1, n / fl), take = juce::jmin (nF, kTblMaxFr);
            std::vector<float> out ((size_t) (take * kTblFl));
            for (int t = 0; t < take; ++t)
            {
                int f = take == 1 ? 0 : (int) std::lround ((double) t * (nF - 1) / (take - 1));
                const int b = f * fl;
                for (int i = 0; i < kTblFl; ++i)
                {
                    double x = (double) i * (fl - 1) / (kTblFl - 1);
                    int i0 = (int) x, i1 = juce::jmin (i0 + 1, fl - 1); float xf = (float) (x - i0);
                    out[(size_t) (t * kTblFl + i)] = mono[(size_t) (b + i0)] + (mono[(size_t) (b + i1)] - mono[(size_t) (b + i0)]) * xf;
                }
            }
            return out;
        }

        juce::var encodeMem (const SoundMemory::Slot& s)
        {
            juce::MemoryBlock mb (s.data.size() * 2);
            auto* p = (juce::uint8*) mb.getData();
            for (size_t i = 0; i < s.data.size(); ++i)
            {
                int v = juce::roundToInt (juce::jlimit (-1.0f, 1.0f, s.data[i]) * 32767.0f);
                p[i * 2] = (juce::uint8) (v & 255); p[i * 2 + 1] = (juce::uint8) ((v >> 8) & 255);
            }
            auto* o = new juce::DynamicObject();
            o->setProperty ("name", s.name);
            o->setProperty ("total", (int) s.data.size());
            o->setProperty ("pcm16", juce::Base64::toBase64 (mb.getData(), mb.getSize()));
            if (s.libId.isNotEmpty()) o->setProperty ("lib", s.libId);
            return juce::var (o);
        }

        bool decodeMem (const juce::var& v, const juce::String& fallbackName, SoundMemory::Slot& out)
        {
            if (! v.isObject()) return false;
            auto pcm = v.getProperty ("pcm16", {}).toString();
            int total = (int) v.getProperty ("total", 0);
            if (pcm.isEmpty() || total <= 0) return false;
            juce::MemoryOutputStream mo;
            if (! juce::Base64::convertFromBase64 (mo, pcm)) return false;
            int n = juce::jmin (total, (int) (mo.getDataSize() >> 1));
            if (n <= 0) return false;
            auto* p = (const juce::uint8*) mo.getData();
            out.data.resize ((size_t) n);
            for (int i = 0; i < n; ++i)
            {
                int s = p[i * 2] | (p[i * 2 + 1] << 8);
                if (s & 0x8000) s -= 0x10000;
                out.data[(size_t) i] = (float) s / 32767.0f;
            }
            auto nm = v.getProperty ("name", {}).toString();
            out.name = nm.isNotEmpty() ? nm : fallbackName;
            out.libId = v.getProperty ("lib", {}).toString();
            return true;
        }

        // Sun / NeXT .au (PCM 8 / 16 / 24 / 32, float, mu-law)
        bool decodeAu (const juce::MemoryBlock& mb, std::vector<std::vector<float>>& ch, double& rate, int maxFrames)
        {
            auto* d = (const juce::uint8*) mb.getData(); size_t n = mb.getSize();
            if (n < 24 || d[0] != '.' || d[1] != 's' || d[2] != 'n' || d[3] != 'd') return false;
            auto be32 = [&] (size_t o) { return (juce::uint32) d[o] << 24 | (juce::uint32) d[o + 1] << 16 | (juce::uint32) d[o + 2] << 8 | d[o + 3]; };
            size_t off = be32 (4); juce::uint32 size = be32 (8), enc = be32 (12); rate = be32 (16); int nch = (int) be32 (20);
            if (nch < 1 || nch > 16 || off > n) return false;
            size_t len = (size == 0xffffffffu) ? n - off : juce::jmin ((size_t) size, n - off);
            int bps = enc == 1 ? 1 : enc == 2 ? 1 : enc == 3 ? 2 : enc == 4 ? 3 : enc == 5 ? 4 : enc == 6 ? 4 : enc == 7 ? 8 : 0;
            if (bps == 0) return false;
            size_t frames = juce::jmin (len / (size_t) (bps * nch), (size_t) maxFrames);
            ch.assign ((size_t) nch, std::vector<float> (frames));
            for (size_t f = 0; f < frames; ++f)
                for (int c = 0; c < nch; ++c)
                {
                    const juce::uint8* p = d + off + (f * (size_t) nch + (size_t) c) * (size_t) bps; float v = 0;
                    switch (enc)
                    {
                        case 1: { int u = ~p[0] & 0xff; int sgn = u & 0x80, ex = (u >> 4) & 7, m = u & 15; int s = ((m << 3) + 0x84) << ex; s -= 0x84; v = (float) (sgn ? -s : s) / 32768.0f; break; }
                        case 2: v = (float) (signed char) p[0] / 128.0f; break;
                        case 3: v = (float) (short) (p[0] << 8 | p[1]) / 32768.0f; break;
                        case 4: { int s = p[0] << 16 | p[1] << 8 | p[2]; if (s & 0x800000) s -= 0x1000000; v = (float) s / 8388608.0f; break; }
                        case 5: v = (float) (int) (p[0] << 24 | p[1] << 16 | p[2] << 8 | p[3]) / 2147483648.0f; break;
                        case 6: { juce::uint32 u = (juce::uint32) p[0] << 24 | p[1] << 16 | p[2] << 8 | p[3]; float x; memcpy (&x, &u, 4); v = x; break; }
                        case 7: { juce::uint64 u = 0; for (int i = 0; i < 8; ++i) u = u << 8 | p[i]; double x; memcpy (&x, &u, 8); v = (float) x; break; }
                    }
                    ch[(size_t) c][f] = v;
                }
            return true;
        }

        struct Decoded { std::vector<float> mono; bool ok = false; juce::String name; };

        // more than 128 frames: thinned out evenly (first and last frame are kept)
        std::vector<float> trimWavetable (std::vector<float> x)
        {
            const int n = (int) x.size();
            const int fl = n % 4096 == 0 ? 4096 : (n >= 2048 ? 2048 : 0);
            if (fl == 0) return x;
            const int nF = n / fl;
            if (nF <= MAX_WT_FRAMES) return x;
            std::vector<float> out ((size_t) (MAX_WT_FRAMES * fl));
            for (int t = 0; t < MAX_WT_FRAMES; ++t)
            {
                int src = (int) std::lround ((double) t * (nF - 1) / (MAX_WT_FRAMES - 1));
                std::copy (x.begin() + (size_t) src * (size_t) fl, x.begin() + (size_t) (src + 1) * (size_t) fl, out.begin() + (size_t) t * (size_t) fl);
            }
            return out;
        }

        // Vital wavetable (.vitaltable, JSON): keyframes of the first "Wave Source" component (2048 float samples each, base64),
        // interpolated linearly over 128 frames (Vital positions run 0..255). Other modifier components are not applied.
        bool decodeVitalTable (const juce::File& file, Decoded& r)
        {
            auto v = juce::JSON::parse (file.loadFileAsString());
            auto* groups = v["groups"].getArray();
            if (groups == nullptr) return false;
            struct Kf { double pos; std::vector<float> w; };
            std::vector<Kf> kfs;
            for (auto& g : *groups)
            {
                auto* comps = g["components"].getArray();
                if (comps == nullptr) continue;
                for (auto& c : *comps)
                {
                    auto* ks = c["keyframes"].getArray();
                    if (! kfs.empty() || c["type"].toString() != "Wave Source" || ks == nullptr) continue;
                    for (auto& k : *ks)
                    {
                        juce::MemoryOutputStream mo;
                        if (! juce::Base64::convertFromBase64 (mo, k["wave_data"].toString())) continue;
                        Kf kf { (double) k["position"], std::vector<float> (2048, 0.0f) };
                        auto* p = (const juce::uint8*) mo.getData();
                        size_t n = juce::jmin ((size_t) 2048, mo.getDataSize() / 4);
                        for (size_t i = 0; i < n; ++i) { juce::uint32 u = (juce::uint32) p[i * 4] | (juce::uint32) p[i * 4 + 1] << 8 | (juce::uint32) p[i * 4 + 2] << 16 | (juce::uint32) p[i * 4 + 3] << 24; float f; memcpy (&f, &u, 4); kf.w[i] = f; }
                        kfs.push_back (std::move (kf));
                    }
                }
            }
            if (kfs.empty()) return false;
            std::stable_sort (kfs.begin(), kfs.end(), [] (const Kf& a, const Kf& b) { return a.pos < b.pos; });
            const int nOut = kfs.size() == 1 ? 1 : MAX_WT_FRAMES;
            std::vector<float> out ((size_t) nOut * 2048);
            for (int t = 0; t < nOut; ++t)
            {
                double p = nOut == 1 ? 0.0 : t * 255.0 / (MAX_WT_FRAMES - 1);
                const Kf* a = &kfs.front(); const Kf* b = &kfs.back();
                for (auto& k : kfs) if (k.pos <= p) a = &k;
                for (auto it = kfs.rbegin(); it != kfs.rend(); ++it) if (it->pos >= p) b = &*it;
                float f = b->pos > a->pos ? (float) ((p - a->pos) / (b->pos - a->pos)) : 0.0f;
                for (int i = 0; i < 2048; ++i) out[(size_t) t * 2048 + (size_t) i] = a->w[(size_t) i] + (b->w[(size_t) i] - a->w[(size_t) i]) * f;
            }
            float peak = 0; for (float x : out) peak = juce::jmax (peak, std::abs (x));
            float g = peak > 0.0001f ? 0.9f / peak : 1.0f;
            for (auto& x : out) x *= g;
            r.mono = std::move (out); r.ok = true; r.name = v["name"].toString();
            return true;
        }

        Decoded decodeAny (const juce::File& file, bool wavetable)
        {
            Decoded r;
            auto startsWithBrace = [&]
            {
                juce::FileInputStream in (file); char c = 0;
                return in.openedOk() && in.read (&c, 1) == 1 && c == '{';
            };
            if (wavetable && (file.hasFileExtension ("vitaltable") || startsWithBrace()))
                if (decodeVitalTable (file, r)) return r;
            const int maxIn = (wavetable ? MAX_WT : MAX_SMP) * 4;
            std::vector<std::vector<float>> ch; double rate = 0;

            juce::AudioFormatManager fm; fm.registerBasicFormats();
            std::unique_ptr<juce::AudioFormatReader> rd (fm.createReaderFor (file));
            if (rd != nullptr && rd->numChannels > 0 && rd->lengthInSamples > 0)
            {
                int frames = (int) juce::jmin ((juce::int64) maxIn, rd->lengthInSamples);
                int nch = (int) juce::jmin ((unsigned) 16, rd->numChannels);
                juce::AudioBuffer<float> buf (nch, frames);
                if (rd->read (&buf, 0, frames, 0, true, nch > 1))
                {
                    for (int c = 0; c < nch; ++c) ch.emplace_back (buf.getReadPointer (c), buf.getReadPointer (c) + frames);
                    rate = rd->sampleRate;
                }
            }
            if (ch.empty())
            {
                juce::MemoryBlock mb; file.loadFileAsData (mb);
                if (mb.getSize() > 0 && decodeAu (mb, ch, rate, maxIn)) {}
                else
                {
                    ch.clear();
                    auto ext = file.getFileExtension().toLowerCase();
                    if (ext.isNotEmpty() && juce::StringArray { ".raw", ".pcm", ".sam", ".smp", ".dat", ".bin", ".sd", ".s16" }.contains (ext) && mb.getSize() >= 2)
                    {
                        auto* p = (const juce::uint8*) mb.getData();
                        size_t n = juce::jmin ((size_t) maxIn, mb.getSize() / 2);
                        std::vector<float> m (n);
                        for (size_t i = 0; i < n; ++i) m[i] = (float) (short) (p[i * 2] | p[i * 2 + 1] << 8) / 32768.0f;
                        ch.push_back (std::move (m)); rate = kRate;
                    }
                }
            }
            if (ch.empty() || ch[0].empty()) return r;

            size_t frames = ch[0].size();
            std::vector<float> mono (frames, 0.0f);
            for (auto& c : ch) for (size_t i = 0; i < frames; ++i) mono[i] += c[i] / (float) ch.size();

            // samples are converted to the host rate; wavetables are not (their frames are single cycles of N samples)
            if (! wavetable && rate > 0 && std::abs (rate - kRate) > 0.5)
            {
                double ratio = rate / kRate;
                int outN = juce::jmax (1, (int) std::floor ((double) frames / ratio));
                std::vector<float> out ((size_t) outN);
                juce::LagrangeInterpolator li;
                li.process (ratio, mono.data(), out.data(), outN);
                mono.swap (out);
            }
            if (wavetable) mono = trimWavetable (std::move (mono));
            const int cap = wavetable ? MAX_WT : MAX_SMP;
            if ((int) mono.size() > cap) mono.resize ((size_t) cap);
            float peak = 0; for (float v : mono) peak = juce::jmax (peak, std::abs (v));
            float g = peak > 0.0001f ? 0.9f / peak : 1.0f;
            for (auto& v : mono) v *= g;
            r.mono = std::move (mono); r.ok = ! r.mono.empty();
            return r;
        }
    }

    struct SoundMemory::Impl : private juce::Timer
    {
        struct Stream { Kind kind; int osc; std::shared_ptr<std::vector<float>> data; size_t offset = 0; juce::int64 startAt = 0; };

        Impl (SoundMemory& o, Ctx& c) : owner (o), ctx (c) {}
        ~Impl() override { stopTimer(); }

        SoundMemory& owner; Ctx& ctx;
        std::unique_ptr<Slot> slots[4][OSC_N];
        std::vector<Stream> streams;

        void cancel (Kind k, int o)
        {
            streams.erase (std::remove_if (streams.begin(), streams.end(), [&] (const Stream& s) { return s.kind == k && s.osc == o; }), streams.end());
        }
        void startStream (Kind k, int o, int delayMs)
        {
            cancel (k, o);
            auto& sl = slots[k][o];
            if (! sl) return;
            Stream s { k, o, std::make_shared<std::vector<float>> (sl->data), 0, juce::Time::getMillisecondCounter() + (juce::int64) delayMs };
            streams.push_back (std::move (s));
            if (! isTimerRunning()) startTimer (kTickMs);
        }
        void sendChunk (Kind k, int o, const std::vector<float>& d, size_t offset, size_t total)
        {
            auto* ev = new juce::DynamicObject();
            int count = (int) juce::jmin ((size_t) CHUNK, total - offset);
            juce::Array<juce::var> arr; arr.ensureStorageAllocated (CHUNK);
            for (int i = 0; i < CHUNK; ++i) arr.add (i < count ? (double) d[offset + (size_t) i] : 0.0);
            ev->setProperty ("bank", bankFor (k, o)); ev->setProperty ("offset", (int) offset); ev->setProperty ("count", count);
            ev->setProperty ("total", (int) total); ev->setProperty ("data", juce::var (arr));
            ctx.be.sendEvent (endpointFor (k), juce::var (ev));
        }
        void timerCallback() override
        {
            auto now = (juce::int64) juce::Time::getMillisecondCounter();
            for (auto& s : streams)
            {
                if (s.startAt > now) continue;
                for (int i = 0; i < kChunksPerTick && s.offset < s.data->size(); ++i)
                { sendChunk (s.kind, s.osc, *s.data, s.offset, s.data->size()); s.offset += (size_t) CHUNK; }
            }
            streams.erase (std::remove_if (streams.begin(), streams.end(), [] (const Stream& s) { return s.offset >= s.data->size(); }), streams.end());
            if (streams.empty()) stopTimer();
        }
        void persist (Kind k, int o)
        {
            auto& sl = slots[k][o];
            ctx.be.setStored (keyFor (k, o), sl ? encodeMem (*sl) : juce::var());
        }
    };

    SoundMemory::SoundMemory (Ctx& c) : impl (new Impl (*this, c))
    {
        // the saved copies are available to the displays at once; restore() streams them to the DSP
        for (int k = 0; k < 4; ++k)
            for (int o = 0; o < OSC_N; ++o)
            {
                auto s = std::make_unique<Slot>();
                if (decodeMem (c.be.getStored (keyFor ((Kind) k, o)), k == Sample ? "SAMPLE" : "TABLE", *s)) impl->slots[k][o] = std::move (s);
            }
    }
    SoundMemory::~SoundMemory() = default;

    const SoundMemory::Slot* SoundMemory::get (Kind k, int o) const
    {
        if (o < 0 || o >= OSC_N) return nullptr;
        return impl->slots[k][o].get();
    }

    void SoundMemory::set (Kind k, int o, const juce::String& name, const juce::String& libId, std::vector<float> data)
    {
        if (o < 0 || o >= OSC_N) return;
        if (data.empty()) { clear (k, o); return; }
        const int cap = isTable (k) ? kTblMaxFr * kTblFl : k == Wavetable ? MAX_WT : MAX_SMP;
        if ((int) data.size() > cap) data.resize ((size_t) cap);
        auto s = std::make_unique<Slot>();
        s->name = name; s->libId = libId; s->data = std::move (data);
        impl->slots[k][o] = std::move (s);
        impl->persist (k, o);
        impl->startStream (k, o, 0);
        sendChangeMessage();
    }

    void SoundMemory::load (Kind k, int o, const juce::File& f, std::function<void (bool, const juce::String&)> done)
    {
        auto dec = decodeAny (f, k != Sample);
        if (dec.ok && isTable (k)) dec.mono = tableFromMono (dec.mono);
        if (! dec.ok)
        {
            impl->ctx.status ("UNSUPPORTED FILE");
            if (done) done (false, "UNSUPPORTED FILE");
            return;
        }
        auto name = (dec.name.isNotEmpty() ? dec.name : f.getFileNameWithoutExtension()).substring (0, 14).toUpperCase();
        if (name.isEmpty()) name = k == Sample ? "SAMPLE" : "TABLE";
        set (k, o, name, {}, std::move (dec.mono));
        impl->ctx.status ("LOADED " + name);
        if (done) done (true, "LOADED " + name);
    }

    void SoundMemory::clear (Kind k, int o)
    {
        if (o < 0 || o >= OSC_N) return;
        impl->cancel (k, o);
        impl->slots[k][o].reset();
        auto* ev = new juce::DynamicObject();
        juce::Array<juce::var> arr; for (int i = 0; i < CHUNK; ++i) arr.add (0.0);
        ev->setProperty ("bank", bankFor (k, o)); ev->setProperty ("offset", 0); ev->setProperty ("count", 0); ev->setProperty ("total", 0); ev->setProperty ("data", juce::var (arr));
        impl->ctx.be.sendEvent (endpointFor (k), juce::var (ev));
        impl->persist (k, o);
        if (! isTable (k)) impl->ctx.status ("OSC " + juce::String (o + 1) + " CLEARED");
        sendChangeMessage();
    }

    void SoundMemory::restore()
    {
        int n = 0;
        for (int k = 0; k < 4; ++k)
            for (int o = 0; o < OSC_N; ++o)
                if (impl->slots[k][o]) impl->startStream ((Kind) k, o, kStaggerMs * n++);
    }

    juce::String SoundMemory::fileWildcard()
    {
        return "*.vitaltable;*.wav;*.wave;*.bwf;*.aif;*.aiff;*.aifc;*.flac;*.ogg;*.oga;*.mp3;*.au;*.snd;*.w64;*.raw;*.pcm;*.sam;*.smp;*.dat;*.bin;*.sd;*.s16";
    }
}
