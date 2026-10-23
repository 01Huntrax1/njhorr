// Minimal scripted host for the C++ that `cmaj generate --target=cpp` emits for the Njohrr patch.
// Used by tools/osc/test_osc.py to render audio from the DSP without a plugin host.
//
//   g++ -O2 -std=c++17 -DDSP_HEADER='"out.cpp"' dsp_host.cpp -o dsp_host
//   ./dsp_host script.txt out.f32
//
// script lines:   p <paramNumber> <value>   set parameter N (event)
//                 shape <lfo 0-9> const <v> | shape <lfo> ramp   load a 256-point LFO shape
//                 wt <slot 0-5> <kind> [a] [b]   load a wavetable memory (kinds: sine, saw, morph = 8 frames sine->saw, saw2k, morph2k, big, clear)
//                 tbl <bank 0-11> <kind>   load a Wavefilter (0-5) / Wavedistortion (6-11) table (kinds: clear, ones, zeros, lin)
//                 smp <slot 0-5> <kind> [hz]     load a 1 s sample (kinds: sine, saw, noise, clear)
//                 on <note> <velocity 0-127>
//                 off <note>
//                 run <seconds>             render, appending interleaved stereo float32 to the output file
#include DSP_HEADER
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
        else if (cmd == "tbl") { int b; std::string k; ls >> b >> k; h.table (b, k); }
        else if (cmd == "wt" || cmd == "smp") { int n; std::string k; float a = 0; ls >> n >> k >> a; h.bank (cmd == "wt", n, k, a); }
        else if (cmd == "on")  { int n, v; ls >> n >> v; h.midi (0x90, n, v); }
        else if (cmd == "off") { int n; ls >> n; h.midi (0x80, n, 0); }
        else if (cmd == "run") { double s; ls >> s; h.render ((int) (s * kRate)); h.queued = 0; }
    }

    fclose (h.out);
    return 0;
}
