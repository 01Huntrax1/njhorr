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

## Factory wavetables
`wavetables/Factory/*.wav` holds 14 ready-made wavetables (mono, 16 bit, one cycle = 2048 samples per frame): Basic Shapes (sine, triangle, saw, square, two pulses, half/full-wave rectified sine), Sine to Saw, Sine to Square, Sine to Triangle, Triangle to Saw, Saw to Square, PWM, Hard Sync, Harmonics, Odd Harmonics, FM Sine, Resonant Saw, Vowels, Organ. Every frame is built additively (band-limited, DC-free, same peak) by `tools/wavetables/build_factory.py`; the saw is a falling ramp so the saw/square morphs stay in phase.
The plugin writes them itself: on the first start the preset bar creates `Documents/Njohrr/Wavetables/Factory/` with all 14 files (generated in C++ by `native_ui/NjoFactory.cpp`, a port of the Python script; `native_ui/test/factory_test.cpp` checks that both produce the same samples). A marker file `.factory-1` in that folder stops it from running again, so files you delete do not come back; delete the marker to reinstall. The files then show up in the Vault under Wavetables.

## Waveguide source
Source type 6, **Waveguide**, has five physical models. All loops are tuned with the exact phase delay of their filters, so the pitch follows the keyboard (measured within about 2 cents up to A4, also with Stretch).

- **Karplus-Strong:** a plucked string. A delay line with a damping low-pass (Tone), a two stage stiffness allpass (Stretch: sharper partials, stronger on high notes), an optional in-loop saturation (Nonlinear) and Tension (the pitch rises with the vibration energy and falls back, a tension-modulated string). Hardness softens the pluck, Pluck Pos moves the pluck point, Pluck Noise mixes noise into the pluck.
- **Bowed String:** two delay lines (neck and bridge) and the bow friction table. Bow Pressure, Bow Pos (bow to bridge), Bow Noise, Bow Offset (asymmetry) and Bow Attack; it sustains while the key is held.
- **Clarinet:** a reed table in an inverting bore loop of half the period (so the note is an octave above a plain loop of the same length). Breath runs from just above the oscillation threshold to just below the closing pressure of the reed for the chosen Reed Stiff and Reed Offset; Breath Noise, Breath Attack.
- **Banded Waveguide:** four band-pass / delay loops, struck by a smooth pulse. Mode Ratios morph from bar (1, 2.76, 5.40, 8.93) over glass (1, 2.32, 4.25, 6.63) to the harmonic series; Hardness is the pulse length, Strike Pos weights the bands, Strike Noise.
- **Drum:** 12 modes of a circular membrane (ratios 1, 1.59, 2.14, 2.30, 2.65, 2.92 ... from the Bessel zeros), weighted by the strike radius (Bessel functions, so a centre hit excites the symmetric modes), Stiffness widens the mode spacing. **Tension** is the tension modulation of real drums: the pitch is raised right after the strike and falls back as the head calms down (up to +50 %). **Snare** adds wires that rattle with the head; **Shell / Shell Tune** are two body resonances.
- All models: Decay (0.05 .. 20 s), Tone, Body / Body Tune (two resonances), Drive, Vel > Excite, Key Decay (higher notes ring shorter). Every knob shows the name of the selected model and unused knobs are dimmed.
- Parameters: `2200 + 16 * slot + j`, mod destinations 636..731 (`OSC n Waveguide ...`). Code: `tools/osc/build_wg.py` (DSP, `native_ui/NjoWg.h`), `tools/osc/apply_wg_ui.py` (patch/index.js), tests in `tools/osc/test_osc.py` (pitch, stability, every knob, mod destinations).
- Delay memory: 6 slots x 16384 floats per voice (8 voices); the lowest note is limited to about 12 Hz at 48 kHz.
- Sources of the models: the Faust-STK physical models (clarinet reed table, bowed string, banded waveguides), tension modulation of drum membranes (Marogna / Avanzini / Bank) and the Bessel modes of the circular membrane. The algorithms are written from scratch for this synth.

## JP-8080 source
Source type 7, **JP-8080**, offers the oscillator waveforms of the Roland JP-8000 / JP-8080. The knobs show the names that belong to the selected waveform and dim the unused ones.

- **Saw, Square** (Pulse Width, PWM Depth / Rate with an internal sine LFO), **Triangle, Sine, Noise** (white).
- **Spectrum:** 32 harmonics with a Tilt (n^-0.3 .. n^-2.5) and a formant Peak (harmonic 2 .. 22); the harmonics above the Nyquist limit are left out.
- **Super Saw:** seven free-running saws with the detune offsets of the analysed JP-8000 (Szabo), the detune curve and the centre / side mix curves; Detune, Mix, Width (0 = mono, 1 = the three lower saws left, the three upper right), and a high-pass that follows the pitch.
- **Feedback Osc:** a sine whose phase is modulated by its own last two outputs (Feedback up to 4.5 rad) with a second-harmonic Color.
- **Tri Mod:** a triangle whose phase is modulated by one of its own harmonics (Mod Ratio 1 .. 8, Mod Depth).
- All waveforms: Noise (dark), Sub (square, one octave below), Drive (tanh).
- Parameters: `2300 + 16 * slot + j`, mod destinations 732..827 (`OSC n JP ...`). Code: `tools/osc/build_jp.py` (DSP, `native_ui/NjoJp.h`), `tools/osc/apply_jp_ui.py` (patch/index.js), tests in `tools/osc/test_osc.py` and `tests/osc.test.js`.
- State: Voice.jps, 6 slots x 64 floats per voice.

## Granular source
Source type 8, **Granular**, plays grains of the sample memory of its slot (load a sample like for the Sampler: drop zone, Vault, Root Note). Up to 12 grains sound at once per voice; their pitch follows the key relative to the Root Note.

- **Position** of the grain start, **Scan** (moves the position through the sample, 1 = real time speed, negative = backwards), **Spray** (random position), **Vel > Position**.
- **Size** (5 .. 500 ms), **Density** (1 .. 200 grains per second), **Timing Jitter** (0 = regular), **Window** (Hann .. trapezoid), **Reverse** (probability of a backwards grain), **Pitch Spread** (up to 12 semitones at random), **Pan Spread**, **Drive**. The level is normalised by the grain overlap.
- Parameters: `2400 + 16 * slot + j` (12 used), mod destinations 828..923. Code: `tools/osc/build_gr.py`, `native_ui/NjoGr.h`.

## Additive source
Source type 9, **Additive**, sums up to 64 partials. Each partial is a rotating phasor (no sine call per sample); the amplitudes are recomputed every 32 samples and smoothed.

- Eight spectra: Saw, Square, Triangle, Organ (drawbars 1, 2, 3, 4, 6, 8), Bell, Vowel (three formants at 650 / 1100 / 2600 Hz), Brass, Hollow (every third partial missing). **Spectrum A**, **Spectrum B** and **Morph** blend two of them.
- **Partials** (1 .. 64), **Tilt** (-1 brighter .. +1 darker), **Odd / Even** (+1 only odd partials, -1 only even), **Inharmonicity** (stiff string stretch, partial n at n f sqrt(1 + B n^2)), **Formant** position and gain, **Shimmer** (slow amplitude movement per partial, with rate), **Partial Decay** (the high partials fade first), **Width** (odd partials left, even right), **Vel > Bright**, **Drive**.
- Parameters: `2500 + 16 * slot + j` (15 used), mod destinations 924..1019. Code: `tools/osc/build_ad.py`, `native_ui/NjoAd.h`; both generators share `tools/osc/srcgen.py`, the web UI part is `tools/osc/apply_gradd_ui.py`.
- State: Voice.grs (6 x 96 floats) and Voice.ads (6 x 512 floats) per voice.

## Spectral source
Source type 11, **Spectral**, is a bank of up to 64 harmonic partials (like the Additive source) whose amplitudes follow a spectral envelope. Two modes (**Mode** switch):
* **Resynth**: the sample memory of the slot (load a sample like for the Sampler; the VAULT button and the drop zone work as there) is analysed with a 2048-point FFT, the envelope is smoothed on a 1/24 octave grid (four blur levels) and imposed on the harmonics of the key pitch: the timbre of the sample at any pitch, held for ever. **Position** / **Position B** pick two frames, **Morph** blends them, **Scan** moves both through the sample (1 = real time, 0 = freeze, negative = backwards, wraps), **Blur** smears the envelope (1/6 octave .. 1.5 octaves), **Shift** moves the envelope up or down by up to an octave while the pitch stays, **Vel > Pos** adds the velocity to the positions. A 1 kHz sine sample, for example, gives a formant at 1 kHz on every key. This is envelope transfer, not a phase vocoder: the sample's own pitch and phases are not kept.
* **Spectrum**: no sample needed. Two formant peaks (**Position** and **Position B** = their frequency, 100 Hz .. 9.7 kHz, **Morph** blends, **Blur** = width).
Both modes: **Tilt**, **Harmonics** (4 .. 64 partials), **Odd / Even**, **Comb** (notches every 2nd .. 8th partial), **Contrast** (sharpens peaks), **Jitter** (slow random partial wobble), **Spread** (inharmonic stretch), **Width** (odd and even partials to the two sides; 0.5 = mono).
Parameters `SP_BASE (2700) + 16 * slot + j`, mod destinations 1116 + 16 * slot + j. The analysis is cached per slot (8 frames) and cleared when a sample is loaded; a frame costs one FFT. Code: `tools/osc/build_sp.py`, `tools/osc/apply_sp_ui.py`, tests in `tools/osc/test_osc.py`.

## Bipolar mode of the modulators
Envelopes and Velocity are unipolar (0..1); every one now has a **Unipolar / Bipolar** switch (modulation page, under the envelope display: the switch of the selected envelope and one for VELOCITY). Bipolar maps the value to `value * 2 - 1` (-1..1), so a sustained envelope at 0.5 modulates by 0 and the release / start pull in the opposite direction; it applies to every matrix slot and drop target that uses the source, per voice and global. Key and Random are bipolar already (Freq modulators are unchanged); LFOs have their own switch (below). The envelope display switches its axis to +1 / 0 / -1. Parameters `3100 + i` (Env 1-10) and `3110` (Velocity), default Unipolar, so existing patches sound the same. Code: `tools/mod/build_bip.py`, tests in `tools/osc/test_osc.py`.

