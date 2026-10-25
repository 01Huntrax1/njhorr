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
- PRESET bar under the title: previous / next, the preset name (click: dropdown with folders, save, rename, move, delete, favorites), SAVE.
- VAULT (dropdown): samples and wavetables you load into any oscillator are added automatically; add more files, rename, delete, and load them into Sampler 1/2 or Wavetable 1-3. A preset remembers which vault file each oscillator used.

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

## Native UI (JUCE C++) and the WebView fallback
The plugin window is now a native JUCE editor written in C++ (`native_ui/`, see `native_ui/README_UI.md`). It is the default
(`-DNJOHRR_NATIVE_UI=ON`). The old WebView UI (`patch/index.js`) is still in the repo as a fallback: configure with
`-DNJOHRR_NATIVE_UI=OFF` to build the plugin with it. The native UI needs `juce_audio_formats` (already linked by CMake) and
no WebKit at runtime. Sound/preset folders and the `.njopreset` format are the same for both UIs, but the native UI only
loads its own stored state keys, and old (pre-slot-rework) presets do not load in either.
Window size: drag the corner (fixed aspect) or use the size dropdown (75-200%).
Known limits: compressed formats (mp3/ogg) depend on what JUCE decodes on your platform, CAF is only decoded by the JS UI.

## Layout
Three pages in the rail on the left, top to bottom: **1 Synth** (OSC 1-6, FM matrix, Global as tabs along the top), **2 Effects** (the three FX racks) and **3 Modulation** (the 20-slot matrix plus the envelope and LFO editors). The envelope / LFO strip stays at the bottom of the Synth and Effects pages so handles can be dragged onto knobs.

## Oscillator slots, per-slot filter/distortion and the FM matrix
The oscillator section is six identical slots (OSC 1-6). Each slot's **Source** is one of:
* **Wavetable** - position, unison (voices/detune/blend), two warp stages.
* **Sampler** - root key, start/end, loop, key tracking.
* **Plaits** - all 24 engines of Mutable Instruments Plaits, ported to Cmajor (`tools/plaits/`) and checked sample by sample against the original C++ (`python3 tools/plaits/compare.py <engine>`; see `tools/plaits/PORTING.md`). The knobs are the engine's Harmonics / Timbre / Morph and follow the engine's own meaning.

