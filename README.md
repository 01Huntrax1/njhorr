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
Edit patch/Eisenpuls_Synth.cmajor or patch/index.js, then regenerate with the Cmajor tools:
    cmaj generate --target=juce --output=<folder> --cmajorIncludePath=<cmajor>/include patch/Eisenpuls_Synth.cmajorpatch

## Presets and library (inside the plugin window)
- PRESET bar under the title: previous / next, SAVE, PRESETS (save as new, overwrite, rename, delete, export, import).
- LIBRARY: samples and wavetables you load into any oscillator are added automatically; import more files, rename, delete, and load them into Sampler 1/2 or Wavetable 1-3. A preset remembers which library file each oscillator used.
- Everything is stored in the plugin's built-in browser storage on this computer (per DAW program). Use PRESETS > EXPORT / IMPORT to move presets between programs or computers.
