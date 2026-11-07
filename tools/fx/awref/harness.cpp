#include HDR
#include HDR2
#include <vector>
#include <iostream>
// usage: h <sr> <in.f32> <out.f32> <paramA> ...
int main (int argc, char** argv)
{
    AudioEffectX::sr = atof (argv[1]);
    PLUG p (nullptr);
    for (int i = 4; i < argc; ++i) p.setParameter (i - 4, (float) atof (argv[i]));
    FILE* f = fopen (argv[2], "rb"); std::vector<float> in; float v[2];
    while (fread (v, 4, 2, f) == 2) { in.push_back (v[0]); in.push_back (v[1]); } fclose (f);
    size_t n = in.size() / 2; std::vector<double> l (n), r (n), ol (n), orr (n);
    for (size_t i = 0; i < n; ++i) { l[i] = in[2*i]; r[i] = in[2*i+1]; }
    const size_t B = 512;
    for (size_t o = 0; o < n; o += B)
    {
        size_t m = std::min (B, n - o); double* ins[2] = { l.data() + o, r.data() + o }; double* outs[2] = { ol.data() + o, orr.data() + o };
        p.processDoubleReplacing (ins, outs, (VstInt32) m);
    }
    f = fopen (argv[3], "wb"); for (size_t i = 0; i < n; ++i) { float w[2] = { (float) ol[i], (float) orr[i] }; fwrite (w, 4, 2, f); } fclose (f);
}
