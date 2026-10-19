// Native reference renderer of the original Plaits engines (used to verify the Cmajor ports).
// usage: ref <engine 0..23> <note> <harmonics> <timbre> <morph> <nblocks> <out.f32> [trigger_blocks]
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "plaits/dsp/voice.h"
#include "plaits/resources.h"
using namespace plaits;
using namespace stmlib;

static char ram[1 << 20];

int main(int argc, char** argv) {
  if (argc < 8) return 1;
  int eng = atoi(argv[1]);
  float note = atof(argv[2]), harm = atof(argv[3]), timb = atof(argv[4]), morph = atof(argv[5]);
  int nblocks = atoi(argv[6]);
  const char* path = argv[7];
  int trig_blocks = argc > 8 ? atoi(argv[8]) : 1000000;
  static char big[512 * 1024];
  BufferAllocator allocator(big, sizeof(big));
  // build only the requested engine (as in Voice::Init) 
  VirtualAnalogVCFEngine e0; PhaseDistortionEngine e1; SixOpEngine e2; WaveTerrainEngine e5; StringMachineEngine e6; ChiptuneEngine e7;
  VirtualAnalogEngine e8; WaveshapingEngine e9; FMEngine e10; GrainEngine e11; AdditiveEngine e12; WavetableEngine e13; ChordEngine e14; SpeechEngine e15;
  SwarmEngine e16; NoiseEngine e17; ParticleEngine e18; StringEngine e19; ModalEngine e20; BassDrumEngine e21; SnareDrumEngine e22; HiHatEngine e23;
  Engine* all[24] = {&e0,&e1,&e2,&e2,&e2,&e5,&e6,&e7,&e8,&e9,&e10,&e11,&e12,&e13,&e14,&e15,&e16,&e17,&e18,&e19,&e20,&e21,&e22,&e23};
  Engine* e = all[eng];
  allocator.Free();
  e->Init(&allocator);
  const uint8_t* data = nullptr;
  if (eng >= 2 && eng <= 4) data = fm_patches_table[eng - 2];
  e->LoadUserData(data);
  e->Reset();
  std::vector<float> out;
  float o[kBlockSize], a[kBlockSize];
  for (int b = 0; b < nblocks; ++b) {
    EngineParameters p;
    bool gate = b < trig_blocks;
    p.trigger = (b == 0 ? TRIGGER_RISING_EDGE : TRIGGER_LOW) | (gate ? TRIGGER_HIGH : TRIGGER_LOW);
    p.note = note; p.harmonics = harm; p.timbre = timb; p.morph = morph; p.accent = 0.8f;
    bool env = false;
    e->Render(p, o, a, kBlockSize, &env);
    for (size_t i = 0; i < kBlockSize; ++i) out.push_back(o[i]);
    for (size_t i = 0; i < kBlockSize; ++i) out.push_back(a[i]);
  }
  FILE* f = fopen(path, "wb"); fwrite(out.data(), 4, out.size(), f); fclose(f);
  return 0;
}
