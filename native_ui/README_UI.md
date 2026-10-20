# Native JUCE UI (work in progress)

A C++ rewrite of `patch/index.js` (the web UI). The JS UI stays as the fallback. The native UI is one component of the fixed
logical size 1180 x 760 (`EditorContent`); the plugin editor scales it to the window.

## Layout of the code
* `NjoData.h/.cpp`, `NjoData.gen.cpp` - parameter specs (872), labels, FX types, LFO presets ... `NjoData.gen.cpp` is generated from
  `patch/index.js` by `node tools/nativeui/gen_data.js` (do not edit by hand). `formatValue()` = `fmt()` of the JS UI.
* `NjoBackend.h` - the only thing the UI needs from the plugin (parameters by number, events to the DSP, stored state, folders).
  `NjoMock.h` is an in-memory implementation for tests.
* `NjoCore.h/.cpp` (`Ctx`) - shared context: parameter access, fx slot types, modulation matrix helpers (`modAssign`, `modsFor` ...).
* `NjoTheme.*` - colours, fonts and painting helpers (card, button, knob).
* `NjoWidgets.*` - `KnobWidget`, `SliderWidget`, `ButtonsWidget`, `SelectWidget`, `StepperWidget` (all `ParamWidget`s bound to one
  parameter number; modulation drop targets). `makeWidget(ctx, num, asKnob)`.
* `NjoEditor.*` - the shell: top bar, page rail (Synth / Effects / Modulation), OSC tabs, preset bar, bottom strip.
* `NjoPages.h` - interfaces of the pages; `pages/*.cpp` implement them (stubs until written).
* `NjoMemory.*` - sample / wavetable memory. `NjoManager.*` - preset bar, Preset Bank, Sound Vault.

## Building and looking at it (headless, no display needed)
JUCE lives in /home/claude/JUCE. Its object files were built once into /tmp/njo_juce_objs (from `test/CMakeLists.txt`).

    native_ui/test/fastbuild.sh /tmp/fb_<name> -j2          # builds /tmp/fb_<name>/njo_shot  (set NJO_SRC=<private copy of native_ui> to build that)
    /tmp/fb_<name>/njo_shot /tmp/shots_<name>               # writes osc1..osc6, fm, global, fx, mod .png (1180x760)

View the PNGs with the Read tool. Compare with the web UI screenshots in
/tmp/claude-0/-home-claude/c011a536-b544-58c8-a399-01d9f993fa60/scratchpad/shot/ (o_wt.png, o_sm.png, o_pl.png, o_fm.png, n_fx.png, n_mod.png, fm_new.png, ...).
The JS UI is the visual and behavioural reference: read the matching parts of patch/index.js and port them 1:1 (same parameters,
same defaults, same formulas for the displays).

## Rules for parallel work
Each worker copies native_ui to /tmp/wk/<name>/native_ui, builds there (NJO_SRC), and only edits ITS files. Shared files
(NjoWidgets, NjoCore, NjoTheme, NjoData, NjoEditor) may only get small additive changes; when you need one, tell the owner (the
main session) in your final report instead of rewriting them. When done, copy your own files back into the repo's native_ui folder
and report what you changed. Do not run git commands.
