#pragma once
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cmath>
#include <cstdlib>
typedef int32_t VstInt32;
typedef void* audioMasterCallback;
class AudioEffect { public: virtual ~AudioEffect() {} };
enum { kVstMaxProgNameLen = 64, kVstMaxParamStrLen = 64, kVstMaxVendorStrLen = 64, kVstMaxEffectNameLen = 64, kVstMaxProductStrLen = 64 };
enum VstPlugCategory { kPlugCategEffect = 1 };
inline void vst_strncpy (char* d, const char* s, int n) { strncpy (d, s, n); d[n] = 0; }
inline void float2string (float v, char* t, int n) { snprintf (t, n, "%f", v); }
inline void dB2string (float, char* t, int) { t[0] = 0; }
inline void int2string (int v, char* t, int n) { snprintf (t, n, "%d", v); }
inline void float2string (double v, char* t, int n) { snprintf (t, n, "%f", v); }
class AudioEffectX : public AudioEffect {
public:
    AudioEffectX (audioMasterCallback, int, int) {}
    virtual ~AudioEffectX() {}
    void setNumInputs (int) {} void setNumOutputs (int) {} void setUniqueID (unsigned long) {}
    void canProcessReplacing() {} void canDoubleReplacing() {} void programsAreChunks (bool) {}
    double getSampleRate() { return sr; }
    void* getEditor() { return 0; }
    static double sr;
};
double AudioEffectX::sr = 48000.0;