**Pages:** each oscillator page (OSC 1-6) holds Source, Tune and Output; the **FILTER** and **DIST** tabs open the filter and the distortion of one oscillator on their own pages (chips A-F switch the oscillator): a large response / transfer-curve display, the controls, and a table card. The **FILTER / WAVEFILTER** and **DISTORTION / WAVEDISTORTION** switches next to the type lists change a slot between the normal types and its table (filter table / shaper table); the table card shows all frames of the table behind each other with the frame at *Table Pos* in front, the drop zone loads your own table and the card dims while the table is not active. Every slot has its own 30-type filter (with its own envelope), a distortion (Off + 6 types), level, pan and output (Main / Bus 1 / Bus 2). Signal flow per slot: **source -> filter -> distortion -> FM / PM matrix and output**; the *Dist vs Filter* switch (Post / Pre) puts the distortion before the filter instead, and the filter and distortion can each be switched off. The FM / PM matrix modulators are the processed (filtered + distorted) slot outputs. The old mixer is replaced by the **FM / PM / PD page**: three graphical 6x6 node matrices (row = modulator, column = carrier, the diagonal nodes carry self feedback): **FM** (exponential frequency modulation, +-4 octaves at 100%), **PM** (phase modulation) and **PD** (phase distortion: the modulator moves the break point of a two-segment phase warp of the carrier, like the Casio CZ; wavetable and sampler slots only, Plaits slots ignore it). Every amount runs from **0 (off) to 100 (%)** and every cell is also a **modulation matrix destination** (dest list entries `FM A > B`, `PM ...`, `PD ...` = 108 extra destinations, 60..167, plus 168..179 for the table positions and 180..185 for the Frequency knobs; a full-amount modulation moves the cell by +-50 points); **drag an LFO / ENV / VEL / KEY / RND handle straight onto a matrix cell (or a feedback box)** to modulate it: the cell lights up while you hover, a coloured dot (with the source count) marks modulated cells, and clicking the dot reopens the amount popup; the parameters are `FM 1 to 1` ... (ids 1400+), `PM` (1440+) and `PD` (1480+). **RM / AM page (second matrix page):** the tab next to FM / PM / PD holds two more 6x6 matrices with the same handling (click a dot, drag up / down, double-click to clear, self-modulation on the diagonal, drop modulation handles on cells): **RM** (ring modulation: the carrier is multiplied by the modulator, so the carrier and modulator themselves disappear and only sum and difference tones remain) and **AM** (amplitude modulation: the carrier is multiplied by the modulator mapped to 0..1, so the carrier stays and sidebands are added). Amount 0 = off, 100 = full depth; both act on the processed slot outputs like FM. Parameters `RM n to m` (ids 1520+) and `AM n to m` (1560+); both are modulation destinations (`RM A > B` = dest 186..221, `AM A > B` = 222..257). **RM / AM page:** a second matrix page (tab *RM / AM*) holds two more 6x6 matrices: **RM** (ring modulation: the carrier is multiplied by the modulator's output, so only sum and difference tones remain) and **AM** (amplitude modulation: the carrier is multiplied by the unipolar modulator, 0..1). Same handling as FM / PM / PD (0 = off .. 100 %, drag modulation sources onto cells); parameters `RM n to m` (ids 1520+) and `AM n to m` (1560+), mod matrix destinations 186..221 (RM) and 222..257 (AM). **Frequency knob and Freq modulators:** every oscillator has a **Frequency** knob (Tune card; 0 = Off, the key pitch is used, otherwise a fixed frequency from 20 Hz to 20 kHz on a log scale; octave / semitone / fine still add to it). There are **10 Freq modulators** (bottom strip tab **FREQ**, and a FREQ tab on the modulation page): each is a curve of *frequency over time* (log axis 20 Hz - 20 kHz, drawn like the LFO shapes: click = add point, drag = move, double-click = delete, drag the dot between two points = curve) with **Retrig** (restart on every note, otherwise free running), **Loop**, **Rate** (length of the curve, 5 ms - 10 s) and **Transpose** (+-48 semitones). Their handles (`FRQ 1` ... `FRQ 10`, matrix sources 24..33) can only be dropped on the **cutoff knobs** and the **Frequency knobs** (matrix destination `OSC n Frequency` = 180..185); the amount scales the curve: at amount 1 the curve moves the target over the whole 20 Hz - 20 kHz range (about 10 octaves). With the Frequency knob on Off the curve adds octaves to the key pitch (a pitch envelope for kicks and zaps); with a Frequency set it moves that frequency. The curves are saved with the plugin state and in presets (`frq`; parameters `Freq Mod n Rate / Transpose / Retrig / Loop` = ids 1600+4n). **Filter and Distortion pages:** the filter and the distortion of every oscillator have their own pages (tabs *FILTER* and *DIST*, chips A-F pick the oscillator; the OSC pages keep source, tune and output). Each page shows the response / transfer curve, the controls, a **Filter | Wavefilter** (or **Distortion | Wavedistortion**) switch that selects the plain or the table type, and a table card with a view of all frames, the loader (click or drop a wavetable file) and **Table Pos**. **Wavefilter and Wavedistortion (tables):** the last entry of every slot's filter *Type* list is **Wavefilter** and the last entry of the distortion *Type* list is **Wavedistortion**. Wavefilter is a bank of 24 band-pass filters (0.4 octave apart, 30 Hz to about 18 kHz) whose gains come from a *filter table*: one frame of the table is a gain curve along a frequency axis centred on the cutoff, so the cutoff slides the curve, resonance narrows the bands and **Table Pos** morphs between the frames. The band gains are recomputed every 8 samples and smoothed. Controls (in the table card, also saved in the plugin state; ids 1049..1055 + 64 * slot): **Mix** (dry / wet), **Range** (2 - 14 octaves covered by the frame, default 8), **Warp** (bends the frequency axis: + widens the middle of the frame, - the edges), **Contrast** (raises the gains to a power: + deeper dips and sharper peaks, - flatter), **Tilt** (+-6 dB per octave around the cutoff), **Spread** (shifts the curve down by up to an octave on the left and up on the right channel for stereo sources) and **Gain Law** (how a table value becomes a gain: *Linear* = (value + 1) / 2, *Bipolar* = the value itself, so negative values invert a band and can cancel / notch, *dB* = -60 dB at -1 up to 0 dB at +1). The response display follows all of them. Wavedistortion is a waveshaper whose transfer curve (input -1..1) is a frame of a *shaper table*; drive scales the input, mix blends with the dry signal, **Table Pos** morphs between frames. Both come with 16 built-in frames (filter: LP, BP, HP, notch, peak, combs, vowels, tilt; shaper: tanh, clip, sine folds, Chebyshev, rectifier, staircases ...) and each slot can load its own tables: click or drop a wavetable file on the drop zone of the table card (every file the wavetable loader reads, `.vitaltable` too; frames are cut like wavetable frames and reduced to 512 points, 64 frames max; the cross returns to the built-in table). The tables are saved with the plugin state (not in presets) and Table Pos is a modulation destination (`OSC n Wavefilter Pos` / `OSC n Wavedistortion Pos`, dest 168..179). **Duplicate notes:** the DSP ignores a note-on for a note number that is already sounding (held, not yet released), so only one voice per note (e.g. one C5) plays at a time; after its note-off it can be played again. The old filter section, Synth osc 1/2, Supersaw, EQ and mixer no longer exist. **Presets from earlier versions do not load** (new layout and parameter ids).

Wavetables work like Vital's:
* **Frames**: 2048 samples per frame, up to **128 frames** per slot (longer files are thinned out evenly). The *Frame Size* selector (256 ... 4096) says how the file is cut into frames; every frame is resampled to 2048 samples and its DC removed. A file whose length is a multiple of 2048 (4096) is cut that way automatically, other lengths are treated as one single cycle. Wavetable files are **not** sample-rate converted (their frames are cycles, not audio).
* **Band-limited playback**: each frame gets a mip chain (2048 ... 8 samples per cycle, built in the background after loading, about 100 ms for 128 frames). The note frequency picks the level, so high notes do not alias; frames are crossfaded with the Position knob and read with cubic interpolation.
* **`.vitaltable`** files (Vital's own format) load too: the keyframes of the first Wave Source are interpolated over 128 frames. Vital's modifier components (wave warp, FFT filters ...) are not applied.
* The saw / sine test tables in `tools/osc/dsp_host.cpp` (`saw2k`, `morph2k`, `big`) and the alias / frame tests in `tools/osc/test_osc.py` cover this.

Notes and limits:
* Loading audio: WAV (PCM 8-32 bit, float, A-law, mu-law, IMA / MS ADPCM, RF64), Wave64, AIFF / AIFF-C, Sun .au, Core Audio .caf and FLAC are decoded by the plugin's own decoders (`tools/audio/decode.js`, checked against ffmpeg in `tests/audio.test.js`). mp3 / ogg / opus / aac / m4a go through the web view's decoder, so they work where the host's web view can play them; headerless .raw / .pcm files are read as 16 bit mono.
* Plaits runs in 12-sample blocks like the original, with Plaits' reference constants at the host sample rate. FM into a Plaits slot is therefore block-rate pitch modulation (cleaner for slow modulation than for audio-rate FM).
* Plaits' "unpatched trigger" sustain modes of the percussive/string/six-op engines are omitted (the synth always supplies a trigger). Wave terrain has the 8 built-in terrains.
* Plaits state is allocated per voice and slot (48 instances); the String engine is the heaviest (about 190k floats in total).
* Sample memory is 96000 samples, wavetable memory 262144 samples per slot; both are stored per plugin instance (see below); the DSP is regenerated with `tools/osc/build_osc.py`, audio tests: `tools/osc/test_osc.py --host <dsp_host>`.
* The window resize hook has not been tested in a real plugin host.

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

## Performance notes

- The DSP is profiled with `tools/osc/bench.py` (scripts for `dsp_host`) and `valgrind --tool=callgrind`; optimisations are checked to give bit-identical audio.
- Per-sample costs removed: the modulation matrix sums only clear / visit the slots that are in use, the FM / PM / PD / RM / AM matrix loops are skipped while no amount is set, the mip level of the unison voices is looked up once per oscillator when all voices share it, and the hot state arrays are sized to powers of two so every `.at()` index wrap is a mask instead of a division. Together about 35-40 % fewer instructions per sample for typical patches.
- The native UI keeps the parameter objects it polls (one string lookup per parameter, not one per parameter per timer tick).
- Memory: the DSP state is about 50 MB (FX delay arena 24 MB, wavetable mips 13 MB, wavetable frames 6 MB, tables / samples about 4 MB).

## Preset and Vault dropdowns (native UI)

The Bank and Vault windows were replaced by dropdown menus in the style of Tone2 Icarus (the files still live in sub folders of `Documents/Njohrr/{Presets,Samples,Wavetables}`):

- **Preset name (click, or the arrow buttons for previous / next):** *Init*, *Favorites*, then every folder as a nested submenu with its presets (the current one is ticked, favourites have a `*`). Below: *Save*, *Save as new in* (folder picker, then a name), *Rename preset*, *Move preset to*, *Add to / Remove from favorites*, *Delete preset* (asks), *Folders* (*New folder in*, *Rename folder*, *Delete folder*), *Show presets folder*, *Rescan*.
- **VAULT button (bar) and the VAULT button of each oscillator:** *Load into* (bar only: which oscillator), *Favorites*, the files as nested folder submenus (the oscillator button lists the wavetables or samples of that oscillator directly; the bar lists *Samples* and *Wavetables*), then *Add files* (pick the folder first), *Loaded file of OSC n* (rename, move, favourite, delete), *Folders*, *Show vault folder*, *Rescan*. A click on a file loads it into the oscillator.
- **Storage:** favourites live in `Documents/Njohrr/library.json`; presets store a content hash of every vault file they use, so a preset finds its samples again even after the files were renamed and moved outside the plugin (first by folder + name + size, then by name + size, then by hash). Renaming or moving inside the plugin keeps slots, the current preset and favourites pointing at the right files.
- Files of earlier versions simply sit in the root folders. The web UI (JS fallback) still shows only the root folders.
