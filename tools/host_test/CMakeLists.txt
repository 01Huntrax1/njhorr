# Loads the built VST3 and checks that a held note keeps sounding while the editor window is destroyed and created again,
# and that stored sounds reach the DSP when a project is loaded without ever opening the editor.
#   cmake -S tools/host_test -B /tmp/host_test_b -DJUCE_DIR=<JUCE> && cmake --build /tmp/host_test_b -j3
#   xvfb-run -a /tmp/host_test_b/reopen_test_artefacts/Release/reopen_test <Njohrr.vst3>
cmake_minimum_required(VERSION 3.16)
project(reopen_test VERSION 1.0 LANGUAGES CXX C)
set(JUCE_DIR "" CACHE PATH "JUCE checkout")
add_subdirectory(${JUCE_DIR} juce)
juce_add_gui_app(reopen_test PRODUCT_NAME reopen_test)
target_sources(reopen_test PRIVATE reopen_test.cpp)
target_include_directories(reopen_test PRIVATE ${CMAKE_CURRENT_LIST_DIR}/../../include/choc)
target_compile_definitions(reopen_test PRIVATE JUCE_PLUGINHOST_VST3=1 JUCE_MODAL_LOOPS_PERMITTED=1 JUCE_USE_CURL=0 JUCE_WEB_BROWSER=0 JUCE_APPLICATION_NAME_STRING="reopen_test" JUCE_APPLICATION_VERSION_STRING="1")
target_link_libraries(reopen_test PRIVATE juce::juce_audio_processors juce::juce_audio_formats juce::juce_gui_extra juce::juce_recommended_config_flags)
