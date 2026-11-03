#include "NjoSf2.h"
#include <cmath>
#include <algorithm>
#include <map>
#include <tuple>

namespace njo::sf2
{
    namespace
    {
        juce::uint32 u32 (const juce::uint8* p) { return (juce::uint32) p[0] | (juce::uint32) p[1] << 8 | (juce::uint32) p[2] << 16 | (juce::uint32) p[3] << 24; }
        int u16 (const juce::uint8* p) { return p[0] | p[1] << 8; }
        int s16 (const juce::uint8* p) { return (int) (short) (p[0] | p[1] << 8); }
        juce::String nameOf (const juce::uint8* p) { char b[21]; for (int i = 0; i < 20; ++i) b[i] = (char) p[i]; b[20] = 0; return juce::String::fromUTF8 (b).trim(); }

        // generator numbers
        enum { gStartOff = 0, gEndOff = 1, gStartLoopOff = 2, gEndLoopOff = 3, gStartCoarse = 4, gEndCoarse = 12, gPan = 17, gDelayVol = 33, gAttackVol = 34, gHoldVol = 35, gDecayVol = 36, gSustainVol = 37, gReleaseVol = 38,
               gInstrument = 41, gKeyRange = 43, gVelRange = 44, gStartLoopCoarse = 45, gAtten = 48, gEndLoopCoarse = 50, gCoarseTune = 51, gFineTune = 52, gSampleId = 53, gSampleModes = 54, gScaleTuning = 56, gRootKey = 58 };

        double tcToMs (int tc) { return 1000.0 * std::pow (2.0, tc / 1200.0); }
    }

    bool File::open (const juce::File& f, juce::String& error)
    {
        file = f; presetList.clear(); presetBag.clear(); instBag.clear(); pbag.clear(); ibag.clear(); pgen.clear(); igen.clear(); shdr.clear(); smplOffset = smplSize = 0;
        std::unique_ptr<juce::FileInputStream> in (f.createInputStream());
        if (in == nullptr) { error = "CANNOT READ THE FILE"; return false; }
        juce::uint8 h[12];
        if (in->read (h, 12) != 12 || std::memcmp (h, "RIFF", 4) != 0 || std::memcmp (h + 8, "sfbk", 4) != 0) { error = "NOT A SOUNDFONT FILE"; return false; }
        const juce::int64 total = in->getTotalLength();
        std::map<juce::String, std::vector<juce::uint8>> pdta;
        juce::int64 pos = 12; bool compressed = false;
        while (pos + 8 <= total)
        {
            juce::uint8 ch[12]; in->setPosition (pos);
            if (in->read (ch, 8) != 8) break;
            juce::uint32 size = u32 (ch + 4); juce::String id = juce::String::fromUTF8 ((const char*) ch, 4);
            if (id == "LIST")
            {
                if (in->read (ch + 8, 4) != 4) break;
                juce::String type = juce::String::fromUTF8 ((const char*) ch + 8, 4);
                juce::int64 p = pos + 12, end = pos + 8 + (juce::int64) size;
                while (p + 8 <= end && p + 8 <= total)
                {
                    juce::uint8 c2[8]; in->setPosition (p);
                    if (in->read (c2, 8) != 8) break;
                    juce::uint32 s2 = u32 (c2 + 4); juce::String id2 = juce::String::fromUTF8 ((const char*) c2, 4);
                    if (type == "sdta" && id2 == "smpl") { smplOffset = p + 8; smplSize = (juce::int64) s2; }
                    else if (type == "pdta" && s2 < 64u * 1024 * 1024)
                    {
                        std::vector<juce::uint8> v ((size_t) s2); if (s2 > 0) in->read (v.data(), (int) s2);
                        pdta[id2] = std::move (v);
                    }
                    else if (type == "INFO" && id2 == "ifil") { juce::uint8 v[4]; if (in->read (v, 4) == 4 && u16 (v) >= 3) compressed = true; }
                    p += 8 + (juce::int64) s2 + (s2 & 1);
                }
            }
            pos += 8 + (juce::int64) size + (size & 1);
        }
        if (compressed) { error = "SF3 (COMPRESSED) NOT SUPPORTED"; return false; }
        if (smplSize <= 0 || pdta["phdr"].empty() || pdta["shdr"].empty()) { error = "NO SAMPLE DATA IN THE FILE"; return false; }
        auto& ph = pdta["phdr"]; size_t np = ph.size() / 38;
        for (size_t i = 0; i < np; ++i)
        {
            const juce::uint8* r = ph.data() + i * 38;
            presetBag.push_back (u16 (r + 24));
            if (i + 1 < np) { PresetInfo pi; pi.name = nameOf (r); pi.program = u16 (r + 20); pi.bank = u16 (r + 22); presetList.push_back (pi); }
        }
        auto& ib = pdta["inst"]; size_t ni = ib.size() / 22;
        for (size_t i = 0; i < ni; ++i) instBag.push_back (u16 (ib.data() + i * 22 + 20));
        for (auto pr : { std::make_pair ("pbag", &pbag), std::make_pair ("ibag", &ibag) })
        {
            auto& v = pdta[pr.first]; for (size_t i = 0; i + 4 <= v.size(); i += 4) pr.second->push_back ({ u16 (v.data() + i) });
        }
        for (auto pr : { std::make_pair ("pgen", &pgen), std::make_pair ("igen", &igen) })
        {
            auto& v = pdta[pr.first]; for (size_t i = 0; i + 4 <= v.size(); i += 4) pr.second->push_back ({ u16 (v.data() + i), (int) (short) (v[i + 2] | v[i + 3] << 8) });
        }
        auto& sh = pdta["shdr"]; size_t ns = sh.size() / 46;
        for (size_t i = 0; i + 1 < ns; ++i)
        {
            const juce::uint8* r = sh.data() + i * 46; SampleHdr s;
            s.name = nameOf (r); s.start = u32 (r + 20); s.end = u32 (r + 24); s.loopStart = u32 (r + 28); s.loopEnd = u32 (r + 32); s.rate = u32 (r + 36);
            s.pitch = r[40] == 255 ? 60 : r[40]; s.correction = (int) (signed char) r[41]; s.type = u16 (r + 44);
            shdr.push_back (s);
        }
        if (presetList.empty() || pbag.empty() || ibag.empty() || shdr.empty()) { error = "EMPTY SOUNDFONT"; return false; }
        return true;
    }

