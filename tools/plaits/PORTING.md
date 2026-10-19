# Porting Plaits engines to Cmajor

Goal: every engine of the original Plaits (`plaits/dsp/engine*/`) runs inside the Njohrr oscillator slots.
The original sources are in `$SP/eurorack` (SP=/tmp/claude-0/-home-claude/c011a536-b544-58c8-a399-01d9f993fa60/scratchpad;
`$SP/eurorack/plaits`, `$SP/eurorack/stmlib`). The native reference renderer is `$SP/ref` (source `tools/plaits/ref/ref.cc`).

## What one engine file looks like
`tools/plaits/parts/eng_NN_name.part` (NN = engine index 0..23, see `build.py ENGINE_NAMES`) is processor-scope Cmajor code that defines

    PlXxx[48] plXxx;                                   // state: one struct per instance (8 voices x 6 slots)
    void plInit_NN (int inst)                          // = Init() + Reset() of the original (+ LoadUserData)
    void plRender_NN (int inst, int trig, float note, float harm, float timb, float morph, float accent)
                                                       // = Render(): writes plOut.at(inst*12+i) and plAux.at(inst*12+i), i < 12
    
`trig` has the bits of the original TriggerState (1 = rising edge, 4 = gate high; never 2). `note` is the MIDI note passed to
`NoteToFrequency` (use `plNoteToFrequency`). The block is always 12 samples (kBlockSize). Look at `parts/eng_08_virtual_analog.part`
and `parts/lib_varosc.part` first: they are complete examples (state structs, ParameterInterpolator replaced by explicit
increment loops, template flags as bool arguments, output buffers as `float[12]&`).

Shared helpers of stmlib are in `core.part`: `plSemitonesToRatio`, `plNoteToFrequency`, `plInterpolate*`, polyblep, `PlOnePole`,
`PlSvf`, `PlDcBlocker`, soft clip, and a per instance random generator (`plRandWord/plRandFloat/plRandSample(inst)`, identical
sequence to `stmlib::Random` when the engine is the only user, so noise based engines can be bit exact too).
`core.part` and `build.py` are shared: do NOT edit them. If you need another helper put it into your own file.

## Rules
* Helper structs / functions / constants of your files must carry a prefix unique to your engines (e.g. `plStr...`, `plSwarm...`)
  because all parts end up in one processor. Library files for several engines of yours: `parts/lib_<yourgroup>_*.part`.
* Tables: put `//@LUT lut_name` on its own line (resources.cc / units.cc names). `gen_lut.py` converts them to `const float[N]` / `const int[N]`.
  For int16/int8 tables the values come out as `int` arrays. Tables that are not in `resources.cc` (computed in C++ at init) must be
  generated in `plInit_NN`, into per-engine global arrays, or at compile time by a small script writing a `luts/*.part` file.
* Cmajor pitfalls: there are no unsigned types (use int32 / int64, int64 literals need the `i64` suffix); `.at(i)` for arrays (wraps
  the index, so size your arrays correctly); struct arguments by reference (`PlFoo& s`); arrays by reference (`float[12]& out`) or
  as slices (`const float[] table`); no struct member functions; no templates (turn flags into bool/int arguments);
  integer division truncates; `float` literals need the `f` suffix; use `abs`, `min`, `max`, `clamp`, `pow`, `exp`, `log`, `sin`, `cos`, `tan`, `sqrt`, `floor`, `fmod`.
  Large constant tables compile fine. Keep per instance state reasonable: report the size in floats of your state structs.
* Do not use the global `plRng` seed anywhere except through the helpers; seed handling is done by the dispatcher (`33 + inst` before `plInit`).
* The module-level post processing (gain / limiter, `build.py GAIN`) is not part of your engines: compare the raw engine output.

## Verification
    python3 tools/plaits/compare.py <engine> [--blocks 400] [--tol 2e-3] [--cases "note,harm,timb,morph;..."] [--aux] [--trig N] [--noise]
builds the stand-alone test patch with only the engine parts present, renders cases with both the original C++ and the port, prints
the maximum sample error (and the aux error with `--aux`). Aim for bit exact or < 1e-3. `--trig N` keeps the gate high for N blocks
(default: forever; the rising edge is always in block 0). For percussive engines use `--trig 8` and enough blocks to cover the decay.
Cover the parameter space: harmonics/timbre/morph at 0, 0.5, 1 and in between, low and high notes, trigger on/off.
Engines whose output is intentionally random and cannot match sample by sample may be checked with `--noise` (RMS and spectrum).
Every `--cases` entry must be checked in both `out` and `aux` unless the aux output is never used by the synth (we only use `out`; `aux` correctness is nice to have).

Do not touch files that belong to other engines, do not run git commands (the owner commits).
