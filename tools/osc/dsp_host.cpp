// Minimal scripted host for the C++ that `cmaj generate --target=cpp` emits for the Njohrr patch.
// Used by tools/osc/test_osc.py to render audio from the DSP without a plugin host.
//
//   g++ -O2 -std=c++17 -DDSP_HEADER='"out.cpp"' dsp_host.cpp -o dsp_host
//   ./dsp_host script.txt out.f32
//
// script lines:   p <paramNumber> <value>   set parameter N (event)
//                 shape <lfo 0-9> const <v> | shape <lfo> ramp   load a 256-point LFO shape
//                 wt <slot 0-5> <kind> [a] [b]   load a wavetable memory (kinds: sine, saw, morph = 8 frames sine->saw, saw2k, morph2k, big, clear)
//                 fshape <freq mod 0-9> const <v> | ramp   load the 256-point curve (0..1) of a Freq modulator
//                 tbl <bank 0-11> <kind>   load a Wavefilter (0-5) / Wavedistortion (6-11) table (kinds: clear, ones, zeros, lin)
//                 smp <slot 0-5> <kind> [hz]     load a 1 s sample (kinds: sine, saw, noise, clear)
//                 ir <rack 0-2> <kind> [n]  load a convolution impulse response (kinds: clear, impulse n = unit pulse at sample n, burst = 0.3 s decaying noise)
//                 moded <bank 0-17> reset | <mode 0-15> <freq> <gain> <decay>   resonator mode edits of slot*3+set (0 = Physical A, 1 = B, 2 = Resonator stage)
//                 eqband <slot 0-29> <band 0-23> <on> <type 0-14> <Hz> <dB> <Q> [harmonics falloff(0-1) set(0 all,1 odd,2 even) channel(0 st,1 L,2 R,3 M,4 S)]   set a band of a Parametric EQ slot
//                 wscount <slot> <n> / wsnode <slot> <idx> <x> <y> <curve>   Waveshaper nodes (values -1..1, stored like EQ bands; send with eqsend)
//                 eqsend <slot>  /  eqclear <slot>   send the bands of the slot to the DSP / remove them all
//                 on <note> <velocity 0-127>
//                 off <note>
//                 run <seconds>             render, appending interleaved stereo float32 to the output file
#include DSP_HEADER
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

static const double kRate = 48000.0;

struct Host
{
    Eisenpuls_Synth dsp;
    FILE* out = nullptr;
    int queued = 0;
    std::vector<float> block;

    Host() { dsp.initialise (1, kRate); block.resize (512 * 2); }

    // the generated class queues at most 32 events per advance(); flush before that
    void flushIfNeeded()
    {
        if (queued >= 24) { render (1); queued = 0; }
    }

    void render (int frames)
    {
        while (frames > 0)
        {
            int n = frames < 512 ? frames : 512;
            dsp.advance (n);
            dsp.copyOutputFrames ((Eisenpuls_Synth::EndpointHandle) Eisenpuls_Synth::EndpointHandles::out, block.data(), (uint32_t) n);
            if (out) fwrite (block.data(), sizeof (float), (size_t) n * 2, out);
            frames -= n;
        }
    }

    void setParam (int num, float v)
    {
        char name[32];
        snprintf (name, sizeof name, "param%d", num);
        auto h = Eisenpuls_Synth::getEndpointHandleForName (name);
        if (h == 0xffffffffu) { fprintf (stderr, "unknown parameter %d\n", num); exit (3); }
        dsp.addEvent (h, 0, reinterpret_cast<const unsigned char*> (&v));
        ++queued;
        flushIfNeeded();
    }

    // loads a 256-point LFO shape: "const v" (every point v) or "ramp" (-1 .. 1)
    void lfoShape (int lfo, const std::string& kind, float v)
    {
        Eisenpuls_Synth::_Eisenpuls_Synth_LfoShapeChunk c {};
        c.lfo = lfo;
        for (int i = 0; i < 256; ++i)
            c.data[i] = kind == "ramp" ? -1.0f + 2.0f * (float) i / 255.0f : v;
        dsp.addEvent_lfoShapeLoad (c);
        ++queued;
        flushIfNeeded();
    }

    void freqShape (int m, const std::string& kind, float v)
    {
        Eisenpuls_Synth::_Eisenpuls_Synth_LfoShapeChunk c {};
        c.lfo = m;
        for (int i = 0; i < 256; ++i) c.data[i] = kind == "ramp" ? (float) i / 255.0f : v;
        dsp.addEvent_frqShapeLoad (c);
        ++queued;
        flushIfNeeded();
    }

