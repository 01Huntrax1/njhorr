#!/bin/bash
# Fast incremental build of the screenshot harness without CMake / without recompiling JUCE.
#   native_ui/test/fastbuild.sh <outdir> [make args]      ->  <outdir>/njo_shot
# JUCE's own object files are taken from /tmp/njo_juce_objs (built once from native_ui/test/CMakeLists.txt, see README_UI.md).
# NJO_SRC (default: the repo's native_ui folder) can point to a private copy of the sources.
set -e
OUT=${1:?outdir}; shift || true
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=${NJO_SRC:-$(cd "$HERE/.." && pwd)}
JOBJ=${NJO_JUCE_OBJS:-/tmp/njo_juce_objs}
JUCE=${JUCE_PATH:-/home/claude/JUCE}
mkdir -p "$OUT"
cat > "$OUT/Makefile" <<MK
SRC := $SRC
OUT := $OUT
CXXFLAGS := -O1 -g0 -std=c++17 -DJUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1 -DJUCE_MODAL_LOOPS_PERMITTED=1 -DJUCE_MODULE_AVAILABLE_juce_audio_basics=1 -DJUCE_MODULE_AVAILABLE_juce_audio_formats=1 -DJUCE_MODULE_AVAILABLE_juce_core=1 -DJUCE_MODULE_AVAILABLE_juce_data_structures=1 -DJUCE_MODULE_AVAILABLE_juce_events=1 -DJUCE_MODULE_AVAILABLE_juce_graphics=1 -DJUCE_MODULE_AVAILABLE_juce_gui_basics=1 -DJUCE_OPENGL_ES=0 -DJUCE_STANDALONE_APPLICATION=1 -DJUCE_USE_CURL=0 -DJUCE_USE_FLAC=1 -DJUCE_USE_OGGVORBIS=1 -DJUCE_WEB_BROWSER=0 -DLINUX=1 -DNDEBUG=1 -D_NDEBUG=1 -I$JOBJ/JuceLibraryCode -I$JUCE/modules -I/usr/include/freetype2 -I/usr/include/libpng16 -Wno-psabi
SRCS := \$(wildcard \$(SRC)/*.cpp) \$(wildcard \$(SRC)/pages/*.cpp) \$(SRC)/test/shot.cpp
OBJS := \$(patsubst \$(SRC)/%.cpp,\$(OUT)/obj/%.o,\$(SRCS))
JOBJS := \$(shell find $JOBJ -name '*.o')
\$(OUT)/njo_shot: \$(OBJS)
	g++ -o \$@ \$(OBJS) \$(JOBJS) -lfontconfig -lfreetype -lrt -ldl -lpthread
\$(OUT)/obj/%.o: \$(SRC)/%.cpp
	@mkdir -p \$(dir \$@)
	g++ \$(CXXFLAGS) -MMD -MP -c \$< -o \$@
-include \$(OBJS:.o=.d)
MK
make -f "$OUT/Makefile" "$@" 2>&1