    int File::defaultPreset() const
    {
        for (size_t i = 0; i < presetList.size(); ++i) if (presetList[i].bank == 0 && presetList[i].program == 0) return (int) i;
        return 0;
    }

    bool File::build (int pi, Built& out, juce::String& error) const
    {
        if (pi < 0 || pi >= (int) presetList.size()) { error = "NO SUCH PRESET"; return false; }
        auto defaults = [] (Zone& z)
        {
            for (int i = 0; i < 64; ++i) { z.g[i] = 0; z.has[i] = false; }
            z.g[gDelayVol] = z.g[gAttackVol] = z.g[gHoldVol] = z.g[gDecayVol] = z.g[gReleaseVol] = -12000; z.g[gScaleTuning] = 100; z.g[gRootKey] = -1;
            z.g[gKeyRange] = 127 << 8; z.g[gVelRange] = 127 << 8; z.g[gSampleId] = -1; z.g[gInstrument] = -1;
        };
        auto readGens = [] (const std::vector<Gen>& gens, int from, int to, Zone& z)
        {
            for (int i = from; i < to && i < (int) gens.size(); ++i)
            {
                int op = gens[(size_t) i].oper; if (op < 0 || op >= 64) continue;
                z.g[op] = gens[(size_t) i].amount; z.has[op] = true;
            }
        };
        struct Raw { Zone z; int sid; };
        std::vector<Raw> raws;
        const int pb0 = presetBag[(size_t) pi], pb1 = presetBag[(size_t) pi + 1];
        Zone pGlobal; defaults (pGlobal); bool haveP = false;
        for (int b = pb0; b < pb1 && b + 1 < (int) pbag.size(); ++b)
        {
            Zone pz; defaults (pz); readGens (pgen, pbag[(size_t) b].gen, pbag[(size_t) b + 1].gen, pz);
            if (! pz.has[gInstrument]) { if (b == pb0) { pGlobal = pz; haveP = true; } continue; }
            const int ii = pz.g[gInstrument];
            if (ii < 0 || ii + 1 >= (int) instBag.size()) continue;
            Zone iGlobal; defaults (iGlobal); bool haveI = false;
            for (int c = instBag[(size_t) ii]; c < instBag[(size_t) ii + 1] && c + 1 < (int) ibag.size(); ++c)
            {
                Zone iz; defaults (iz); readGens (igen, ibag[(size_t) c].gen, ibag[(size_t) c + 1].gen, iz);
                if (! iz.has[gSampleId]) { if (c == instBag[(size_t) ii]) { iGlobal = iz; haveI = true; } continue; }
                // instrument zone = instrument global overridden by the zone; preset zone = preset global overridden by the zone, added on top (ranges: intersected)
                Zone m; defaults (m);
                for (int g = 0; g < 64; ++g)
                {
                    int v = (haveI && iGlobal.has[g] && ! iz.has[g]) ? iGlobal.g[g] : iz.g[g];
                    bool hv = iz.has[g] || (haveI && iGlobal.has[g]);
                    int pv = 0; bool hp = false;
                    if (pz.has[g]) { pv = pz.g[g]; hp = true; } else if (haveP && pGlobal.has[g]) { pv = pGlobal.g[g]; hp = true; }
                    if (g == gKeyRange || g == gVelRange)
                    {
                        int lo = v & 255, hi = (v >> 8) & 255;
                        if (hp) { lo = std::max (lo, pv & 255); hi = std::min (hi, (pv >> 8) & 255); }
                        m.g[g] = lo | (hi << 8);
                    }
                    else if (g == gInstrument || g == gSampleId || g == gSampleModes || g == gRootKey || g == gScaleTuning) m.g[g] = v;
                    else m.g[g] = hv ? v + (hp ? pv : 0) : (hp ? m.g[g] + pv : m.g[g]);
                    if (hv || hp) m.has[g] = true;
                    if (! hv && ! hp) m.g[g] = (g == gDelayVol || g == gAttackVol || g == gHoldVol || g == gDecayVol || g == gReleaseVol) ? -12000 : (g == gScaleTuning ? 100 : (g == gRootKey ? -1 : (g == gKeyRange || g == gVelRange ? (127 << 8) : 0)));
                }
                m.g[gSampleId] = iz.g[gSampleId];
                raws.push_back ({ m, iz.g[gSampleId] });
            }
        }
        if (raws.empty()) { error = "THE PRESET HAS NO ZONES"; return false; }

        // zones -> records, samples (deduplicated by region and loop)
        struct Reg { int sid; juce::int64 start, end, ls, le; std::vector<float> a; int rate; };
        std::vector<Reg> regs; std::map<std::tuple<int, juce::int64, juce::int64, juce::int64, juce::int64>, int> regIdx;
        struct Z { int f[kSfZf]; int reg; };
        std::vector<Z> zones;
        juce::String note;
        std::unique_ptr<juce::FileInputStream> in (file.createInputStream());
        if (in == nullptr) { error = "CANNOT READ THE FILE"; return false; }
        const juce::int64 nSmp = smplSize / 2;
        for (auto& rz : raws)
        {
            if (rz.sid < 0 || rz.sid >= (int) shdr.size()) continue;
            auto& sh = shdr[(size_t) rz.sid]; auto& g = rz.z.g;
            if (sh.type & 0x8000) continue;     // ROM samples
            juce::int64 st = (juce::int64) sh.start + g[gStartOff] + 32768ll * g[gStartCoarse], en = (juce::int64) sh.end + g[gEndOff] + 32768ll * g[gEndCoarse];
            juce::int64 ls = (juce::int64) sh.loopStart + g[gStartLoopOff] + 32768ll * g[gStartLoopCoarse], le = (juce::int64) sh.loopEnd + g[gEndLoopOff] + 32768ll * g[gEndLoopCoarse];
            st = juce::jlimit<juce::int64> (0, nSmp, st); en = juce::jlimit<juce::int64> (st, nSmp, en);
            if (en - st < 4) continue;
            int mode = g[gSampleModes] & 3; bool loops = (mode == 1 || mode == 3) && le > ls + 8 && ls >= st && le <= en;
            auto key = std::make_tuple (rz.sid, st, en, loops ? ls : 0, loops ? le : 0);
            int ri;
            if (regIdx.count (key)) ri = regIdx[key];
            else
            {
                Reg r; r.sid = rz.sid; r.start = st; r.end = en; r.ls = loops ? ls - st : 0; r.le = loops ? le - st : 0; r.rate = (int) sh.rate;
                r.a.resize ((size_t) (en - st)); std::vector<juce::uint8> raw ((size_t) (en - st) * 2);
                in->setPosition (smplOffset + st * 2);
                if (in->read (raw.data(), (int) raw.size()) != (int) raw.size()) continue;
                for (size_t i = 0; i < r.a.size(); ++i) r.a[i] = (float) s16 (raw.data() + i * 2) / 32768.0f;
                ri = (int) regs.size(); regs.push_back (std::move (r)); regIdx[key] = ri;
            }
            Z z; for (int i = 0; i < kSfZf; ++i) z.f[i] = 0;
            z.f[KeyLo] = g[gKeyRange] & 127; z.f[KeyHi] = (g[gKeyRange] >> 8) & 127; z.f[VelLo] = g[gVelRange] & 127; z.f[VelHi] = (g[gVelRange] >> 8) & 127;
            if (z.f[KeyHi] < z.f[KeyLo] || z.f[VelHi] < z.f[VelLo]) continue;
            z.f[LoopMode] = loops ? mode : 0; z.f[Root] = g[gRootKey] >= 0 ? g[gRootKey] : sh.pitch;
            z.f[TuneCents] = g[gCoarseTune] * 100 + g[gFineTune] + sh.correction; z.f[SampleRate] = (int) sh.rate;
            z.f[AttenCb] = juce::jlimit (0, 1440, g[gAtten]);
            int pan = g[gPan]; if (pan == 0 && (sh.type & 7) == 4) pan = -500; else if (pan == 0 && (sh.type & 7) == 2) pan = 500;
            z.f[Pan] = juce::jlimit (-500, 500, pan);
            z.f[AttackMs] = juce::jlimit (1, 30000, (int) std::lround (tcToMs (g[gAttackVol]))); z.f[HoldMs] = g[gHoldVol] <= -11000 ? 0 : juce::jlimit (0, 30000, (int) std::lround (tcToMs (g[gHoldVol])));
            z.f[DecayMs] = juce::jlimit (1, 60000, (int) std::lround (tcToMs (g[gDecayVol]))); z.f[SustainCb] = juce::jlimit (0, 1440, g[gSustainVol]);
            z.f[ReleaseMs] = juce::jlimit (1, 30000, (int) std::lround (tcToMs (g[gReleaseVol]))); z.f[ScaleTuning] = juce::jlimit (0, 1200, g[gScaleTuning]);
            z.reg = ri; zones.push_back (z);
        }
        if (zones.empty()) { error = "THE PRESET HAS NO USABLE SAMPLES"; return false; }

        // too many zones: every second key group is dropped and its neighbour covers its keys
        if ((int) zones.size() > kSfMaxZones)
        {
            std::stable_sort (zones.begin(), zones.end(), [] (const Z& a, const Z& b) { return std::make_pair (a.f[KeyLo], a.f[KeyHi]) < std::make_pair (b.f[KeyLo], b.f[KeyHi]); });
            int guard = 0;
            while ((int) zones.size() > kSfMaxZones && guard++ < 8)
            {
                std::vector<std::pair<int, int>> groups;
                for (auto& z : zones) if (groups.empty() || groups.back() != std::make_pair (z.f[KeyLo], z.f[KeyHi])) groups.push_back ({ z.f[KeyLo], z.f[KeyHi] });
                if (groups.size() < 2) break;
                std::vector<Z> kept;
                for (auto& z : zones)
                {
                    size_t gi = (size_t) (std::find (groups.begin(), groups.end(), std::make_pair (z.f[KeyLo], z.f[KeyHi])) - groups.begin());
                    if (gi % 2 == 0 || gi + 1 == groups.size()) kept.push_back (z);
                }
                // extend the kept groups over the dropped ones
                std::vector<std::pair<int, int>> keptGroups;
                for (auto& z : kept) if (keptGroups.empty() || keptGroups.back() != std::make_pair (z.f[KeyLo], z.f[KeyHi])) keptGroups.push_back ({ z.f[KeyLo], z.f[KeyHi] });
                for (auto& z : kept)
                {
                    size_t gi = (size_t) (std::find (keptGroups.begin(), keptGroups.end(), std::make_pair (z.f[KeyLo], z.f[KeyHi])) - keptGroups.begin());
                    if (gi + 1 < keptGroups.size()) z.f[KeyHi] = keptGroups[gi + 1].first - 1; else z.f[KeyHi] = std::max (z.f[KeyHi], 127);
                    if (gi == 0) z.f[KeyLo] = 0;
                }
                zones.swap (kept);
            }
            if ((int) zones.size() > kSfMaxZones) zones.resize ((size_t) kSfMaxZones);
            note = "ZONES MERGED";
        }

        // used regions only; audio budget: decimate by 2 up to three times, then shorten
        std::vector<int> used; for (auto& z : zones) if (std::find (used.begin(), used.end(), z.reg) == used.end()) used.push_back (z.reg);
        auto totalLen = [&] { juce::int64 t = 0; for (int r : used) t += (juce::int64) regs[(size_t) r].a.size(); return t; };
        std::map<int, int> rateOf; for (int r : used) rateOf[r] = regs[(size_t) r].rate;
        int dec = 0;
        while (totalLen() > kSfAudio && dec < 3)
        {
            for (int r : used)
            {
                auto& rg = regs[(size_t) r]; std::vector<float> n (rg.a.size() / 2);
                for (size_t i = 0; i < n.size(); ++i) n[i] = 0.5f * (rg.a[2 * i] + rg.a[2 * i + 1]);
                rg.a.swap (n); rg.ls /= 2; rg.le /= 2; rateOf[r] /= 2;
            }
            ++dec;
        }
        if (dec) note += (note.isEmpty() ? "" : ", ") + juce::String ("SAMPLES DECIMATED X") + juce::String (1 << dec);
        if (totalLen() > kSfAudio)
        {
            const double f = (double) kSfAudio / (double) totalLen();
            for (int r : used)
            {
                auto& rg = regs[(size_t) r]; size_t nl = std::max<size_t> (16, (size_t) std::floor ((double) rg.a.size() * f));
                if (rg.le > 0) nl = std::max<size_t> (nl, (size_t) std::min<juce::int64> (rg.le, (juce::int64) rg.a.size() / 2 + 16));
                if (nl < rg.a.size()) { rg.a.resize (nl); if (rg.le > (juce::int64) nl) { rg.le = (juce::int64) nl; rg.ls = std::min<juce::int64> (rg.ls, (juce::int64) nl / 2); } }
            }
            note += (note.isEmpty() ? "" : ", ") + juce::String ("SAMPLES SHORTENED");
        }

        out.data.assign ((size_t) kSfHdr, 0.0f);
        out.data[0] = 12345.0f; out.data[1] = (float) zones.size(); out.data[2] = 1.0f;
        std::map<int, int> placeAt; int cursor = 0;
        for (int r : used)
        {
            auto& rg = regs[(size_t) r];
            if (cursor + (int) rg.a.size() > kSfAudio) rg.a.resize ((size_t) std::max (0, kSfAudio - cursor));
            placeAt[r] = cursor; out.data.insert (out.data.end(), rg.a.begin(), rg.a.end()); cursor += (int) rg.a.size();
        }
        for (size_t zi = 0; zi < zones.size(); ++zi)
        {
            auto& z = zones[zi]; auto& rg = regs[(size_t) z.reg]; float* o = out.data.data() + 8 + zi * (size_t) kSfZf;
            for (int i = 0; i < kSfZf; ++i) o[i] = (float) z.f[i];
            o[Start] = (float) placeAt[z.reg]; o[Len] = (float) rg.a.size(); o[LoopS] = (float) rg.ls; o[LoopE] = (float) std::min<juce::int64> (rg.le, (juce::int64) rg.a.size());
            if (o[LoopE] <= o[LoopS] + 2) { o[LoopMode] = 0; o[LoopS] = o[LoopE] = 0; }
            o[SampleRate] = (float) rateOf[z.reg];
        }
        out.name = presetList[(size_t) pi].name; out.note = note; out.zones = (int) zones.size(); out.samples = cursor;
        return true;
    }
}