    // loads a wavetable (kind) or sample memory into a slot
    void bank (bool wt, int slot, const std::string& kind, float a)
    {
        std::vector<float> d;
        const double tp = 6.283185307179586;
        if (kind == "clear") { }
        else if (wt)
        {
            // kinds: sine, saw, morph (8 frames of 256, sine -> saw); 2k variants use 2048 point frames:
            // saw2k (1 frame), morph2k (16 frames), big (128 frames), sawhi (1 frame of 2048 with a full-bandwidth saw)
            bool k2 = kind == "saw2k" || kind == "morph2k" || kind == "big";
            int frames = kind == "morph" ? 8 : (kind == "morph2k" ? 16 : (kind == "big" ? 128 : 1));
            int N = k2 ? 2048 : 256;
            for (int f = 0; f < frames; ++f)
                for (int i = 0; i < N; ++i)
                {
                    double ph = (double) i / N, sn = sin (tp * ph), sw = 2.0 * ph - 1.0;
                    double m = (kind == "morph" || kind == "morph2k" || kind == "big") ? f / (double) (frames - 1) : ((kind == "saw" || kind == "saw2k") ? 1.0 : 0.0);
                    d.push_back ((float) (0.9 * (sn * (1.0 - m) + sw * m)));
                }
        }
        else
        {
            double hz = a > 0 ? a : 261.6256;
            unsigned rng = 1;
            for (int i = 0; i < 48000; ++i)
            {
                double ph = fmod (hz * i / kRate, 1.0);
                rng = rng * 1664525u + 1013904223u;
                d.push_back (kind == "saw" ? (float) (0.9 * (2 * ph - 1)) : kind == "noise" ? (float) ((rng >> 8) / 8388608.0 - 1.0) * 0.9f : (float) (0.9 * sin (tp * ph)));
            }
        }
        sendBank (wt, slot, d);
    }

    void table (int bank, const std::string& kind)
    {
        std::vector<float> d;
        if (kind != "clear")
            for (int i = 0; i < 512; ++i)
                d.push_back (kind == "ones" ? 1.0f : kind == "zeros" ? 0.0f : (float) (i / 511.0 * 2.0 - 1.0));
        sendTable (bank, d);
    }

    void sendTable (int bank, const std::vector<float>& d)
    {
        int total = (int) d.size();
        for (int off = 0; off == 0 || off < total; off += 256)
        {
            Eisenpuls_Synth::_Eisenpuls_Synth_BankChunk c {};
            c.bank = bank; c.offset = off; c.total = total;
            c.count = total - off < 256 ? (total - off > 0 ? total - off : 0) : 256;
            for (int i = 0; i < c.count; ++i) c.data[i] = d[(size_t) off + i];
            dsp.addEvent_tblLoad (c);
            ++queued;
            flushIfNeeded();
            if (total == 0) break;
        }
    }

    void sendBank (bool wt, int slot, const std::vector<float>& d)
    {
        int total = (int) d.size();
        for (int off = 0; off == 0 || off < total; off += 256)
        {
            Eisenpuls_Synth::_Eisenpuls_Synth_BankChunk c {};
            c.bank = slot; c.offset = off; c.total = total;
            c.count = total - off < 256 ? (total - off > 0 ? total - off : 0) : 256;
            for (int i = 0; i < c.count; ++i) c.data[i] = d[(size_t) off + i];
            if (wt) dsp.addEvent_wtBankLoad (c); else dsp.addEvent_smpBankLoad (c);
            ++queued;
            flushIfNeeded();
            if (total == 0) break;
        }
    }

    void irLoad (int rack, const std::string& kind, int n)
    {
        std::vector<float> d;
        unsigned rng = 7;
        if (kind == "impulse") { d.assign ((size_t) n + 64, 0.0f); d[(size_t) n] = 1.0f; }
        else if (kind == "burst")
            for (int i = 0; i < 14400; ++i) { rng = rng * 1664525u + 1013904223u; d.push_back ((float) ((rng >> 8) / 8388608.0 - 1.0) * (float) exp (-i / 2400.0)); }
        int total = (int) d.size();
        for (int off = 0; off == 0 || off < total; off += 256)
        {
            Eisenpuls_Synth::_Eisenpuls_Synth_BankChunk c {};
            c.bank = rack; c.offset = off; c.total = total;
            c.count = total - off < 256 ? (total - off > 0 ? total - off : 0) : 256;
            for (int i = 0; i < c.count; ++i) c.data[i] = d[(size_t) off + i];
            dsp.addEvent_irLoad (c);
            ++queued;
            flushIfNeeded();
            if (total == 0) break;
        }
    }

