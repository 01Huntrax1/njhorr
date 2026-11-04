#!/bin/bash
# Regenerates cmajor_plugin.cpp (the JUCE plugin source) from patch/ with the Cmajor tool, and the native UI tables from patch/index.js.
#   tools/regen_plugin.sh            regenerate NjoData.gen.cpp and cmajor_plugin.cpp
#   tools/regen_plugin.sh --check    only check that both are up to date (exit 1 if not), changes nothing
# Needs the cmaj command line tool: CMAJ=/path/to/cmaj (default: ~/cmajor-lang/cmajor/build/tools/command/cmaj, then cmaj on the PATH), CMAJ_INCLUDE for its include folder.
# NOTE: the target must be "juce". "--target=cpp" gives only the DSP class, without createPluginFilter() and the embedded patch files,
# and the plugin then fails to link (LNK2001 createPluginFilter).
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
if [ -z "$CMAJ" ]; then
    for c in "$HOME/cmajor-lang/cmajor/build/tools/command/cmaj" /home/claude/cmajor-lang/cmajor/build/tools/command/cmaj "$(command -v cmaj)"; do
        [ -x "$c" ] && { CMAJ=$c; break; }
    done
fi
CMAJ_INCLUDE=${CMAJ_INCLUDE:-$(dirname "$(dirname "$(dirname "$(dirname "$(dirname "$CMAJ")")")")")/include}
CHECK=0; [ "$1" = "--check" ] && CHECK=1
[ -x "$CMAJ" ] || { echo "cmaj not found: set CMAJ=/path/to/cmaj"; exit 2; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fail=0

# 1. native UI tables from index.js
cp "$ROOT/native_ui/NjoData.gen.cpp" "$TMP/NjoData.old"
node "$ROOT/tools/nativeui/gen_data.js" >/dev/null
if ! cmp -s "$TMP/NjoData.old" "$ROOT/native_ui/NjoData.gen.cpp"; then
    if [ $CHECK = 1 ]; then echo "native_ui/NjoData.gen.cpp is out of date (run tools/regen_plugin.sh)"; cp "$TMP/NjoData.old" "$ROOT/native_ui/NjoData.gen.cpp"; fail=1
    else echo "updated native_ui/NjoData.gen.cpp"; fi
fi

# 2. the JUCE plugin source
"$CMAJ" generate --target=juce --output="$TMP/juce" --cmajorIncludePath="$CMAJ_INCLUDE" "$ROOT/patch/Eisenpuls_Synth.cmajorpatch" >/dev/null
NEW="$TMP/juce/cmajor_plugin.cpp"
[ -f "$NEW" ] || { echo "the juce target produced no cmajor_plugin.cpp"; exit 2; }
grep -q "JUCE_CALLTYPE createPluginFilter" "$NEW" || { echo "generated file has no createPluginFilter()"; exit 2; }
grep -q "GeneratedPlugin<::Eisenpuls_Synth>" "$NEW" || { echo "generated file does not name the plugin class"; exit 2; }
if cmp -s "$NEW" "$ROOT/cmajor_plugin.cpp"; then
    echo "cmajor_plugin.cpp is up to date"
elif [ $CHECK = 1 ]; then
    echo "cmajor_plugin.cpp is out of date (run tools/regen_plugin.sh)"; fail=1
else
    cp "$NEW" "$ROOT/cmajor_plugin.cpp"; echo "updated cmajor_plugin.cpp"
fi
exit $fail