**LFO polarity:** every LFO has a **Unipolar / Bipolar** switch (modulation page, under the LFO display, for the selected LFO). Bipolar (default, as before) is -1..1; Unipolar maps the LFO to `(v + 1) / 2` = 0..1, so it only pushes the target in one direction (a sine at 100% amount sweeps between 0 and +1 instead of -1 and +1). It applies to every matrix slot and drop target, per voice and global; the shape editor still shows the raw shape. Parameters `3111 + i` (LFO 1-10), default Bipolar, so existing patches sound the same. Code: `tools/mod/build_lfobip.py`, test in `tools/osc/test_osc.py`.

## SoundFont source
Source type 12, **SoundFont**, is a multisample player for SoundFont 2 files (`.sf2`; SF3 / compressed files are refused). Drop a file on the drop zone (or click it): the native UI reads the presets of the file, builds the **zone table** of the default preset (bank 0 program 0, otherwise the first) and sends it with the audio to the DSP; the **PRESET** button lists all presets of the file and switches. The display shows the zone map (keys across, velocity up).
* **Zones:** key range, velocity range, root key (generator or sample header), coarse / fine tuning plus the sample correction, scale tuning, initial attenuation, pan, loop mode and loop points (also the sample offsets of the file's generators) and the volume envelope (attack, hold, decay, sustain, release) are used. A note plays every matching zone (up to 4 layers, e.g. velocity layers cross-faded by range or stereo pairs). Modulators, filters, LFOs and effects of the file are ignored. Preset and instrument generators are merged as in the SF2 spec (instrument zone over instrument global, preset values added on top, ranges intersected).
* **Knobs:** **Gain** (+-12 dB), **Vel Sens**, **Attack / Decay / Sustain / Release** (scale the zone's own envelope), **Loop** (Zone = as in the file, Off = play each sample once, On = loop every zone that has loop points), **Stereo** (0 = mono centre, 1 = the zones' pan), **Start** (offset into every sample), **Drive**.
* **Limits:** up to 64 zones per preset (more are thinned: every second key group is dropped and its neighbour covers the keys) and 262144 samples of audio per slot (above that every sample is decimated by 2, up to 3 times, then shortened); the status line says what was reduced. The audio is shared between zones that use the same sample region and loop. The bank is stored in the plugin state as float32 together with the file path and the preset number (the vault does not know the .sf2 kind; a moved file only loses the preset menu).
Parameters `SF_BASE (2800) + 16 * slot + j` (10 used), mod destinations 1212 + 16 * slot + j. Voice state: `Voice.sfl` (4 layers x 24 floats per slot). Code: `tools/osc/build_sf.py` (DSP), `native_ui/NjoSf2.cpp` (file parser), `native_ui/NjoMemory.cpp` (kind 7), tests `tools/osc/test_osc.py`, `native_ui/test/sf2_test.cpp` (with `tools/osc/mk_sf2.py`). The browser fallback UI has the controls but no loader.

## Modal Drum source
Source type 10, **Modal Drum**, is a drum in the manner of modal drum models (MODO DRUM, V-Drums, Chromaphone). The pitch follows the key.

- **Batter head:** 12 modes of a circular membrane (Bessel zeros), weighted by the **Hit Position** (centre .. rim); **Decay**, **Head Tone** (coated .. clear: damping of the upper modes), **Edge** (sharp .. round bearing edge), **Stick** (felt .. hard, a Hann pulse) and **Vel > Stick**.
- **Resonant head:** the same 12 modes, tuned by **Reso Tune** (+-7 semitones) and excited by the batter head and by the air pressure of the hit; **Reso Head** is its level.
- **Shell:** 6 modes excited by the batter head; **Size** and **Shell Depth** set their pitch and ring time, **Shell** the level.
- **Snare wires:** noise that only rattles while the resonant head moves faster than a threshold (**Snare Tension**), then dies quickly.
- **Sympathetic:** the output of the other Modal Drum slots (all voices, previous sample) shakes the heads of this slot, so a kick makes a snare slot buzz. Set up a kick in one slot and a snare in another.
- **Tension:** the pitch rises with the vibration energy (tension modulation), **Drive** saturates.
- Parameters: `2600 + 16 * slot + j`, mod destinations 1020..1115 (the mod value array grew to 2048 entries). Code: `tools/osc/build_dk.py` (DSP, `native_ui/NjoDk.h`), `tools/osc/apply_dk_ui.py`. Research notes: modal synthesis of membranes with tension modulation (Marogna / Avanzini / Bank), reso head and shell coupling and snare contact as in the published modal drum models; MODO DRUM itself is closed source.
- State: Voice.dks, 6 x 192 floats per voice.

## Where samples and wavetables are saved
Each plugin instance keeps its own samples and wavetables in the plugin's stored state, so they are saved with the DAW project and
are never shared between instances (loading a kick into Sampler 1 in one instance does not touch another instance).
They are stored as 16-bit audio, roughly 260 KB of project data per loaded sampler or wavetable memory.
The Sound Vault folders (Documents/Njohrr/...) are a shared library of files; which vault file an oscillator uses is also per instance.
Regression test: `cd tests && npm install && npm test`.

## FX rack
There is one FX rack of 16 slots (see *16 effects per rack* below): **Main**. (The Bus 1 and Bus 2 racks were removed.) Any effect (Distortion, Bit Crush, Delay,
Chorus, Flanger, Phaser, Tremolo, Reverb, Filter with all 30 filter types of the Filter page, EQ, Compressor) fits in any slot, with on/off, mix,
a mode selector and up to six knobs. Drag the grip (or use the arrows) to change the order within the rack; the signal runs top to bottom.

Routing: the Output selector of the oscillators is gone from the native editor. Everything plays through the Main rack, which feeds Width / Tone / Output.
Old presets that route a source to Bus 1 / Bus 2 keep sounding: the parameters (`out`, `880` / `881`) stay in the file but all three buses are summed into Main
(the bus racks and levels are no longer processed, their stored slot settings are ignored).

Parameters: Main slots `param541`-`640` (order `641`-`650`), Bus 1 `651`-`750` (order `751`-`760`), Bus 2 `761`-`860` (order `861`-`870`), channel outputs
`871`-`879`, bus levels `880`/`881`. The old fixed-chain parameters were removed; presets saved before the racks are converted when loaded.
Sources: `tools/rack/rack_dsp.cmajor.part` (DSP), `tools/rack/apply_rack_patch.py` (rebuilds `patch/Eisenpuls_Synth.cmajor` from the pre-rack source
`542767d`), `tools/rack/apply_rack_ui.py` (first UI step, since extended by hand). Tests: `tools/rack/test_rack.py` (audio, needs a build of
`tools/rack/dsp_host.cpp`) and `tests/fxrack.test.js`.

## Native UI (JUCE C++) and the WebView fallback

Look: a hunter-tech theme defined in `native_ui/NjoTheme.cpp` (plates with cut corners, rivets, etched marks, hexagonal knobs with blade pointers). Surfaces are procedural textures generated at start-up (brushed steel plates and window background, red plasma veins on active elements, grained glass for displays), so there are no image files to ship. The colours are in `NjoTheme.h`.

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
* **Wave Terrain** - a two dimensional terrain read along an orbit (see "Wave Terrain source" below).

**Pages:** each oscillator page (OSC 1-6) holds Source, Tune and Output; the **FILTER** and **DIST** tabs open the filter and the distortion of one oscillator on their own pages (chips A-F switch the oscillator): a large response / transfer-curve display, the controls, and a table card. The **FILTER / WAVEFILTER** and **DISTORTION / WAVEDISTORTION** switches next to the type lists change a slot between the normal types and its table (filter table / shaper table); the table card shows all frames of the table behind each other with the frame at *Table Pos* in front, the drop zone loads your own table and the card dims while the table is not active. Every slot has its own 30-type filter (with its own envelope), a distortion (Off + 6 types), level, pan and output (Main / Bus 1 / Bus 2). Signal flow per slot: **source -> filter -> distortion -> FM / PM matrix and output**; the *Dist vs Filter* switch (Post / Pre) puts the distortion before the filter instead, and the filter and distortion can each be switched off. The FM / PM matrix modulators are the processed (filtered + distorted) slot outputs. The old mixer is replaced by the **FM / PM / PD page**: three graphical 6x6 node matrices (row = modulator, column = carrier, the diagonal nodes carry self feedback): **FM** (exponential frequency modulation, +-4 octaves at 100%), **PM** (phase modulation) and **PD** (phase distortion: the modulator moves the break point of a two-segment phase warp of the carrier, like the Casio CZ; wavetable and sampler slots only, the other sources ignore it). Every amount runs from **0 (off) to 100 (%)** and every cell is also a **modulation matrix destination** (dest list entries `FM A > B`, `PM ...`, `PD ...` = 108 extra destinations, 60..167, plus 168..179 for the table positions and 180..185 for the Frequency knobs; a full-amount modulation moves the cell by +-50 points); **drag an LFO / ENV / VEL / KEY / RND handle straight onto a matrix cell (or a feedback box)** to modulate it: the cell lights up while you hover, a coloured dot (with the source count) marks modulated cells, and clicking the dot reopens the amount popup; the parameters are `FM 1 to 1` ... (ids 1400+), `PM` (1440+) and `PD` (1480+). **RM / AM page (second matrix page):** the tab next to FM / PM / PD holds two more 6x6 matrices with the same handling (click a dot, drag up / down, double-click to clear, self-modulation on the diagonal, drop modulation handles on cells): **RM** (ring modulation: the carrier is multiplied by the modulator, so the carrier and modulator themselves disappear and only sum and difference tones remain) and **AM** (amplitude modulation: the carrier is multiplied by the modulator mapped to 0..1, so the carrier stays and sidebands are added). Amount 0 = off, 100 = full depth; both act on the processed slot outputs like FM. Parameters `RM n to m` (ids 1520+) and `AM n to m` (1560+); both are modulation destinations (`RM A > B` = dest 186..221, `AM A > B` = 222..257). **RM / AM page:** a second matrix page (tab *RM / AM*) holds two more 6x6 matrices: **RM** (ring modulation: the carrier is multiplied by the modulator's output, so only sum and difference tones remain) and **AM** (amplitude modulation: the carrier is multiplied by the unipolar modulator, 0..1). Same handling as FM / PM / PD (0 = off .. 100 %, drag modulation sources onto cells); parameters `RM n to m` (ids 1520+) and `AM n to m` (1560+), mod matrix destinations 186..221 (RM) and 222..257 (AM). **Frequency knob and Freq modulators:** every oscillator has a **Frequency** knob (Tune card; 0 = Off, the key pitch is used, otherwise a fixed frequency from 20 Hz to 20 kHz on a log scale; octave / semitone / fine still add to it). There are **10 Freq modulators** (bottom strip tab **FREQ**, and a FREQ tab on the modulation page): each is a curve of *frequency over time* (log axis 20 Hz - 20 kHz, drawn like the LFO shapes: click = add point, drag = move, double-click = delete, drag the dot between two points = curve) with **Retrig** (restart on every note, otherwise free running), **Loop**, **Rate** (length of the curve, 5 ms - 10 s) and **Transpose** (+-48 semitones). Their handles (`FRQ 1` ... `FRQ 10`, matrix sources 24..33) can only be dropped on the **cutoff knobs** and the **Frequency knobs** (matrix destination `OSC n Frequency` = 180..185); the amount scales the curve: at amount 1 the curve moves the target over the whole 20 Hz - 20 kHz range (about 10 octaves). With the Frequency knob on Off the curve adds octaves to the key pitch (a pitch envelope for kicks and zaps); with a Frequency set it moves that frequency. The curves are saved with the plugin state and in presets (`frq`; parameters `Freq Mod n Rate / Transpose / Retrig / Loop` = ids 1600+4n). **Filter and Distortion pages:** the filter and the distortion of every oscillator have their own pages (tabs *FILTER* and *DIST*, chips A-F pick the oscillator; the OSC pages keep source, tune and output). Each page shows the response / transfer curve, the controls, a **Filter | Wavefilter** (or **Distortion | Wavedistortion**) switch that selects the plain or the table type, and a table card with a view of all frames, the loader (click or drop a wavetable file) and **Table Pos**. **Wavefilter and Wavedistortion (tables):** the last entry of every slot's filter *Type* list is **Wavefilter** and the last entry of the distortion *Type* list is **Wavedistortion**. Wavefilter is a bank of 24 band-pass filters (0.4 octave apart, 30 Hz to about 18 kHz) whose gains come from a *filter table*: one frame of the table is a gain curve along a frequency axis centred on the cutoff, so the cutoff slides the curve, resonance narrows the bands and **Table Pos** morphs between the frames. The band gains are recomputed every 8 samples and smoothed. Controls (in the table card, also saved in the plugin state; ids 1049..1055 + 64 * slot): **Mix** (dry / wet), **Range** (2 - 14 octaves covered by the frame, default 8), **Warp** (bends the frequency axis: + widens the middle of the frame, - the edges), **Contrast** (raises the gains to a power: + deeper dips and sharper peaks, - flatter), **Tilt** (+-6 dB per octave around the cutoff), **Spread** (shifts the curve down by up to an octave on the left and up on the right channel for stereo sources) and **Gain Law** (how a table value becomes a gain: *Linear* = (value + 1) / 2, *Bipolar* = the value itself, so negative values invert a band and can cancel / notch, *dB* = -60 dB at -1 up to 0 dB at +1). The response display follows all of them. Wavedistortion is a waveshaper whose transfer curve (input -1..1) is a frame of a *shaper table*; drive scales the input, mix blends with the dry signal, **Table Pos** morphs between frames. Both come with 16 built-in frames (filter: LP, BP, HP, notch, peak, combs, vowels, tilt; shaper: tanh, clip, sine folds, Chebyshev, rectifier, staircases ...) and each slot can load its own tables: click or drop a wavetable file on the drop zone of the table card (every file the wavetable loader reads, `.vitaltable` too; frames are cut like wavetable frames and reduced to 512 points, 64 frames max; the cross returns to the built-in table). The tables are saved with the plugin state (not in presets) and Table Pos is a modulation destination (`OSC n Wavefilter Pos` / `OSC n Wavedistortion Pos`, dest 168..179). **Duplicate notes:** the DSP ignores a note-on for a note number that is already sounding (held, not yet released), so only one voice per note (e.g. one C5) plays at a time; after its note-off it can be played again. The old filter section, Synth osc 1/2, Supersaw, EQ and mixer no longer exist. **Presets from earlier versions do not load** (new layout and parameter ids).

Wavetables work like Vital's:
* **Frames**: 2048 samples per frame, up to **128 frames** per slot (longer files are thinned out evenly). The *Frame Size* selector (256 ... 4096) says how the file is cut into frames; every frame is resampled to 2048 samples and its DC removed. A file whose length is a multiple of 2048 (4096) is cut that way automatically, other lengths are treated as one single cycle. Wavetable files are **not** sample-rate converted (their frames are cycles, not audio).
* **Band-limited playback**: each frame gets a mip chain (2048 ... 8 samples per cycle, built in the background after loading, about 100 ms for 128 frames). The note frequency picks the level, so high notes do not alias; frames are crossfaded with the Position knob and read with cubic interpolation.
* **`.vitaltable`** files (Vital's own format) load too: the keyframes of the first Wave Source are interpolated over 128 frames. Vital's modifier components (wave warp, FFT filters ...) are not applied.
* The saw / sine test tables in `tools/osc/dsp_host.cpp` (`saw2k`, `morph2k`, `big`) and the alias / frame tests in `tools/osc/test_osc.py` cover this.

Notes and limits:
* Loading audio: WAV (PCM 8-32 bit, float, A-law, mu-law, IMA / MS ADPCM, RF64), Wave64, AIFF / AIFF-C, Sun .au, Core Audio .caf and FLAC are decoded by the plugin's own decoders (`tools/audio/decode.js`, checked against ffmpeg in `tests/audio.test.js`). mp3 / ogg / opus / aac / m4a go through the web view's decoder, so they work where the host's web view can play them; headerless .raw / .pcm files are read as 16 bit mono.
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

## Performance notes

- The wavetable and sampler buffers have power-of-two sizes (`wtMip` 4 194 304, `smpBuf` 1 048 576 floats), so every array read in the oscillator inner loop wraps with a mask instead of an integer modulo. Measured with `tools/osc/bench.py` and the offline DSP host (8 notes, 6 oscillators, 7 unison voices each, filters on, 4 s): 2.27 s → 1.78 s (-21 %), audio output bit-identical. The cost is about 5 MB more DSP state.
- The editor only polls the DSP while its window is open (see the sound persistence notes above).
- Known gap: drawn LFO / FREQ shapes only reach the DSP when an editor has been opened.

## Physical modelling source

Each oscillator slot has a fourth Source type, **Physical**: modal synthesis in the style of RipplerX. An exciter strikes two resonators, A and B, each a bank of 16 two-pole resonators (modes).

- **Exciter**: a mallet (an impulse through a one-pole low-pass; **Hardness** sets its cutoff, 200 Hz to 25 kHz) and a noise burst (**Noise Time** 2 ms to 3 s, same colour filter). **Noise** blends the two; a long Noise Time keeps the resonator driven (bowed or blown sounds).
- **Models** per resonator: String, Beam, Squared (square membrane), Membrane (circular, Bessel zeros), Plate, Drumhead, Marimba (tuned 1:4:10), Open Tube, Closed Tube (odd harmonics). The mode ratio tables are in `tools/phys/build_phys.py` and are generated into the DSP and into `native_ui/NjoPhys.h`.
- **Decay** is the decay time (T60) of the fundamental; **Material** sets how fast the upper modes die (0 = wood, high modes damp quickly; 1 = metal, all modes ring equally); **Hit** is the strike position (mode i is weighted by |sin(pi * hit * i)|, so 0.5 on a string removes the even harmonics); **Inharm** stretches the upper modes.
- **B Tune** moves resonator B by +-24 semitones, **A / B** blends the two. **Coupling**: Parallel (both are excited by the exciter) or Serial (A's output excites B).
- Mod matrix: every Physical parameter of every slot is its own destination (see *Mod matrix* below). The slot's filter, distortion, Tune (Octave, Semi, Fine, Key Track, Frequency), FM / PM and level work as for the other sources.
- Parameters: ids `1700 + 32 * slot + j` (16 per slot, in `layout.py` as `PHY`). The coefficients of the modes are recomputed every 64 samples, and only when the pitch or a parameter changed. A voice costs 32 resonators per sample for the slot.
- The mode display of the slot shows the ratio, strength and (dimmer = shorter) decay of every mode of A (red) and B (orange).

`tools/phys/build_phys.py` writes the DSP into `patch/Eisenpuls_Synth.cmajor` (idempotent); `tools/phys/apply_phys_ui.py` was the one-time edit of `patch/index.js`. Tests: `tools/osc/test_osc.py` (every model, pitch, decay, hit position, B tune, serial coupling, noise, extreme settings).

## FX page

The FX page (native editor) is laid out like a modern synth's effect page. The Main rack is shown; it holds up to 16 effects (the list scrolls) in the same parameters and processing order as before (presets are unchanged).

- **List** (left): the effects of the rack in processing order. Click an effect to open its page, the dot bypasses it, the arrows and the grip move it (drag to reorder). **+ ADD FX** opens a grid of all effect types; a new effect is appended to the end of the chain with its own default settings and selected.
- **Effect page** (centre): name, mode dropdown (for effects that have modes), ON / bypass, **REMOVE**, a display and large knobs for Mix and every parameter of the effect (all of them accept modulation drops). The displays follow the knobs and are schematic: Filter and EQ show the frequency response, Distortion the transfer curve of the chosen algorithm, Bit Crush the quantised sine, Delay the echo taps (with Ping-Pong), Chorus / Flanger / Phaser the modulation (the Phaser also its notches), Tremolo the gain shape of the chosen waveform, Reverb the decay with pre-delay, Compressor the transfer curve with threshold, ratio and makeup.
- The JS fallback UI (`patch/index.js`) still has the old row based rack.
- **Console effect** (FX type 17, after the console channel strips such as Sonic Sweep 2): input-transformer saturation followed by two sweepable parametric mid bands. Lo-Mid sweeps 45 Hz - 3 kHz, Hi-Mid 500 Hz - 18 kHz, both +-15 dB; **Drive** is the tanh transformer stage, **Age** adds an asymmetric bias (even harmonics) and rounds the highs. The mode sets the bandwidth of both bands (Wide, Medium, Narrow, Surgical = Q 0.45 / 1 / 2.5 / 6); the "EQ first" modes put the EQ in front of the saturation (EQ flip). Not included: the console's fixed 80 Hz / 12 kHz shelves, 75 Hz low-cut, noise and the parallel/serial channel blend. Code: `tools/fx/build_console.py`, tests in `tools/fx/test_fx.py`.
- **Filterbank effect** (FX type 18, after the Sherman Filterbank): two multimode filters (zero-delay-feedback state variable). **Response** sweeps continuously low-pass - band-pass - high-pass, **Anti-Mix** crossfades the response towards the notch, **F2 Offset** tunes filter 2 -24..+24 semitones away from filter 1 (harmonic sync; filter 2 is a little more resonant), **Drive** overdrives the input in front of the filters. Modes: Parallel (2 x 12 dB), Series (24 dB), Blend (50:50); the *Mirror* modes run filter 2 with the mirrored response (LP <-> HP). An envelope follower or LFO comes from the modulation matrix (all parameters are targets). Not included: the pitch follower and the switched-capacitor clock artefacts. Code: `tools/fx/build_fbank.py`, tests in `tools/fx/test_fx.py`.
- **Korg35 and Scream filters** (Filter effect modes 30-32, group *Korg / Scream*; the oscillator filter keeps its 30 types + Wavefilter): **Korg35 LP / HP** are 12 dB Sallen-Key filters in the manner of the MS-20 / Korg35: the resonance is positive feedback that saturates with the level, so it bites and screams when pushed and self-oscillates at the top of the Reso range. **Scream** follows Massive: a 24 dB low-pass with additional internal feedback. The Drive knob becomes the *Scream* amount, which feeds the saturated output back in front of the filter, giving the dirty, analog peak around the resonance (low values suit dirty basses). All three are zero-delay-feedback state variable filters whose damping grows with the band level (stable at every setting). Code: `tools/fx/build_korg.py`, `tools/fx/build_scream.py`, tests in `tools/fx/test_fx.py`.
- **Filter effect envelope** (replaces the earlier own ADSR): the Filter effect has an envelope on its cutoff: **Env Amt** (bipolar, centre = off, +-100% = +-7 octaves) and **Env Src** (ENV 1-10): the envelope takes its Attack, Decay, Sustain and Release from that **modulation envelope** and runs like it (linear attack, exponential decay / release), so one set of times drives the matrix and the filter. The gate is "any note held" (the rack is global); every new note retriggers from the current level, the release starts when the last note is let go. **Key Track** (P6) makes the cutoff follow the last played note (+-4 octaves over the key range at 100%), and a jump of the cutoff (automation, key track) is smoothed over about 5 ms. Works in all three racks. Presets made with the previous ADSR keep their Env Amt but P5 / P6 now mean Env Src / Key Track (the old Sustain / Release parameters 3000+ / 3030+ stay in the file, unused). Code: `tools/fx/build_fenv.py` + `tools/fx/build_fenv2.py`, tests in `tools/fx/test_fx.py`.

## Alpha Juno source

Source type 5, **Alpha Juno**, follows the structure of the [Roland Alpha Juno](https://en.wikipedia.org/wiki/Roland_Alpha_Juno) DCO: one oscillator per voice with a **pulse wave** and a **saw wave** that are summed, a **sub oscillator** and **noise**; pulse width modulation by the LFO or the envelope; vibrato from the same LFO; and the 16' / 8' / 4' range.

- **Wave selectors**: Saw 1-5, Pulse 1-3 and Sub 1-6, each with its own level. The documentation I could find only states the numbers of variants (three pulse, five saw, six sub waves on the Juno-1 / Juno-2), not their shapes, so the variants are my own approximations: Pulse 1 variable width, Pulse 2 = 25 %, Pulse 3 = 12.5 %; Saw 1 ramp (with **Curve**), Saw 2 PWM saw (the ramp runs over the pulse width, then drops), Saw 3 saw + octave-up saw, Saw 4 saw + third-harmonic saw, Saw 5 soft saw; Sub 1 square -1 oct, Sub 2 25 % pulse -1 oct, Sub 3 square -2 oct, Sub 4 25 % pulse -2 oct, Sub 5 squares at -1 and -2 oct, Sub 6 triangle -1 oct.
- **Width** is the pulse width (Pulse 1 and Saw 2); **PWM Depth** sweeps it, **PWM Source** is LFO (rate = **PWM Rate**, triangle), Env (the amp envelope) or Manual. Every Alpha Juno parameter is a mod matrix destination of its own.
- **Vibrato** applies the LFO to the pitch (up to +-50 cents); **Drift** adds slow random pitch wander (about 8 cents); **Noise** is slightly dark white noise.
- Edges are band-limited with PolyBLEP. The Alpha Juno chorus is not part of the source: use the Chorus effect.
- Parameters: `1700 + 32 * slot + 16..30` (second half of the Physical block). Generated by `tools/phys/build_juno.py` (after `build_phys.py`); `tools/phys/apply_juno_ui.py` and `apply_alphajuno_ui.py` were the one-time `patch/index.js` edits.

## Step sequencers (modulation sources Seq 1-10)

Ten 16-step sequencers are modulation sources 34-43 and can drive any destination in the matrix. Each has a SEQ tab in the bottom strip and on the modulation page: click or drag in the bar display to set steps (Shift snaps to 1/16, double-click resets a step), plus Length (1-16), Rate (Hz) or tempo Sync with Division, Glide, Direction (Forward / Backward / Ping-pong / Random), Retrig (Free = one global sequencer, Note = restarts per voice on note-on) and Unipolar / Bipolar. All steps and settings are normal automatable parameters (ids 3600 + 32 * n + k), so presets and host automation work. The DSP is generated by `tools/mod/build_seq.py` and checked by `tools/mod/test_seq.py`. The DSP reports the current step of every sequencer used in the matrix through the output event `seqPos` (sequencer * 16 + step) for all ten sequencers, whether or not they are routed (with Retrig the most recently started voice while it sounds), and sends every position again every 0.3 s; the editor shows it as a white frame around the step (`tools/mod/build_seqpos.py`, test `tools/mod/test_seqpos.py` with a host built with `-DSEQPOS_LOG`).

## Stepper features (like the Spire Stepper)

Each of the 10 sequencers has, besides the 16 step levels: a wave shape per step (flat, ramp down, ramp up, triangle, half sine, gate 50 %, gate 25 %, decay; click the symbol below a step, right click goes back), Hold (switches the shapes off), a Loop start step (plays the steps once, then repeats from the loop step to the length), Time x1-x4 (speed multiplier), and the Sync modes Free (Hz), Sync (tempo division) and Spos (the position follows the host: the step is locked to the song position, forward, backward or ping-pong over the loop). Parameters: Time / Loop / Hold = 3600 + 32 * n + 24 / 25 / 26, step shapes = 5000 + 16 * n + k. Generated by `tools/mod/build_seq2.py`, tested in `tools/mod/test_seq.py`.

## Arpeggiator and the SEQ / ARP page

The fourth page on the left rail, SEQ / ARP, holds the step sequencer editor (see above) and the arpeggiator. The arpeggiator sits in front of the voices: with Arp On, the held keys are played one after the other (Up, Down, Up / Down, Random, As played) over 1-4 octaves, at a tempo-synced Division or a free Rate (Hz), with Gate (note length) and Latch (keeps playing after the keys are released). The parameters are 3920-3927 (automatable, saved with presets). The DSP is generated by `tools/mod/build_arp.py` and checked by `tools/mod/test_arp.py`. The sequencers with Retrig restart on every arpeggiator note, so both can be combined. Keys pressed within the same moment form one chord; a note that arrives a few milliseconds late starts the pattern with the notes held so far.

### First start
The first time a plugin instance is loaded (the stored state has no `njo.defaults1` marker yet) all six oscillators get the **Basic Shapes** wavetable (`native_ui/NjoPluginEditor.h`, `Bridge::applyFirstRunDefaults`). It is stored with the plugin state like any loaded table, so it can be replaced or cleared; a slot that already has a table keeps it.

### 303 mode of the arpeggiator
`Arp Mode: 303` (SEQ / ARP page) plays a 16-step TB-303 pattern instead of the held keys: **Note** per step (-12..+24 semitones, click / drag, shift = octaves, double-click = root), **Gate** (off = rest), **Accent** (full velocity, otherwise 60 %) and **Slide** (the note is tied: the next note starts before it ends and the voice glides into it), **Length** 1-64 (the editor shows 16 steps per page, tabs 1-16 / 17-32 / 33-48 / 49-64). The root is the last key pressed; the voice plays mono and legato in this mode, a slide glides for at least 60 ms (the Glide knob if longer), steps without slide restart the oscillators. Rate / Sync / Division / Gate / Latch work as in the other arp modes. Route Velocity (accent) in the matrix to the cutoff or the filter envelope for the typical acid sound. Params 5200-5264 for steps 1-16 and 5500-5691 for steps 17-64 (not automatable; steps 17-64 default to a repeat of the 16 step pattern), DSP `tools/mod/build_arp303.py` + `tools/mod/build_arp64.py`, tests in `tools/mod/test_arp.py`.

### Key Start
* `Start: Free / Key` (param 3929, button next to the sequencer chips, default Key): the global sequencers only run while a note sounds and start at step 1 with the first note. `Free` lets them run all the time, as before. Sequencers in `Retrig: Note` mode always start per note.

### Host load (Seq Monitor)
* The sequencer steps, the step shapes and the matrix slots 21-256 are `automatable: false`: they stay in the saved state and in the UI, but the host's automation list only shows the other parameters.
* Parameters with `automatable: false` are not handed to the host at all (cmaj_JUCEPlugin.h, createParameterTree): they stay in the patch, the UI and the saved state, but the host sees about 1,100 parameters fewer. Thousands of host parameters made FL Studio hang when the plugin was closed.
* Only sequencers used in the matrix run, plus the one the editor shows. The editor tells the DSP which one through the hidden parameter 3928 `Seq Monitor` (0 = none); only that sequencer sends playhead events, so a closed editor costs no CPU and no events (and the 32-events-per-block limit cannot be hit).
* The Web UI (patch/index.js view) is only the fallback view of the patch; the sequencer editor exists in the native UI only.

## Checks

`python3 tools/check_params.py` compares every parameter declared in the DSP with the UI table (min, max, default). The host clamps values to the declared range, so a declaration that is too small silently cuts a UI value; run it after changing parameters.

## Mod matrix
- **256 slots** (the DSP and the host parameters have 256: `Slot n Source / Dest / Amount`, ids 307.. for 1-10, 472.. for 11-20 and `4000 + 3 * (n - 21)` for 21-256). Not literally unlimited: a plugin has a fixed parameter list, and 256 simultaneous routings is far beyond what a patch needs. The DSP only visits the slots up to the last one in use, so unused slots cost nothing.
- **Native editor**: the matrix on the modulation page is paged (20 slots per page, `<` / `>` below, the page count grows with the slots in use). Dropping a modulation handle on a knob uses the first free slot, on any page. The fallback web UI (`patch/index.js`) still lists only the first 20 slots; the other slots exist as parameters and work.
- **New destinations 258..443**: every Physical / Alpha Juno parameter of every oscillator (31 per slot, `OSC n ...` in the destination list, grouped per oscillator). A full-amount modulation moves a linear parameter by +-50 % of its range (selectors such as *Model* or *Range* step through their values); Noise Time, the two Decays and PWM Rate move by +-2 octaves. The same parameters show modulation rings on their knobs and accept dropped handles. These replace the old coupling of "Position / Harm", "Warp 1" and "Warp 2" to hit / material / noise / width / PWM / sub.
- Generated by `tools/mod/build_mod.py` (after `build_phys.py` and `build_juno.py`); tested by `tools/osc/test_osc.py` (new destination, slots 21 / 100 / 256, 30 slots summed, clearing a slot).

## Inspirator (generative sequencer)
- The SEQ / ARP page has a second tab, **INSPIRATOR**, a port of the stand-alone Inspirator MIDI generator (`tools/mod/inspirator_source.cmajor.txt`, built into the synth by `tools/mod/build_inspirator.py`). It writes whole parts for the synth's voices: **Chords** (progression by style / key / scale, Complexity picks triads, sevenths, ninths), **Lead**, **Bass**, **Arp** and **Drums** (12 lanes: kick, snare, clap, hats, rim, toms, ride, crash; notes per lane).
- The page follows the layout of the original: mode tabs, Song / Part seed boxes (drag or double-click to type), Chords Free / Locked (keeps the progression when the style changes), Variation, **GENERATE** (new Part seed), Style / Key / Scale / Bars / Chord Rate buttons, a song code (`C-maj-pop-4-1234`, Copy / Paste), the chord cards (click one to pick another degree, chord shape, borrowed chord or push), a piano roll of the generated pattern with the playhead (the DSP streams the pattern through the output events `insDump` / `insPos`, shown by `native_ui/pages/InspPanel.h`), the knob row and the MIDI In buttons. Drums shows the 12 lane columns (Density / Random / Note) instead of the chord cards.
- **Drag and drop into the DAW**: drag the **DRAG MIDI** handle (top right) or the piano roll itself onto a piano roll, a channel or the playlist of the host (FL Studio and others); the plugin writes the generated pattern as a standard MIDI file (96 ticks per quarter note, one loop long, drums on channel 10, `Njohrr` folder in the temp directory, named after mode and song code) and hands it over as an external file drag.
- Controls: On, Mode, Style (Pop, Rock, Hip-Hop, Trap, Lo-Fi, House, Techno, Jazz, Neo-Soul, Reggaeton, Drum & Bass, Afrobeats, Funk, Dub, Disco, Bossa Nova, Synthwave, Dubstep, Trance, Drill, UK Garage, Salsa, Metal, Country, Blues, Ambient, Ska, Amapiano, Breakbeat, Gospel, Hardstyle, Moombahton), Key, Scale, Song Seed (shared harmony), Part Seed (the part itself), Variation, Bars (1 / 2 / 4 / 8), Swing, Push (chords arrive an eighth early), Chord Rate, Fill Every, Timing Offset (ms), and per mode Complexity, Density, Humanize, Octave, Range, Gate, Velocity, Vel Random, Dur Random. Chords also has a progression override per bar (Chord 1-8 and Lock Chords), Drums has Density / Random / Note per lane. Same seeds always give the same pattern.
- It runs with the host transport (tempo, time signature and position events align the loop on the host's bars) or, while a key is held, free running at the host tempo. **MIDI In**: Transpose (the held key transposes the pattern, relative to Key), Hold (plays only while a key is held) or Off (the keys play the synth normally, the pattern runs with the transport only).
- **Extras** (EXTRAS button, parameters 7129-7140, `tools/mod/build_inspirator2.py` .. `build_inspirator5.py`): per-bar **locks** (click `lock bar n` above the roll: the bar keeps its notes while seeds / settings change), **voicing** for Chords (Inversion, Spread Close / Open / Wide, Strum, Figure Block / Up / Down / Up-Down / Alberti), **melody rules** for Lead (Chord Pull, Max Leap, Degree focus), **Ghost Notes** (Bass / Drums), **Mutate** (re-rolls a share of notes: scale-step shifts, octave jumps, drops, velocities) and the **Generator**: Classic (the original), **Euclid** (Bjorklund rhythm, chord tones), **Markov** (order-2 chain over scale-step deltas, trained on a built-in corpus: Pop / Minor / Jazz, or Custom = the imported MIDI file - the idea of YetAnotherMIDIGenerator reduced to a tiny model, no neural net), **Cellular** (rule 30 / 90 / 110 / 150 automaton for rhythm and steps), **L-System** (string rewriting), **Import**. Variant (0-15) selects rotation / corpus / rule / rule set. Generators apply to Lead, Bass, Arp and Drums.
- **More functions** (`build_inspirator9.py`, parameters 7141-7144): **Chord Bass** (Chords: root note two octaves below, optionally with its octave), **Drum Chance** (every drum note except the downbeats plays with this probability), **Ratchet** (hats split into 32nds / triplet-like bursts), **Poly** (Euclid drums: hat, open hat and percussion run in loops of 12:5:7, 10:7:9 or 14:5:11 steps against the bar) and the generators **Walk** (random walk with momentum) and **Permute** (a 4-note motif, bar by bar reversed / inverted).
- **Random chords**: the RANDOM CHORDS button (header, Chords / Lead / Bass / Arp) writes a new progression into the per-bar chord overrides (random degree and chord shape per bar, first bar mostly the tonic, now and then a borrowed chord; push flags stay); AUTO resets every bar to the automatic progression. The cards show overridden bars in orange and you can still edit each one.
- **Genre progressions** (`build_inspirator10.py`): every style 9-31 has its own 4 major and 4 minor progressions (the Song Seed picks one), e.g. Salsa ii-V-I-I / I-IV-V-IV, Gospel I-vi-ii-V / I-IV-ii-V, Blues I-IV-I-V / I-I-IV-V, Bossa Nova ii-V-I-vi, Reggaeton I-V-vi-IV / i-VII-VI-VII, Trance / Synthwave vi-IV-I-V / i-VI-III-VII. The progression table has up to 64 rows; the original styles 0-8 are unchanged.
- **Trance generator** (Generator = Trance, `build_inspirator11.py`; written from the public feature descriptions of FeelYourSound TranceEngine / SongEngine - no code or data of that product is used, and nothing was decompiled): Chords = rhythmic **plucks** (16 rhythms), Bass = **rolling / offbeat / gallop / psy** lines (Variant % 4) with octave figures (Variant / 4), Arp = **16 arpeggio patterns** over the chord tones, Lead = **call and response** / **focus note** / **micro phrases** / **acid line** (Variant / 4, cell = Variant % 4), Drums = the Trance kit. **RANDOM CHORDS** now opens a menu of six progression algorithms: Mixed, Circle of fifths, Tonic pedal, Trance loops, Stepwise, Colourful.
- **Genre generator** (Generator = Genre, `build_inspirator12.py`): the Trance engine for all 32 styles. Every style has its own tables: 4 pluck rhythms, 4 bass rhythms, 4 arpeggio patterns with step rate (8ths or 16ths), 4 lead kinds. Variant % 4 picks one of the four, Variant / 4 is the octave figure (bass) or phrase cell (lead). Drums use the style's own kit. The Trance generator stays as the trance-only version.
- **MIDI import**: drop a `.mid` file on the Inspirator panel (or IMPORT MIDI): notes are quantised to 1/64 at 96 ticks per quarter, up to 8 bars / 512 notes, sent to the DSP (`InsImportChunk`), stored with the project and played by Generator = Import; Mutate / Ghost / Voicing vary it, and it trains the Markov Custom corpus.
- **Styles** 9-19: Reggaeton, Drum & Bass, Afrobeats, Funk, Dub, Disco, Bossa Nova, Synthwave, Dubstep, Trance, Drill, UK Garage, Salsa, Metal, Country, Blues, Ambient, Ska, Amapiano, Breakbeat, Gospel, Hardstyle, Moombahton (32 styles in total, chosen from a dropdown grouped by family; `build_inspirator5.py` .. `build_inspirator8.py`).
- Parameters 7000 (On) and 7001-7128 (the original Inspirator parameters 1-128), all `automatable: false` (they stay in presets). The hand edits of the original (drum step masks 7020-7035 / 7090-7097, fill edits 7083-7085 / 7088) are parameters but have no editor yet, and Test: `tools/mod/test_inspirator.py`.

## Per-oscillator FX rack
- The FILTER, DIST and RESO tabs are merged into one **FX** tab (per oscillator, chips A-F). It works like the main FX section: a rack bar with the **4 slots** on top (click a tile to edit it, the arrow opens the effect type menu and Move left / right, the knob at the right is the slot's Mix); below it the page of the selected effect (filter with Wavefilter, distortion with Wavedistortion, resonator, or the knobs of the other types). The rack replaces the fixed order of the pre-matrix stages. Each slot has a **Type**, a **Mix** and three parameters P1..P3: `OSC n FX s <Type|Mix|P1|P2|P3>`, ids `6300 + 32 * n + 8 * s + k` (n = 0..5, s = 0..3, k = 0..7: type, mix, P1..P6).
- Types: Off, **Filter**, **Distortion**, **Resonator** (these three use the parameters of the OSC's FILTER / DIST / RESO pages, the slot only sets position and mix), **Bitcrush** (Bits, Rate), **Fold** (Drive, Bias, Stage 2, Shape sine > triangle, Asym, Attenuate), **Comb** (Time, Feedback, Damp, Polarity, Key Track, Mod = delay modulation; fractional delay up to 1024 samples), **Tilt** (Freq, Tilt). Any type can be used in any slot, also twice. Default: Filter > Dist > Reso > Off (the old behaviour).
- The effects run per voice (own state / delay lines for each of the 8 voices) before the RM / AM / FM matrices. The old `Pre-Matrix Order` parameter (id `1045 + 64 * n`) stays only for old presets: a value other than 0 sets the first three slot types.
- Not included: the FX-page effects (reverb, delay, granular ... they need big per-slot memory and can not run 8 voices x 6 oscillators).

## Per-oscillator Resonator and pre-matrix order
- Every oscillator slot has three stages between its source and the FM / PM / PD matrix: **Filter**, **Distortion** and the new **Resonator**. The **Order** list (parameter `OSC n Pre-Matrix Order`, id `1045 + 64 * n`, shown on the DIST and the new RESO page) picks the sequence: Filter > Dist > Reso (default, the old behaviour), Dist > Filter > Reso (the old "Pre" setting), Filter > Reso > Dist, Reso > Filter > Dist, Dist > Reso > Filter, Reso > Dist > Filter.
- The **Resonator** is the 16-mode modal bank of the Physical source used as an effect on the slot signal (ids `1056..1063 + 64 * n`): On, Model (the same 9 models), Decay, Material, Position, Inharm, Tune (+-24 st relative to the played key) and Mix. Each mode has peak gain 1, so only what the input contains at the mode frequencies rings up; the wet signal is soft-limited. Works on any source type, stereo, per voice.
- Generated by `tools/phys/build_reso.py` (after `build_phys.py`); tests in `tools/osc/test_osc.py` (tuning, mix 0, all models, order, all six orders bounded).

## Convolution reverb and extended effects
**Convolution** (FX type 12) is a partitioned-FFT convolution reverb (1024-sample blocks, up to 1.5 s of impulse response). Modes: Room, Hall, Plate, Cathedral, Chamber, Reverse, Gated, Ambience (impulse responses generated on the fly from Size / Decay / Damp) and **User IR**: *LOAD IR* on the effect page takes any audio file (up to 2 s, mono-summed, converted to 48 kHz and normalised); it is kept in the plugin state and re-sent after the window is reopened. Parameters: Size, Decay, Damp, PreDly (0-200 ms), Width, Tone (low-pass below the centre, high-pass above). Limits: **one convolution engine per rack** (the lowest convolution slot of a rack owns it, further ones pass the signal through), 1024 samples (about 21 ms) latency, and the IR is rebuilt in the background 0.15 s after Size / Decay / Damp / mode change (the old one keeps playing meanwhile). The convolution is the most CPU-hungry effect in the rack. Engine: `tools/fx/conv_dsp.cmajor.part`, inserted by `tools/fx/build_fx.py`.

More algorithms and parameters (`tools/fx/build_fx2.py`; all effects keep their old ids and defaults of existing slots, the new parameters start at 0.5 in presets saved before):
* Distortion: modes Rectify, Fuzz, Tanh; Bias, Low Cut (pre-shaper high-pass), Presence; DC blocker after the shaper.
* Bit Crush: modes Round, Mu-law, Floor; Dither (TPDF) and Jitter (random hold length).
* Delay: mode Ducking (echoes drop while the input plays); Mod (slow time modulation), Low Cut in the feedback path.
* Chorus / Flanger / Phaser: Width of the wet signal; Flanger modes Positive / Negative feedback.
* Reverb: wet Low Cut and High Cut. EQ: High Freq (4-16 kHz). Compressor: soft Knee (0-12 dB).

Tests: `python3 tools/fx/test_fx.py --host <dsp_host built from cmaj generate --target=cpp>` (the host got an `ir` command).

## Njohrr FX (effects-only plugin)
A second VST3, **Njohrr FX**, with only the effects section: an audio input, the Main FX rack (all 27 effect types), the Output card (Drive, algorithm, width, tone, DC block, output gain) and the preset bar. No oscillators, no modulation page, no MIDI.
* Same DSP source and the same parameter ids as the synth (generated, `tools/fx/build_fxplugin.py` -> `patch_fx/`), so FX settings are compatible. Differences: the input feeds the Main rack at unity gain (the synth Master level is not applied), **Drive** blends the shaped input in (default 0 = clean), **Bus 1 / Bus 2 return levels default to 0** (the buses are parallel racks: raise the return to hear them), and the output limit is +-8 instead of +-1.
* The editor is the same native UI built with `NJOHRR_FX_ONLY=1` (no page rail, no modulation strip, window 1180 x 564). Mod-matrix sources that need notes (envelopes, key, velocity) have no signal here; free-running LFOs still work.
* Build: CMake target `NjohrrFX` (option `NJOHRR_BUILD_FX`, default ON), output `build/NjohrrFX_artefacts/Release/VST3/`; the CI workflow uploads it as `NjohrrFX-VST3-<OS>`. Its plugin source is `cmajor_plugin_fx.cpp`, generated by `tools/regen_plugin.sh` (which also regenerates `patch_fx/`).
* Tests: `tools/fx/test_fxplugin.py --host <dsp_host built with -DDSP_FX from the patch_fx class>` (unity pass-through, silence, no synth on MIDI, and racks).

## Through-zero FM matrix (TZFM)
A fourth modulation matrix next to FM, PM, PD, RM and AM: on the RM / AM page, third panel (parameter ids 2900 + 6 * modulator + carrier, 0-100 %, `tools/osc/build_tzfm.py`). It is linear FM with a signed frequency: the modulator is integrated into a phase offset, so the carrier's frequency is f * (1 + 4 * amount * modulator) and runs backwards through zero when that factor is negative (the exponential FM matrix cannot do that). Because the modulator is integrated, a DC offset detunes the carrier. Like PM and PD it only reaches sources with a phase input (Wavetable, Sampler, Wave Terrain, Alpha Juno, Kick, JP-8080); the cells are not modulation matrix destinations.

## Legato switch
Global page, Voice card: **Legato** (On by default, parameter id 4). In Mono mode with Legato on, a note played over a held one only changes the pitch (with Glide) and does not restart the oscillators; with Legato off every note restarts them (the pitch still glides). It has no effect in Poly mode.

## Unison on every source
Every oscillator source has the **Unison** section (Voices 1-16, Detune, Blend, Width, Detune Curve, Drift). Wavetable and Alpha Juno run several voices of the oscillator itself. All other sources (Sampler, Wave Terrain, Physical, Kick, Waveguide, JP-8080, Granular, Additive, Modal Drum, Spectral, SoundFont) play once per note and then go through a detuned-copy stage (`tools/osc/build_unigen.py`, marker UNI-ALL): every copy is a two-tap crossfading delay-line pitch shifter (window about 35 ms) of the source's mono sum, with the slot's detune curve, blend, width and drift; the side signal (L - R) of a stereo source is kept. Phase Spread has no effect there, and a pitch shifter adds a little graininess compared with real oscillator voices (most audible on very low notes).

## 16 effects per rack
The Main FX rack holds **16 effects** instead of 10. The ids of slots 1-10 are unchanged (presets keep loading); slots 11-16 are new global slots 30..47 with their own parameters: slot parameters `3200 + (rack * 6 + j) * 10` (Type, On, Mix, Mode, P1-P6), tempo sync `3400 + rack * 6 + j`, processing order `3380 + rack * 6 + j`. The **FX Order** parameters (`641..`, `751..`, `861..`) now run 0-15 and hold rack-local slot numbers; a stored order of 10 entries stays valid (the new slots follow in their natural order). The DSP arrays grew to 48 slots (effect memory 48 x 196608 floats, about 38 MB). In the native editor the effect list is a scrollable list. The web fallback UI (`patch/index.js` view) still shows slots 1-10 only. Code: `tools/fx/build_fxslots.py`; tests in `tools/fx/test_fx.py` (slots 11 and 16 behave like slot 1, order across old and new slots, sync).

## Airwindows effects
Nine effects are ports of **Airwindows** plugins by Chris Johnson (MIT licence, <https://github.com/airwindows/airwindows>; licence text in `licenses/Airwindows-MIT.txt`).
They are FX types 19-27 in every slot of the rack (names start with *AW*):

| Type | Original | Parameters |
|---|---|---|
| AW PurestDrive | PurestDrive | Drive |
| AW Spiral | Spiral2 | Input, Highpass, Presence, Output |
| AW Drive | Drive | Drive, Highpass, Output |
| AW Tube | Tube2 | Input, Tube |
| AW Density | Density2 | Density, Highpass, Output |
| AW Console 7 | Console7Channel | Fader |
| AW Channel | Channel9 | Drive, Output; the mode list is the console type (Neve, API, SSL, Teac, Mackie) |
| AW ToTape | ToTape6 | Input, Soften, Head Bump, Flutter, Output |
| AW MackEQ | MackEQ | Trim, Hi, Lo, Gain |

The slot **Mix** replaces the originals' Dry/Wet knob. The processing is computed in 64-bit float (`awS` state, `awD` derived values; flutter delay lines of ToTape in the slot arena);
the sample-rate scaling of the originals is kept. Differences to the originals: the denormal noise injection is a tiny alternating offset, Console 7 smooths the fader with the
fixed 64-sample speed, ToTape's flutter uses its own random generator. Code: `tools/fx/build_aw.py`. Tests: `tools/fx/test_fx.py` (every type finite, bounded, audible, with default / maximum / minimum
values) and `tools/fx/awref/compare.py`, which compiles the original Airwindows C++ with a small stub of the VST SDK and compares the output (relative RMS error below 1e-2; see the notes in the script).

## Plasma effect (FX type 28)
An asymmetric distortion in the style of Dimethoxy's free "Plasma" plugin (https://github.com/Dimethoxy/Plasma). Own implementation from the public feature description, no code of the original.
* **Mode** = style: Soft, Hard, Fold, Half, Fuzz, Diode, Arctan, Rational, Soft Exp, Ripple, Tri Fold, Cubic. The shapers use first-order antiderivative anti-aliasing (ADAA), the level is compensated.
* **Drive** 0-40 dB, **Asym** (bias in front of the shaper, makes even harmonics; its DC is removed), **Girth** (high-passed noise that follows the signal level erodes the sound; silence stays silent).
* **Filter** HP / LP / Dual / Peak (four steps), **Freq** 20 Hz-20 kHz, **Reso** (Q up to 20 for HP / LP / Dual, boost for Peak) behind the shaper (TPT state variable filter).
Code `tools/fx/build_plasma.py`, tests in `tools/fx/test_fx.py`.

## Tools
* `tools/regen_plugin.sh` regenerates `cmajor_plugin.cpp`, `patch_fx/` and `cmajor_plugin_fx.cpp` (Cmajor target **juce**, never `cpp`: that one lacks `createPluginFilter()` and the plugin would not link) and the native UI tables; `--check` only reports whether both are up to date.
* `tools/fx/test_fx.py` also checks that every effect type is wired everywhere (DSP parameter range and dispatch, generated UI tables, colours) and that no type is clamped to another.

## Unison on the Alpha Juno source, Unison Drift and Phase Spread
The Alpha Juno source now has the same **unison** as the wavetable source (Voices 1-7, Detune, Blend, Width, Detune Curve; shared parameters, so presets and modulation work the same way). Every unison voice is a complete DCO (saw + pulse + sub, band-limited); the LFO, pulse width and noise are shared. Level is kept equal to a single voice. Two new unison parameters on both sources (OSC page, Tune card):
* **Drift**: slow random pitch wander per unison voice (a new target every 2048 samples, up to about 12 cents). On the Juno source it adds to the DCO's own analog Drift, which is now independent per voice.
* **Phase Spread**: random start phase per unison voice (voice 1 keeps the Start Phase), so stacked voices do not all start in phase and cancel / add as one.
**Super Saw and Hyper Saw (Unison Style 4 / 5)**: unison now has up to **16 voices**. *Super* uses the JP-8000 detune curve (Szabo measurement: 7 asymmetric offsets, interpolated for other voice counts) with the JP-8000 Mix curves, where **Blend** sets the centre / side balance and the centre voice stays at the note pitch. *Hyper* is a wider, stronger-than-linear curve (reaches about +-3 semitones at full Detune) for stacks of 12-16 voices. Styles 0-3 are unchanged; level stays equal to one voice. Code: `tools/osc/apply_super.py`.
CPU: the Juno source costs about as much per voice as a wavetable voice; 7 unison voices on all six slots with a chord is the worst case (about 2x the time of single voices in the offline host). Code: `tools/osc/build_uni.py`, `tools/phys/build_juno.py`.

## Table and resonator editors

Three graphical editors open over the OSC pages (native editor only; the JS fallback UI has none):

- **Wavefilter** and **Wavedistortion** (FILTER / DIST page, EDIT button on the table card): draw the frame with the mouse (freehand, linearly interpolated), previous/next frames are shown faint, mouse wheel changes frame. Tools: add (duplicate), delete, morph first to last, smooth, invert, flip, normalize, random and presets (low/high/band pass, notch, comb, formant; linear, soft, hard, fold, asym, stairs). Without a loaded table the 16 built-in frames are copied so you can edit them. Edits go through the sound memory (`tblLoad`), so they persist in the plugin state like a loaded table.
- **Resonator editor** (Physical source: EDIT on the source card, tabs Physical A / B; RESO page: EDIT for the resonator stage): frequency (x0.5..x2), gain (0..2) and decay (x0.1..x10) multipliers of each of the 16 modes, with a spectrum view and Hz labels. Presets: odd / even modes, stretch, squeeze, decay tilt, randomise, reset. Edits are sent through `modLoad` (`ModeEdit` sound-memory kind, 48 multipliers per slot and set) and persist; a fully neutral edit clears the slot.

## FX tempo sync, trance gate and more effect modes

- **Sync** (ids 940..969, one per slot, shown next to the mode list for Delay, Chorus, Flanger, Phaser and Tremolo): Off or one of the 18 divisions of the LFO sync list. With a division set, the Delay time becomes that note length at the host tempo (or the *Sync BPM Override*), and the modulation of the Chorus / Flanger / Phaser / Tremolo is locked to a beat clock that follows the host position (`positionIn`), so the effects stay in phase with the song. The Rate / Time knob is dimmed while sync is on. The beat clock free-runs at the tempo when the host sends no position.
- **Tremolo** gained *Trance Gate* (16-step pattern per cycle, 24 patterns, Smooth edges, Swing, Stereo shifts the right channel by up to half a pattern; with sync one cycle = the chosen division, e.g. 1/1 = one bar), *Auto-Pan*, *Random S&H* and *Smooth Random*. The step patterns live in `FX_GATE_PATTERNS` (patch/index.js) and `tools/fx/build_fx3.py`; keep both in step.
- New modes: Distortion (Diode, Chebyshev, Tape, Gated), Bit Crush (Bits Only, Rate Only, Noise Shaped), Delay (Reverse, Multi-tap), Chorus (Ensemble, Wide), Flanger (Through-Zero, Stereo), Phaser (10 / 12 stages, Inverted 4 / 8), Reverb (Chamber, Ambience, Dark, Bright, Infinite), EQ (Tilt, Loudness, Presence), Compressor (Limiter, Expander, Gate).
- The effect Type parameters now range 0..12 (Convolution was clamped to Compressor by the host before).
- Generator: `tools/fx/build_fx3.py` (marker `// FX-SYNC`, run after `build_fx2.py`); tests in `tools/fx/test_fx.py`.

## Parametric EQ (FX type 13)

A new effect type "Parametric EQ" next to the old 3-band EQ (which is unchanged). Up to **24 bands** per slot, each with its own type:
Bell, Low/High Shelf, Low Cut 12/24/48, High Cut 12/24/48, Band Pass, Notch, Tilt, All-Pass, **Comb Feed-forward** and **Comb Feedback**.
Bell, Band Pass and Notch bands can add **harmonics** (1-16 extra bands at 2f, 3f ... with a falloff per step; all, odd or even harmonics), like the harmonic bands of MEqualizer.
Each band can work on Stereo, Left, Right, Mid or Side. Up to 64 biquad sections run per slot; combs use a per-band delay line.

Slot controls: Output (+-18 dB), Gain Scale (0-200 % of all band gains), Freq Shift (+-1 octave), Q Scale (x0.25-x4), Mix.

Editor (native UI only): curve display with draggable nodes (frequency / gain, vertical drag sets Q for cut filters), wheel = Q, shift+wheel = harmonics, double-click adds / deletes, right-click menus, band chips, presets.
The bands are stored in the sound memory (kind EqBands) and streamed to the DSP with the `eqLoad` event, so they persist with the plugin state like samples do.
Limitations: the bands are not automatable and are not mod destinations (only the slot controls are); the JS fallback UI has no band editor.
Generator: `tools/fx/build_eq.py`; tests: `tools/fx/test_fx.py` (PEQ section).

## Wave Terrain source

Source type 2, **Wave Terrain**, reads a two dimensional terrain z = T(x, y) along a closed **orbit**; the orbit is traversed once per cycle at the note frequency, so the pitch follows the keyboard. The display shows one cycle of the output.

- **Terrain A / B** (12 terrains: Sine Product, Ripples, Saddle, Chebyshev, Checker, Spiral, Diamond, Interference, Lattice, Bumps, Fractal, Twist) and **Morph** between them; **Scale** (0.25..4 times the features), **Warp** (bends the plane before the lookup) and **Fold** (wavefolds the result).
- **Orbit**: Center X / Y, Radius X / Y, Rotation, **Y : X** (the frequency ratio of the two axes: whole numbers give a periodic sound, other values drift and beat), Phase between the axes (0 = circle, 0.25 = a line when the ratio is 1) and Shape (circle to squircle). **Move Rate / Depth** let the center wander slowly, **Vel > Radius** scales the radius with the velocity.
- **Smooth** (a low-pass that follows the note), **Drive** and **Bits** after the lookup; a DC blocker follows.
- Parameters: slot parameters 24..27 (ids 1024 + 64 x osc: Terrain A, Scale, Warp, Fold) and 16 more with the ids 2100 + 16 x osc + j; every continuous knob is a modulation destination (`OSC n Terrain ...`, dest 540..635; the destinations `Position / Warp 1 / Warp 2` of the slot are Scale / Warp / Fold here).
- Limits: the terrain is evaluated once per sample and is not band-limited (high notes with a large radius alias, like a wavetable with the Aliasing switch on); Smooth reduces that.

The Plaits source (24 engines with extras) that existed in earlier versions on this branch was removed; presets that used it come back as Wave Terrain.

## Wavetable aliasing switch

Each oscillator has an **Aliasing** switch on the Wavetable source page (parameter ids 2000 + oscillator). Off (default) reads band-limited mip levels, so notes stay clean up to the top of the keyboard. On reads the full 2048-sample level for every note, so the harmonics above Nyquist fold back: the gritty, digital sound of simple wavetable synths. It applies to the whole slot including unison voices; it is not a modulation target.

## Saturator and Waveshaper (FX types 14, 15)

**Saturator** has 12 models (Tube, Tape, Transformer, Diode, Fuzz, Soft Clip, Hard Clip, Rectifier, Sine Fold, Rational, Exciter, Arctan) and the controls Drive (0..36 dB), Tone (tilt), Bias, Output, Low Cut and Sag. The output level is compensated automatically, so Drive changes the character rather than the loudness, and a DC blocker follows the non-linearity.

**Waveshaper** applies a transfer curve you draw: up to 16 nodes with a curvature per segment (double-click adds / removes a node, drag the diamonds for the curvature, right-click for presets). Modes: Curve (full -1..1 range), Mirror (the right half is mirrored, odd symmetry) and Rectified (input folded to its absolute value, which doubles the frequency). Fewer than two nodes is a straight line. The nodes are stored in the sound memory like the EQ bands (so they are saved with the preset), are not automatable and not modulation targets.

Both use first-order antiderivative anti-aliasing (ADAA) instead of oversampling, which removes most of the aliasing at low CPU cost; very high drive on hard edges can still alias a little. There is no multiband mode. The JS fallback UI has the knobs but no node editor.

## Reverb engines (FX type 8)

The Schroeder comb reverb was replaced by two engines from the open literature (tools/fx/build_reverb.py). The slot parameters and ids are unchanged (Size, Damp, PreDly, Width, Low Cut, High Cut).

- **Zita-rev1** (Fons Adriaensen, GPL; ported from the GPLv3 Cmajor ZitaReverb example): 8x8 feedback delay network with allpass feedback, Hadamard mixing, a low / mid RT60 split (200 Hz crossover) and high-frequency damping. Modes Hall, Room, Cathedral, Chamber, Dark, Bright and Infinite. Size sets the RT60 (e.g. Hall 0.6-8 s, Cathedral 2-16 s), Damp the high-frequency damping, each mode its own delay scale.
- **Dattorro plate** (J. Dattorro, "Effect Design Part 1", JAES 1997): input diffusion and a figure-eight tank with modulated allpasses. Modes Plate and Ambience.
- Size / Damp / pre-delay / width and the wet low / high cut work in every mode. Changing the mode keeps the slot's memory (the old tail of the other engine fades out as noise).
- Tests: `tools/fx/test_fx.py` (FX-REV section).

## Kick source and the Source dropdown

Source type 5, **Kick**, is a kick drum voice in the spirit of the open-source kick synths Geonkick (GPL-3), Kickmess / LMMS Kicker and ChowKick: sine body with a pitch sweep, click, noise tail, sub oscillator and a drive stage. The algorithms are written from scratch for this synth (no code copied); the designs are the references. The Source selector of every oscillator is now a dropdown (Wavetable, Sampler, Plaits, Physical, Alpha Juno, Kick).

- **Pitch** falls from the played note times 2^Sweep (0-6 octaves) down to the played note, so the kick is tuned by the key. Sweep Time / Curve shape the fall, Tune adds +-24 semitones.
- **Modes:** Classic (sine with feedback tone), 808 (the pitch follows the decaying body like a resonant circuit, saturated, pulse excited), Punch (two stage pitch fall, second harmonic), Hardstyle (long fall, hard clipped).
- **Body:** Decay (20 ms - 3 s), Tone, Character (mode specific), Punch (transient boost), Sub (octave below).
- **Click:** Click level, Click Tone and Click Decay; **Noise** tail; **Drive** with 6 curves (Hard Clip, Tanh, Atan, Log, Exp, Poly).
- Ids: `KICK_BASE` 1900 + 16 * slot + j; every parameter is a mod destination (444..539). Generator `tools/kick/build_kick.py` (DSP) and `tools/kick/apply_kick_ui.py` (JS UI); tests in `tools/osc/test_osc.py`.

## Mutable-style effects (Granular, Warp)

Two FX types (29, 30) inspired by Mutable Instruments Clouds and Warps. These are our own implementations written after the public manuals, not code ports.

- **Granular** (29): modes Granular, Freeze, Pitch Shifter, Looping Delay. Params: Position, Size, Pitch, Density, Texture, Feedback.
- **Warp** (30): modes Analog RM, Digital RM, Vocoder, Freq Shift. Params: Amount, Level, Pitch, Shape, Drive, Release. (Crossfade, Fold, XOR and Comparator moved to the oscillator matrices below.)

Generated by `tools/fx/build_mutable.py` (idempotent, marker `FX-MUTABLE`); tests in `tools/fx/test_fx.py`.

## Crossfade / Fold / XOR / Comparator matrices
Four more 6 x 6 oscillator matrices next to FM, PM, PD, RM, AM and TZFM (ids 5300 + 36 * kind + 6 * source + target, 0-100 %; `tools/osc/build_mxmat.py`, tests in `tools/osc/test_osc.py`): **XF** crossfade (equal power, 100 % = only the source), **FD** wave fold (sum of both folded harder with the amount), **XR** xor of the 16 bit values, **CP** comparator (dry > maximum > gate of source vs. target). Like RM / AM the source is the previous output sample of the source slot and the carrier is the target slot's signal after filter and distortion. All of them (and TZFM) are mod matrix destinations like FM / RM: groups "TZFM / XF / FD / XR / CP matrix (amount)", destinations 1308 + 36 * m + 6 * source + target (m = 0 TZFM, 1 XF, 2 FD, 3 XR, 4 CP), +-50 % of the range at full amount (`tools/osc/build_mxdst.py`); drop a modulation source on a matrix cell as usual.
In the native UI the title of every panel on the FM / PM / PD and RM / AM pages is a dropdown: any of the 10 matrices can be shown in any panel (the choice is not saved with the preset).

## 303 pattern bank
The 303 pattern editor has a bar with a pattern dropdown, previous / next, **SAVE**, **SAVE AS** and **DEL**. A pattern (length plus note / accent / slide / gate of all 64 steps) is a small text file `<Documents>/Njohrr/303 Patterns/<name>.n303` (`native_ui/NjoA3Bank.h`, test `native_ui/test/a3bank_test.cpp`); the first time three patterns are written (Acid Classic, Octave Bounce, Slide Line 32), files the user deletes stay deleted. The pattern in use is part of the plugin state like any parameter; the name shown in the bar is remembered with the project.

## More modulation strength
* The FM, PM and TZFM matrix cells go to **400 %** (PD, RM, AM and the XF / FD / XR / CP matrices stay at 100 %, they saturate there). Exponential FM and TZFM accept up to eight times the full-scale modulator before they clamp.
* The amount of every **mod matrix slot** goes to **+-400 %** (was +-100 %). The destinations scale with it as before, so presets made earlier sounds the same; the slider has a square taper (100 % at a quarter of the half track) so steps near zero stay fine. DSP: `tools/osc/build_mxrange.py`, tests in `tools/osc/test_osc.py`.

## More sequencer types (arpeggiator modes 6-8)
`Arp Mode` has three more entries; all of them play scheduled, polyphonic notes (chords, ratchets and ties work) from the arp clock (Rate / Sync / Division, Gate = default note length). The root is the last key pressed. DSP `tools/mod/build_seqmodes.py`, tests in `tools/mod/test_arp.py`, editors on the SEQ / ARP page (`native_ui/pages/ModEditors.cpp`). All parameters are not automatable.
* **Euclid / Poly** (ids 5710 + 8 * lane + k): four lanes, each with On, Steps (1-64), Pulses, Rotation, Offset (semitones from the root), Probability and Ratchet (1-4). Step i of a lane hits when `((i + rotation) % steps * pulses) % steps < pulses`; the lanes run on the same clock with their own lengths, so different lengths give polyrhythms. The first step of a lane is accented.
* **Melodic** (length 5800, rows 5810 + 64 * row + step): up to 64 steps, per step Note (-24..24), Velocity, Length (10-400 % of a step, over 100 % ties into the next), Chord (none, octave, fifth, major, minor, sus4, maj7, min7, dim), Probability, Ratchet and Gate. The editor shows one lane at a time (chips on top), 16 steps per page.
* **Generative** (ids 5750-5759): **Turing Machine** (shift register of Loop bits, Mutation % flips the bit that wraps: 0 % = fixed loop) or **Random Walk** (Max Step in scale degrees, Bias up / down), mapped to one of 12 scales over Range semitones above the root (+ Shift), Rest % and Ratchet.

## MSEG modulation envelopes
Each of the 10 modulation envelopes (sources ENV 1-10) can run as an MSEG. In the ENV / LFO page the envelope display has a button **> MSEG** (ADSR mode, the default, so old presets sound as before); it converts the current A/D/S/R into 3 nodes. **ADSR** switches back.

- Up to **8 nodes**; each has *time* (ms to reach it from the previous node, 0-10 s), *level* (0-1) and the *curve* of the segment before it (-1..1, shape `x^exp(curve*2.5)`).
- Drag a node to change time and level, drag the diamond on a segment for the curve, click empty space to add a node, double click a node to delete it (double click a diamond = straight).
- **Sustain node** (green): while the key is held the envelope stops there. **Loop** (LOOP button or right click > Loop starts / ends here): while held the envelope repeats the nodes of the loop region.
- On note off the envelope continues with the nodes after the sustain node. Without further nodes (or without a sustain node) the level falls to 0 with the ADSR Release knob.
- Parameters 7200 + 30 * env (non-automatable, stored in presets): mode, nodes, sustain, loop on / start / end, then 3 values per node. The filter-effect envelope keeps the ADSR behaviour.
- Tests: `python3 tools/mod/test_mseg.py --host <dsp_host>`; script `tools/mod/build_mseg.py` (marker MSEG-DSP).
