# Njohrr - VST3 build

The plugin is a Cmajor patch (patch/) wrapped into a JUCE VST3 project by `cmaj generate --target=juce`.

## Build locally (needs CMake, a C++17 compiler and a JUCE checkout; built here against JUCE commit 454fe891)
    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DJUCE_PATH=/path/to/JUCE
    cmake --build build --config Release

The result is build/Njohrr_artefacts/Release/VST3/Njohrr.vst3
- Windows: copy the .vst3 folder to C:\Program Files\Common Files\VST3
- macOS:   copy to ~/Library/Audio/Plug-Ins/VST3  (universal arm64 + x86_64; unsigned, so you may need to allow it in System Settings or run: xattr -cr Njohrr.vst3)
- Linux:   copy to ~/.vst3
Linux also needs libgtk-3-dev and libwebkit2gtk-4.1-dev (the editor is a web view).

## Without a local compiler
Push this folder to a GitHub repository and run the "Build VST3" workflow (Actions tab).
It builds Windows, macOS and Linux and attaches each as a downloadable artifact.

## Changing the sound or UI
Edit patch/Eisenpuls_Synth.cmajor or patch/index.js, then generate into a separate temp folder (see "Important when rebuilding"):
    cmaj generate --target=juce --output=<folder> --cmajorIncludePath=<cmajor>/include patch/Eisenpuls_Synth.cmajorpatch

## Preset Bank and Sound Vault (inside the plugin window)
- PRESET bar under the title: previous / next, SAVE, BANK (the Preset Bank: save as new, overwrite, rename, delete).
- VAULT (the Sound Vault): samples and wavetables you load into any oscillator are added automatically; add more files, rename, delete, and load them into Sampler 1/2 or Wavetable 1-3. A preset remembers which vault file each oscillator used.

## Folders (Preset Bank and Sound Vault)
Inside the plugin the managers work on real folders in your Documents folder:

    Documents/Njohrr/Presets      *.njopreset   (plain text, easy to copy/share)
    Documents/Njohrr/Samples      audio files used by the samplers
    Documents/Njohrr/Wavetables   audio files used by the wavetable oscillators

- Every manager window has OPEN FOLDER and RESCAN. Drop files in with your file manager, press RESCAN, they show up.
- Anything you load into an oscillator is copied into the matching folder automatically.
- macOS may ask once whether the DAW may access your Documents folder - allow it.
- Outside the plugin (e.g. in a browser) the same managers fall back to temporary browser storage.

## Important when rebuilding
`include/cmajor/helpers/cmaj_NjohrrFiles.h` and the small `njo` binding in `include/cmajor/helpers/cmaj_PatchWebView.h` are Njohrr additions.
Do NOT re-run `cmaj generate` over this folder (it would overwrite them). To change the UI: edit patch/index.js, generate into a separate
temporary folder, and copy only the new `cmajor_plugin.cpp` back here.

## Where samples and wavetables are saved
Each plugin instance keeps its own samples and wavetables in the plugin's stored state, so they are saved with the DAW project and
are never shared between instances (loading a kick into Sampler 1 in one instance does not touch another instance).
They are stored as 16-bit audio, roughly 260 KB of project data per loaded sampler or wavetable memory.
The Sound Vault folders (Documents/Njohrr/...) are a shared library of files; which vault file an oscillator uses is also per instance.
Regression test: `cd tests && npm install && npm test`.

## FX racks and buses 
There are three FX racks of 10 slots each: **Bus 1**, **Bus 2** and **Main** (tabs on the FX page). Any effect (Distortion, Bit Crush, Delay,
Chorus, Flanger, Phaser, Tremolo, Reverb, Filter with all 30 filter types of the Filter page, EQ, Compressor) fits in any slot, with on/off, mix,
a mode selector and up to six knobs. Drag the grip (or use the arrows) to change the order within a rack; the signal runs top to bottom.

Routing: every mixer channel (Osc, Sub, Noise, Supersaw, Sampler 1/2, WT 1-3) has an **Output** selector (Main / Bus 1 / Bus 2) on the Mixer page.
Sources on Bus 1 / Bus 2 are filtered by their own copy of the voice filter, pass through the synth Drive, then the bus rack and the **Bus 1 / Bus 2**
level faders; both buses then feed the Main rack, which feeds Width / Tone / Output. With every source on Main (the default) the sound is the same as
without buses.

Parameters: Main slots `param541`-`640` (order `641`-`650`), Bus 1 `651`-`750` (order `751`-`760`), Bus 2 `761`-`860` (order `861`-`870`), channel outputs
`871`-`879`, bus levels `880`/`881`. The old fixed-chain parameters were removed; presets saved before the racks are converted when loaded.
Sources: `tools/rack/rack_dsp.cmajor.part` (DSP), `tools/rack/apply_rack_patch.py` (rebuilds `patch/Eisenpuls_Synth.cmajor` from the pre-rack source
`542767d`), `tools/rack/apply_rack_ui.py` (first UI step, since extended by hand). Tests: `tools/rack/test_rack.py` (audio, needs a build of
`tools/rack/dsp_host.cpp`) and `tests/fxrack.test.js`.

## UI embedded in cmajor_plugin.cpp
`cmajor_plugin.cpp` is generated from `patch/` (DSP and UI together). After changing `patch/`, regenerate it as described above.

 LFOs and drag-and-drop modulation

* Top tabs **OSC / FILTER / FX / MIXER**; OSC has a sub tab row (Synth, Sampler 1, Sampler 2, WT 1-3).
* A collapsible strip at the bottom holds **MOD** (10 envelopes with an ADSR display, 10 LFOs with a shape editor) and **MATRIX** (the 20-slot matrix).
* **Drag an LFO / ENV / VEL / KEY / RND handle onto a knob** to create a modulation slot (first free matrix slot). The knob shows a coloured ring, and a dot with the number of sources; click the dot to change the amount or remove it. Targets are listed in `MOD_TARGET` in `patch/index.js`.
* **LFO shape editor**: click to add a point, drag to move, double-click a point to delete it, drag the diamond on a segment to bend it, optional grid snap. The shape menu holds the 6 built-in waves plus drawn presets. Drawn shapes are sent to the DSP as a 256-point table (`lfoShapeLoad`), and saved per plugin instance and in presets.
* Per LFO: **Mode** Free / Trig (restart per note) / Env (one-shot), **Rate** in Hz or tempo sync with a division, **Delay**, **Rise** (fade-in), **Smooth**, **Phase**.
* Tests: `cd tests && npm test` (also `modui.test.js`).
* **Window size**: the dropdown in the top bar (75% - 200% of 1180x760) resizes the plugin window through a native `njoResize` hook (`cmaj_PatchWebView.h` / `cmaj_JUCEPlugin.h`). It only shows up inside the plugin; dragging the window edge also works and the UI scales to fit. The size is stored with the plugin state.
