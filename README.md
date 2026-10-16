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
