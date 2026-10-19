// usage: host <engine> <note> <harm> <timb> <morph> <nblocks> <out.f32> [trigBlocks] [instance]
// output layout identical to tools/plaits/ref/ref.cc: per block 12 out samples then 12 aux samples
#include DSP_HEADER
#include <cstdio>
#include <cstdlib>
#include <vector>
int main (int argc, char** argv)
{
    if (argc < 8) return 1;
    PlaitsTest dsp;
    dsp.initialise (1, 48000.0);
    dsp.addEvent_evInstance (argc > 9 ? (float) atof (argv[9]) : 0.0f);
    dsp.addEvent_evEngine ((float) atof (argv[1]));
    dsp.addEvent_evNote ((float) atof (argv[2]));
    dsp.addEvent_evHarm ((float) atof (argv[3]));
    dsp.addEvent_evTimb ((float) atof (argv[4]));
    dsp.addEvent_evMorph ((float) atof (argv[5]));
    if (argc > 8) dsp.addEvent_evTrigBlocks ((float) atof (argv[8]));
    int nblocks = atoi (argv[6]);
    std::vector<float> res;
    std::vector<float> o (12), a (12);
    for (int b = 0; b < nblocks; ++b)
    {
        dsp.advance (12);
        dsp.copyOutputFrames ((PlaitsTest::EndpointHandle) PlaitsTest::EndpointHandles::out, o.data(), 12);
        dsp.copyOutputFrames ((PlaitsTest::EndpointHandle) PlaitsTest::EndpointHandles::aux, a.data(), 12);
        res.insert (res.end(), o.begin(), o.end());
        res.insert (res.end(), a.begin(), a.end());
    }
    FILE* f = fopen (argv[7], "wb"); fwrite (res.data(), 4, res.size(), f); fclose (f);
    return 0;
}