    std::vector<float> eqData[30];
    void eqBand (int slot, int idx, int on, int type, float hz, float db, float q, int harm, float fall, int set, int ch)
    {
        auto& v = eqData[slot];
        if (v.empty()) v.assign (240, 0.0f);
        float* b = &v[(size_t) idx * 10];
        b[0] = (float) on; b[1] = type / 16.0f; b[2] = std::log2 (hz / 20.0f) / std::log2 (1000.0f); b[3] = db / 24.0f;
        b[4] = std::log2 (q / 0.1f) / std::log2 (300.0f); b[5] = harm / 16.0f; b[6] = fall; b[7] = set / 4.0f; b[8] = ch / 4.0f; b[9] = 0;
    }
    void eqSend (int slot, bool clear)
    {
        auto& v = eqData[slot];
        if (v.empty()) v.assign (240, 0.0f);
        if (clear) std::fill (v.begin(), v.end(), 0.0f);
        Eisenpuls_Synth::_Eisenpuls_Synth_BankChunk c {};
        c.bank = slot; c.offset = 0; c.count = 240; c.total = clear ? 0 : 240;
        for (int i = 0; i < 240; ++i) c.data[i] = v[(size_t) i];
        dsp.addEvent_eqLoad (c);
        ++queued;
        flushIfNeeded();
    }
    std::vector<float> modEdit[18];
    void modEd (int bank, bool reset, int mode, float f, float g, float d)
    {
        auto& v = modEdit[bank];
        if (v.empty()) v.assign (48, 1.0f);
        if (reset) std::fill (v.begin(), v.end(), 1.0f); else { v[(size_t) mode * 3] = f; v[(size_t) mode * 3 + 1] = g; v[(size_t) mode * 3 + 2] = d; }
        Eisenpuls_Synth::_Eisenpuls_Synth_BankChunk c {};
        c.bank = bank; c.offset = 0; c.total = reset ? 0 : 48; c.count = 48;
        for (int i = 0; i < 48; ++i) c.data[i] = v[(size_t) i];
        dsp.addEvent_modLoad (c);
        ++queued;
        flushIfNeeded();
    }

    void midi (int b0, int b1, int b2)
    {
        Eisenpuls_Synth::std_midi_Message m;
        m.message = (b0 << 16) | (b1 << 8) | b2;
        dsp.addEvent_midiIn (m);
        ++queued;
        flushIfNeeded();
    }
};

int main (int argc, char** argv)
{
    if (argc < 3) { fprintf (stderr, "usage: dsp_host script out.f32\n"); return 2; }

    Host& h = *new Host();   // the DSP state is tens of MB: heap, not stack
    h.out = fopen (argv[2], "wb");
    if (! h.out) return 2;

    std::ifstream in (argv[1]);
    std::string line;
    while (std::getline (in, line))
    {
        std::istringstream ls (line);
        std::string cmd;
        if (! (ls >> cmd) || cmd[0] == '#') continue;

        if (cmd == "p")        { int n; float v; ls >> n >> v; h.setParam (n, v); }
        else if (cmd == "shape") { int n; std::string k; float v = 0; ls >> n >> k >> v; h.lfoShape (n, k, v); }
        else if (cmd == "fshape") { int m; std::string k; float v = 0; ls >> m >> k >> v; h.freqShape (m, k, v); }
        else if (cmd == "tbl") { int b; std::string k; ls >> b >> k; h.table (b, k); }
        else if (cmd == "wt" || cmd == "smp") { int n; std::string k; float a = 0; ls >> n >> k >> a; h.bank (cmd == "wt", n, k, a); }
        else if (cmd == "ir")  { int r, n = 0; std::string k; ls >> r >> k >> n; h.irLoad (r, k, n); }
        else if (cmd == "moded") { int b; std::string k; ls >> b >> k; if (k == "reset") h.modEd (b, true, 0, 1, 1, 1); else { float f, g, d; ls >> f >> g >> d; h.modEd (b, false, std::stoi (k), f, g, d); } }
        else if (cmd == "eqband") { int sl, ix, on, ty, hm = 0, hs = 0, ch = 0; float hz, db, q, hf = 0.5f; ls >> sl >> ix >> on >> ty >> hz >> db >> q >> hm >> hf >> hs >> ch; h.eqBand (sl, ix, on, ty, hz, db, q, hm, hf, hs, ch); }
        else if (cmd == "wsnode") { int sl, ix; float x, y, c; ls >> sl >> ix >> x >> y >> c; auto& v = h.eqData[sl]; if (v.empty()) v.assign (240, 0.0f); v[(size_t) (1 + 3 * ix)] = x; v[(size_t) (2 + 3 * ix)] = y; v[(size_t) (3 + 3 * ix)] = c; }
        else if (cmd == "wscount") { int sl, n; ls >> sl >> n; auto& v = h.eqData[sl]; if (v.empty()) v.assign (240, 0.0f); v[0] = n / 16.0f; }
        else if (cmd == "eqsend") { int sl; ls >> sl; h.eqSend (sl, false); }
        else if (cmd == "eqclear") { int sl; ls >> sl; h.eqSend (sl, true); }
        else if (cmd == "on")  { int n, v; ls >> n >> v; h.midi (0x90, n, v); }
        else if (cmd == "off") { int n; ls >> n; h.midi (0x80, n, 0); }
        else if (cmd == "run") { double s; ls >> s; h.render ((int) (s * kRate)); h.queued = 0; }
    }

    fclose (h.out);
    return 0;
}
