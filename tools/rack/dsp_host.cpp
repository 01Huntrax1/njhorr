// Minimal scripted host for the C++ that `cmaj generate --target=cpp` emits for the Njohrr patch.
// Used by tools/rack/test_rack.py to render audio from the DSP without a plugin host.
//
//   g++ -O2 -std=c++17 -DDSP_HEADER='"out.cpp"' dsp_host.cpp -o dsp_host
//   ./dsp_host script.txt out.f32
//
// script lines:   p <paramNumber> <value>   set parameter N (event)
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
        else if (cmd == "on")  { int n, v; ls >> n >> v; h.midi (0x90, n, v); }
        else if (cmd == "off") { int n; ls >> n; h.midi (0x80, n, 0); }
        else if (cmd == "run") { double s; ls >> s; h.render ((int) (s * kRate)); h.queued = 0; }
    }

    fclose (h.out);
    return 0;
}
