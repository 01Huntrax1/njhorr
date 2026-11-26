#include "Editors.h"
#include "OscDisplays.h"
#include "../NjoPhys.h"
#include "../NjoTableOps.h"
#include <algorithm>
#include <cmath>

namespace njo
{
    using namespace theme;

    namespace
    {
        struct Btn : public juce::Component
        {
            juce::String text; bool accent = false, over = false; std::function<void()> click;
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f);
                paintButton (g, r, accent, over, false, 3.0f);
                g.setColour (accent ? juce::Colours::white : ink); g.setFont (font (9.0f, true).withExtraKerningFactor (0.05f));
                g.drawText (text, r.toNearestInt(), juce::Justification::centred);
            }
            void mouseEnter (const juce::MouseEvent&) override { over = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { over = false; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && click) click(); }
        };

        void header (juce::Graphics& g, juce::Rectangle<int> r, const juce::String& t)
        {
            g.setColour (red); g.fillRect (juce::Rectangle<float> ((float) r.getX() + 12, (float) r.getY() + 13, 7, 7));
            g.setColour (ink); g.setFont (impact (13.0f));
            g.drawText (t.toUpperCase(), r.getX() + 26, r.getY() + 6, 560, 20, juce::Justification::centredLeft);
        }
    }

    // ====================================================================================================================== TableEditor
    // Wavefilter / Wavedistortion table: frames of 512 points.  Draw, Chebyshev harmonics, frame strip, undo, copy / paste, symmetry tools, generators, file drop.
    struct TableEditor::Impl
    {
        Impl (TableEditor& o, Ctx& c, SoundMemory& m, int osc, bool f) : owner (o), ctx (c), mem (m), os (osc), filter (f)
        {
            auto add = [this] (int row, const juce::String& t, std::function<void()> fn, bool accent = false)
            {
                auto* b = buttons.add (new Btn()); b->text = t; b->click = std::move (fn); b->accent = accent; rowOf.push_back (row); owner.addAndMakeVisible (b); return b;
            };
            closeBtn = add (-1, "CLOSE", [this] { flush(); owner.setVisible (false); if (owner.onClose) owner.onClose(); }, true);
            // every tool group is a menu: FRAME, EDIT, GENERATE, RASTER, RAZOR, PRESETS, FILE; UNDO and ALL FRAMES stay buttons
            auto menuBtn = [this, add] (const juce::String& t, std::function<void (juce::PopupMenu&)> fill, std::function<void (int)> pick) -> Btn*
            {
                Btn* bt = add (0, t + "  v", {}, false);
                bt->click = [this, bt, fill, pick] { juce::PopupMenu m; fill (m); juce::Component::SafePointer<juce::Component> sp (&owner); m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (bt), [sp, pick] (int r) { if (sp != nullptr && r > 0) pick (r); }); };
                return bt;
            };
            menuBtn ("FRAME", [this] (juce::PopupMenu& m)
            {
                m.addItem (1, "Previous frame"); m.addItem (2, "Next frame"); m.addSeparator(); m.addItem (3, "Add frame"); m.addItem (4, "Delete frame", frames() > 1);
                m.addSeparator(); m.addItem (5, "Copy frame"); m.addItem (6, "Paste frame", clip.size() == 512); m.addSeparator(); m.addItem (7, "Morph all frames (first to last)");
            }, [this] (int r)
            {
                if (r == 1) select (cur - 1); else if (r == 2) select (cur + 1); else if (r == 3) addFrame(); else if (r == 4) delFrame();
                else if (r == 5) clip.assign (frame(), frame() + 512);
                else if (r == 6) { if (clip.size() == 512) edit ([this] (float* v) { std::copy (clip.begin(), clip.end(), v); }); }
                else if (r == 7) morphAll();
            });
            menuBtn ("EDIT", [] (juce::PopupMenu& m)
            {
                m.addItem (1, "Smooth"); m.addItem (2, "Invert"); m.addItem (3, "Flip (reverse)"); m.addItem (4, "Normalize"); m.addItem (5, "Random"); m.addSeparator();
                m.addItem (6, "Odd symmetry"); m.addItem (7, "Even symmetry"); m.addItem (8, "Rectify"); m.addItem (9, "Quantise (8 levels)");
            }, [this] (int r)
            {
                if (r == 1) edit ([this] (float* v) { smooth (v); });
                else if (r == 2) edit ([] (float* v) { for (int i = 0; i < 512; ++i) v[i] = -v[i]; });
                else if (r == 3) edit ([] (float* v) { std::reverse (v, v + 512); });
                else if (r == 4) edit ([] (float* v) { float p = 0; for (int i = 0; i < 512; ++i) p = juce::jmax (p, std::abs (v[i])); if (p > 1.0e-4f) for (int i = 0; i < 512; ++i) v[i] /= p; });
                else if (r == 5) edit ([this] (float* v) { randomise (v); });
                else if (r == 6) edit ([] (float* v) { tblops::oddSymmetry (v); });
                else if (r == 7) edit ([] (float* v) { tblops::evenSymmetry (v); });
                else if (r == 8) edit ([] (float* v) { tblops::rectify (v); });
                else if (r == 9) edit ([] (float* v) { tblops::quantise (v, 8); });
            });
            menuBtn ("GENERATE", [this] (juce::PopupMenu& m) { const auto& nm = tblops::names (filter); for (size_t i = 0; i < nm.size(); ++i) m.addItem ((int) i + 1, nm[i]); },
                     [this] (int r) { const auto& nm = tblops::names (filter); if (r >= 1 && r <= (int) nm.size()) preset (nm[(size_t) r - 1]); });
            add (0, "UNDO", [this] { undo(); });
            add (0, "ALL FRAMES", [this] { allFrames = ! allFrames; buttons[(size_t) allBtn]->accent = allFrames; owner.repaint(); });
            allBtn = buttons.size() - 1;
            add (0, "PRESETS  v", [this] { presetMenu(); });
            presBtn = buttons.getLast();
            add (0, "RAZOR  v", [this] { razorMenu(); });
            razBtn = buttons.getLast();
            rastBtn = menuBtn ("RASTER: OFF", [this] (juce::PopupMenu& m)
            {
                static const int rv[5] = { 0, 8, 16, 32, 64 }; for (int i = 0; i < 5; ++i) m.addItem (i + 1, i == 0 ? juce::String ("Off") : juce::String (rv[i]) + " columns", true, rast == i);
            }, [this] (int r)
            {
                static const int rv[5] = { 0, 8, 16, 32, 64 }; rast = juce::jlimit (0, 4, r - 1); rastBtn->text = rast == 0 ? juce::String ("RASTER: OFF  v") : "RASTER: " + juce::String (rv[rast]) + "  v"; rastBtn->repaint(); owner.repaint();
            });
            menuBtn ("FILE", [] (juce::PopupMenu& m) { m.addItem (1, "Load a table / wave file..."); m.addItem (2, "Back to the default table"); },
                     [this] (int r)
                     {
                         if (r == 1) chooseFile();
                         else if (r == 2) defaultTable();
                     });
        }

        void defaultTable() { pushUndo(); fromBuiltIn = true; d.assign (16 * 512, 0.0f); for (int f2 = 0; f2 < 16; ++f2) for (int i = 0; i < 512; ++i) d[(size_t) (f2 * 512 + i)] = oscmodel::tblDefault (filter, f2, i); cur = juce::jlimit (0, 15, cur); name = "EDITED"; setPos(); touch(); commit(); }
        int frames() const { return (int) d.size() / 512; }
        void razorApply()
        {
            if (! rz.active()) return;
            pushUndo(); std::vector<float> o (512);
            for (int f = rzAll ? 0 : cur, e = rzAll ? frames() : cur + 1; f < e; ++f)
            { float* v = d.data() + (size_t) f * 512; tblops::razorRender (v, rz, o.data()); for (int i = 0; i < 512; ++i) v[i] = juce::jlimit (-1.0f, 1.0f, o[(size_t) i]); }
            rz.reset(); razBtn->accent = false; fromBuiltIn = false; touch(); commit();
        }
        // the razor of the wavetable editor: the live preview is drawn over the frame, APPLY bakes it into this frame (or all frames)
        // preset manager: factory sets (a morph through generators), user presets as files (all frames of the table)
        void presetMenu()
        {
            juce::PopupMenu m, fm, um, dm; const auto& fs = tblops::factorySets (filter); auto root = ctx.be.rootFolder();
            for (size_t i = 0; i < fs.size(); ++i) fm.addItem ((int) i + 1, fs[i].name);
            auto users = tblops::userNames (root, filter);
            for (int k = 0; k < users.size(); ++k) { um.addItem (2000 + k, users[k]); dm.addItem (3000 + k, users[k]); }
            m.addSubMenu ("Factory sets", fm); if (! users.isEmpty()) { m.addSubMenu ("User presets", um); m.addSubMenu ("Delete user preset", dm); }
            m.addSeparator(); m.addItem (1000, "Save the table as..."); m.addItem (1001, "Open preset folder");
            juce::Component::SafePointer<juce::Component> sp (&owner);
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (presBtn), [this, sp, users, root] (int r)
            {
                if (sp == nullptr || r <= 0) return;
                const auto& fs2 = tblops::factorySets (filter); std::vector<float> nd;
                auto put = [this] (std::vector<float> v) { pushUndo(); d = std::move (v); cur = juce::jlimit (0, frames() - 1, cur); fromBuiltIn = false; setPos(); touch(); commit(); };
                if (r <= (int) fs2.size()) put (tblops::buildFactory (filter, fs2[(size_t) r - 1]));
                else if (r == 1000)
                {
                    flush(); auto* w = new juce::AlertWindow (filter ? "Save Wavefilter table" : "Save Shaper table", "Name of the preset:", juce::MessageBoxIconType::NoIcon);
                    w->addTextEditor ("n", name.isEmpty() || name == "EDITED" ? "My table" : name, {}); w->addButton ("Save", 1, juce::KeyPress (juce::KeyPress::returnKey)); w->addButton ("Cancel", 0, juce::KeyPress (juce::KeyPress::escapeKey));
                    w->enterModalState (true, juce::ModalCallbackFunction::create ([this, sp, w, root] (int rr) { if (rr == 1 && sp != nullptr) tblops::saveUser (root, filter, w->getTextEditorContents ("n"), d); }), true);
                }
                else if (r == 1001) { tblops::presetDir (root, filter).createDirectory(); tblops::presetDir (root, filter).revealToUser(); }
                else if (r >= 3000 && r - 3000 < users.size()) tblops::removeUser (root, filter, users[r - 3000]);
                else if (r >= 2000 && r - 2000 < users.size()) { if (tblops::loadUser (root, filter, users[r - 2000], nd)) put (std::move (nd)); }
            });
        }
        void razorMenu()
        {
            juce::PopupMenu m, sg, sh, lv, tu, du, mx, ph;
            for (int n = 1; n <= 8; ++n) sg.addItem (100 + n, n == 1 ? "1 (off)" : juce::String (n) + " segments", true, rz.n == n);
            static const char* sn[5] = { "Source (the frame)", "Sine", "Saw", "Square", "Triangle" }; for (int i = 0; i < 5; ++i) sh.addItem (200 + i, sn[i], true, rz.shp[0] == i);
            lv.addItem (300, "All +1"); lv.addItem (301, "Alternate +1 / -1"); lv.addItem (302, "Rising"); lv.addItem (303, "Falling"); lv.addItem (304, "Alternate +1 / 0.5");
            tu.addItem (400, "None"); tu.addItem (401, "Alternate 0 / +12 st"); tu.addItem (402, "Rising +2 st per segment"); tu.addItem (403, "Alternate 0 / -12 st"); tu.addItem (404, "Alternate 0 / +7 st");
            static const float dv[5] = { 0.2f, 0.35f, 0.5f, 0.65f, 0.8f }; for (int i = 0; i < 5; ++i) du.addItem (500 + i, juce::String ((int) (dv[i] * 100)) + " %", true, std::abs (rz.duty - dv[i]) < 0.01f);
            static const float mv[4] = { 0.25f, 0.5f, 0.75f, 1.0f }; for (int i = 0; i < 4; ++i) mx.addItem (600 + i, juce::String ((int) (mv[i] * 100)) + " %", true, std::abs (rz.mix - mv[i]) < 0.01f);
            for (int i = 0; i < 4; ++i) ph.addItem (700 + i, juce::String (i * 25) + " % phase", true, std::abs (rz.ph[0] - 0.25f * (float) i) < 0.01f);
            m.addSubMenu ("Segments", sg); m.addSubMenu ("Shape of all segments", sh); m.addSubMenu ("Level pattern", lv); m.addSubMenu ("Tune pattern", tu);
            m.addSubMenu ("Duty (alternating lengths)", du); m.addSubMenu ("Mix", mx); m.addSubMenu ("Start phase", ph);
            m.addSeparator(); m.addItem (800, "Constant polarity", true, rz.pol); m.addItem (801, "Apply to all frames", true, rzAll);
            m.addSeparator(); m.addItem (900, "APPLY", rz.active()); m.addItem (901, "Reset razor");
            juce::Component::SafePointer<juce::Component> sp (&owner);
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (razBtn), [this, sp] (int r)
            {
                if (sp == nullptr || r <= 0) return;
                if (r > 100 && r <= 108) rz.n = r - 100;
                else if (r >= 200 && r < 205) for (auto& x : rz.shp) x = r - 200;
                else if (r >= 300 && r < 305) for (int k = 0; k < 8; ++k) rz.lvl[k] = r == 300 ? 1.0f : r == 301 ? ((k & 1) ? -1.0f : 1.0f) : r == 302 ? (float) (k + 1) / (float) juce::jmax (1, rz.n) : r == 303 ? 1.0f - (float) k / (float) juce::jmax (1, rz.n) : ((k & 1) ? 0.5f : 1.0f);
                else if (r >= 400 && r < 405) for (int k = 0; k < 8; ++k) rz.semi[k] = r == 400 ? 0.0f : r == 401 ? ((k & 1) ? 12.0f : 0.0f) : r == 402 ? 2.0f * (float) k : r == 403 ? ((k & 1) ? -12.0f : 0.0f) : ((k & 1) ? 7.0f : 0.0f);
                else if (r >= 500 && r < 505) { static const float dv2[5] = { 0.2f, 0.35f, 0.5f, 0.65f, 0.8f }; rz.duty = dv2[r - 500]; }
                else if (r >= 600 && r < 604) { static const float mv2[4] = { 0.25f, 0.5f, 0.75f, 1.0f }; rz.mix = mv2[r - 600]; }
                else if (r >= 700 && r < 704) for (auto& x : rz.ph) x = 0.25f * (float) (r - 700);
                else if (r == 800) rz.pol = ! rz.pol;
                else if (r == 801) rzAll = ! rzAll;
                else if (r == 900) { razorApply(); owner.repaint(); return; }
                else if (r == 901) rz.reset();
                razBtn->accent = rz.active(); razBtn->repaint(); owner.repaint();
            });
        }
        void load()
        {
            if (auto* sl = mem.get (filter ? SoundMemory::FilterTable : SoundMemory::ShaperTable, os); sl && sl->data.size() >= 512)
            {
                d = sl->data; d.resize ((d.size() / 512) * 512); name = sl->name;
            }
            else
            {
                d.assign (16 * 512, 0.0f); name = "EDITED";
                for (int f = 0; f < 16; ++f) for (int i = 0; i < 512; ++i) d[(size_t) (f * 512 + i)] = oscmodel::tblDefault (filter, f, i);
                fromBuiltIn = true;
            }
            const float pos = ctx.get (posId());
            cur = juce::jlimit (0, frames() - 1, juce::roundToInt (pos * (float) (frames() - 1)));
            harmDirty = true;
        }
        int posId() const { return oscId (os, oscKey (filter ? "wfpos" : "wdpos")); }
        void setPos() { ctx.begin (posId()); ctx.set (posId(), frames() <= 1 ? 0.0f : (float) cur / (float) (frames() - 1)); ctx.end (posId()); }
        void select (int f) { cur = juce::jlimit (0, frames() - 1, f); setPos(); harmDirty = true; owner.repaint(); }
        float* frame() { return d.data() + (size_t) cur * 512; }
        void commit() { dirty = false; selfWrite = true; mem.set (filter ? SoundMemory::FilterTable : SoundMemory::ShaperTable, os, name, {}, d); selfWrite = false; }
        void flush() { if (dirty) commit(); owner.stopTimer(); }
        void touch() { dirty = true; harmDirty = true; owner.repaint(); if (! owner.isTimerRunning()) owner.startTimer (250); }
        void pushUndo() { undoStack.push_back (d); if (undoStack.size() > 30) undoStack.erase (undoStack.begin()); }
        void undo()
        {
            if (undoStack.empty()) return;
            d = undoStack.back(); undoStack.pop_back(); cur = juce::jlimit (0, frames() - 1, cur); setPos(); touch(); commit();
        }
        void edit (const std::function<void (float*)>& fn)
        {
            pushUndo();
            for (int f = allFrames ? 0 : cur, e = allFrames ? frames() : cur + 1; f < e; ++f)
            {
                float* v = d.data() + (size_t) f * 512; fn (v);
                for (int i = 0; i < 512; ++i) v[i] = juce::jlimit (-1.0f, 1.0f, v[i]);
            }
            fromBuiltIn = false; touch(); commit();
        }
        static void smooth (float* v)
        {
            float t[512];
            for (int pass = 0; pass < 2; ++pass)
            {
                for (int i = 0; i < 512; ++i) t[i] = 0.25f * v[juce::jmax (0, i - 1)] + 0.5f * v[i] + 0.25f * v[juce::jmin (511, i + 1)];
                std::copy (t, t + 512, v);
            }
        }
        void randomise (float* v)
        {
            juce::Random r;
            float k[9]; for (float& x : k) x = r.nextFloat() * 2.0f - 1.0f;
            for (int i = 0; i < 512; ++i)
            {
                float x = (float) i / 511.0f * 8.0f; int a = (int) x; float f = x - (float) a;
                float w = f * f * (3.0f - 2.0f * f);
                v[i] = k[a] + (k[juce::jmin (8, a + 1)] - k[a]) * w;
            }
        }
        void preset (const juce::String& n) { edit ([this, n] (float* v) { tblops::generate (filter, n, v); }); }
        void addFrame()
        {
            if (frames() >= 64) return;
            pushUndo();
            std::vector<float> copy (frame(), frame() + 512);
            d.insert (d.begin() + (cur + 1) * 512, copy.begin(), copy.end());
            ++cur; setPos(); touch(); commit();
        }
        void delFrame()
        {
            if (frames() <= 1) return;
            pushUndo();
            d.erase (d.begin() + cur * 512, d.begin() + (cur + 1) * 512);
            cur = juce::jmin (cur, frames() - 1); setPos(); touch(); commit();
        }
        // the frames between the first and the last one become a linear blend of the two
        void morphAll()
        {
            const int n = frames(); if (n < 3) return;
            pushUndo();
            for (int f = 1; f < n - 1; ++f)
                for (int i = 0; i < 512; ++i)
                    d[(size_t) (f * 512 + i)] = d[(size_t) i] + (d[(size_t) ((n - 1) * 512 + i)] - d[(size_t) i]) * (float) f / (float) (n - 1);
            touch(); commit();
        }
        void chooseFile()
        {
            chooser = std::make_unique<juce::FileChooser> ("Load a table or wave file", juce::File(), SoundMemory::fileWildcard());
            chooser->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles, [this] (const juce::FileChooser& fc)
            {
                auto f = fc.getResult(); if (f.existsAsFile()) loadFile (f);
            });
        }
        void loadFile (const juce::File& f) { pushUndo(); mem.load (filter ? SoundMemory::FilterTable : SoundMemory::ShaperTable, os, f, {}); }   // the change listener reloads the frames
        void harmonics()
        {
            if (! harmDirty) return;
            tblops::chebAnalyse (frame(), hv.data()); harmDirty = false;
        }

        juce::Rectangle<int> canvas, harm, strip;
        void paintAll (juce::Graphics& g)
        {
            auto all = owner.getLocalBounds();
            paintCard (g, all.toFloat());
            header (g, all, juce::String (filter ? "Wavefilter editor" : "Wavedistortion editor") + "  -  OSC " + juce::String (os + 1) + "  -  " + name);
            paintInset (g, canvas.toFloat(), 4.0f);
            auto r = canvas.toFloat().reduced (10.0f, 8.0f);
            auto X = [&] (float t) { return r.getX() + t * r.getWidth(); };
            auto Y = [&] (float v) { return r.getY() + (0.5f - 0.5f * v) * r.getHeight(); };
            g.setColour (juce::Colours::white.withAlpha (0.07f));
            for (int i = 1; i < 8; ++i) g.drawVerticalLine ((int) X ((float) i / 8.0f), r.getY(), r.getBottom());
            for (int i = 1; i < 4; ++i) g.drawHorizontalLine ((int) Y (-1.0f + (float) i * 0.5f), r.getX(), r.getRight());
            if (rast > 0)
            {
                static const int rv[5] = { 0, 8, 16, 32, 64 }; const int nc = rv[rast];
                g.setColour (juce::Colour (0xffff3e30).withAlpha (0.16f));
                for (int i = 1; i < nc; ++i) g.drawVerticalLine ((int) X ((float) i / (float) nc), r.getY(), r.getBottom());
                for (int i = 1; i < 16; ++i) g.drawHorizontalLine ((int) Y (-1.0f + (float) i * 0.125f), r.getX(), r.getRight());
            }
            g.setColour (juce::Colours::white.withAlpha (0.20f)); g.drawHorizontalLine ((int) Y (0.0f), r.getX(), r.getRight()); g.drawVerticalLine ((int) X (0.5f), r.getY(), r.getBottom());
            if (! filter) { g.setColour (juce::Colours::white.withAlpha (0.14f)); g.drawLine (X (0), Y (-1), X (1), Y (1)); }
            auto path = [&] (int f)
            {
                juce::Path p;
                for (int i = 0; i < 512; ++i)
                {
                    float x = X ((float) i / 511.0f), y = Y (d[(size_t) (f * 512 + i)]);
                    if (i == 0) p.startNewSubPath (x, y); else p.lineTo (x, y);
                }
                return p;
            };
            if (cur > 0) { g.setColour (juce::Colour (0xff8a909a).withAlpha (0.28f)); g.strokePath (path (cur - 1), juce::PathStrokeType (1.0f)); }
            if (cur < frames() - 1) { g.setColour (juce::Colour (0xff8a909a).withAlpha (0.28f)); g.strokePath (path (cur + 1), juce::PathStrokeType (1.0f)); }
            if (rz.active())   // razor preview
            {
                std::vector<float> o (512); tblops::razorRender (frame(), rz, o.data()); juce::Path pp;
                for (int i = 0; i < 512; ++i) { float x = X ((float) i / 511.0f), y = Y (juce::jlimit (-1.0f, 1.0f, o[(size_t) i])); if (i == 0) pp.startNewSubPath (x, y); else pp.lineTo (x, y); }
                g.setColour (juce::Colour (0xff6fd0ff)); g.strokePath (pp, juce::PathStrokeType (1.6f));
            }
            auto p = path (cur);
            g.setColour (juce::Colour (0xffff3e30).withAlpha (0.25f)); g.strokePath (p, juce::PathStrokeType (6.0f));
            g.setColour (juce::Colour (0xffff6f65)); g.strokePath (p, juce::PathStrokeType (2.0f));
            g.setColour (dim); g.setFont (mono (8.5f, false));
            if (filter)
            {
                const float range = ctx.get (oscId (os, oscKey ("wfrange")));
                g.drawText (juce::String (-range * 0.5f, 1) + " oct", canvas.reduced (12, 10), juce::Justification::bottomLeft);
                g.drawText ("CUTOFF", canvas.reduced (12, 10), juce::Justification::centredBottom);
                g.drawText ("+" + juce::String (range * 0.5f, 1) + " oct", canvas.reduced (12, 10), juce::Justification::bottomRight);
                g.drawText ("+1", canvas.reduced (12, 10), juce::Justification::topLeft);
                g.drawText ("-1", canvas.reduced (12, 24), juce::Justification::bottomLeft);
            }
            else
            {
                g.drawText ("OUTPUT +1", canvas.reduced (12, 10), juce::Justification::topLeft);
                g.drawText ("INPUT -1", canvas.reduced (12, 24), juce::Justification::bottomLeft);
                g.drawText ("INPUT +1", canvas.reduced (12, 24), juce::Justification::bottomRight);
            }
            g.drawText ("FRAME " + juce::String (cur + 1) + " / " + juce::String (frames()) + (fromBuiltIn ? "  (built-in: editing creates your own)" : "") + (allFrames ? "  - tools act on ALL frames" : "") + "   wheel = frame",
                        canvas.reduced (12, 10), juce::Justification::topRight);

            // Chebyshev terms: bar n sets the n-th harmonic that a sine at the input gets from this curve
            paintInset (g, harm.toFloat(), 4.0f);
            harmonics();
            auto hr = harm.toFloat().reduced (6.0f, 16.0f);
            const float bw = hr.getWidth() / (float) tblops::NH, mid = hr.getCentreY();
            g.setColour (juce::Colours::white.withAlpha (0.2f)); g.drawHorizontalLine ((int) mid, hr.getX(), hr.getRight());
            g.setColour (dim); g.setFont (mono (8.0f, false));
            g.drawText (filter ? "COSINE TERMS 1..16  -  DRAG TO SET" : "CHEBYSHEV 1..16 = HARMONICS OF A SINE INPUT  -  DRAG TO SET", harm.getX() + 6, harm.getY() + 2, harm.getWidth() - 12, 12, juce::Justification::left);
            for (int k = 0; k < tblops::NH; ++k)
            {
                const float v = juce::jlimit (-1.0f, 1.0f, hv[(size_t) k]), h = v * hr.getHeight() * 0.5f;
                g.setColour (juce::Colour (0xff7fd0ff).withAlpha (0.85f));
                g.fillRect (juce::Rectangle<float> (hr.getX() + bw * (float) k + 1.0f, h >= 0 ? mid - h : mid, juce::jmax (1.0f, bw - 2.0f), juce::jmax (1.0f, std::abs (h))));
                g.setColour (dim); g.drawText (juce::String (k + 1), (int) (hr.getX() + bw * (float) k), harm.getBottom() - 13, (int) bw, 11, juce::Justification::centred);
            }
            // frame strip
            paintInset (g, strip.toFloat(), 3.0f);
            const int n = frames(); const float sw = (float) strip.getWidth() / (float) n;
            for (int f = 0; f < n; ++f)
            {
                auto cell = juce::Rectangle<float> ((float) strip.getX() + sw * (float) f, (float) strip.getY(), sw, (float) strip.getHeight()).reduced (1.0f, 2.0f);
                if (f == cur) { g.setColour (juce::Colour (0xffff3e30).withAlpha (0.22f)); g.fillRect (cell); }
                juce::Path q; const int step = sw < 24.0f ? 32 : 8;
                for (int i = 0; i < 512; i += step)
                {
                    float x = cell.getX() + 1.0f + (float) i / 511.0f * (cell.getWidth() - 2.0f), y = cell.getCentreY() - d[(size_t) (f * 512 + i)] * (cell.getHeight() * 0.5f - 2.0f);
                    if (i == 0) q.startNewSubPath (x, y); else q.lineTo (x, y);
                }
                g.setColour (f == cur ? juce::Colour (0xffff6f65) : juce::Colour (0xff8a909a)); g.strokePath (q, juce::PathStrokeType (1.0f));
            }
            if (dropOver) { g.setColour (juce::Colour (0xffff3e30)); g.drawRect (all, 2); g.setFont (font (11.0f, true)); g.drawText ("DROP A TABLE OR WAVE FILE", canvas, juce::Justification::centred); }
        }
        void layout()
        {
            auto b = owner.getLocalBounds().reduced (12, 8);
            auto head = b.removeFromTop (28);
            closeBtn->setBounds (head.removeFromRight (80).reduced (0, 2));
            const int toolsH = 34;
            auto tools = b.removeFromBottom (toolsH);
            b.removeFromBottom (6);
            strip = b.removeFromBottom (juce::jmin (46, b.getHeight() / 5)); b.removeFromBottom (6);
            auto bb = b; harm = bb.removeFromRight (juce::jmax (200, b.getWidth() * 36 / 100)); bb.removeFromRight (8);
            canvas = bb;
            const int nb = buttons.size() - 1, gap = 6; const int bw = juce::jmin (118, (tools.getWidth() - (nb - 1) * gap) / juce::jmax (1, nb));
            for (int i = 1; i < buttons.size(); ++i) buttons[i]->setBounds (tools.getX() + (i - 1) * (bw + gap), tools.getY() + 4, bw, 26);
        }
        TableEditor& owner; Ctx& ctx; SoundMemory& mem; int os; bool filter;
        std::vector<float> d; juce::String name; int cur = 0; bool dirty = false, fromBuiltIn = false, allFrames = false, harmDirty = true, selfWrite = false, dropOver = false;
        juce::OwnedArray<Btn> buttons; std::vector<int> rowOf; Btn* closeBtn = nullptr; Btn* rastBtn = nullptr; Btn* razBtn = nullptr; Btn* presBtn = nullptr; tblops::Razor rz; bool rzAll = false; int rast = 0; int allBtn = 0; int lastIdx = -1; float lastV = 0.0f;
        std::vector<std::vector<float>> undoStack; std::vector<float> clip; std::array<float, tblops::NH> hv {}; int mode = 0;   // mode: 1 draw, 2 harmonics, 3 strip
        std::unique_ptr<juce::FileChooser> chooser;
    };

    TableEditor::TableEditor (Ctx& c, SoundMemory& m, int osc, bool f) : impl (new Impl (*this, c, m, osc, f)) { c.addListener (this); m.addChangeListener (this); setVisible (false); setName ("tableEditor"); }
    TableEditor::~TableEditor() { impl->mem.removeChangeListener (this); impl->ctx.removeListener (this); }
    void TableEditor::open() { impl->fromBuiltIn = false; impl->undoStack.clear(); impl->load(); setVisible (true); toFront (false); resized(); repaint(); }
    void TableEditor::testApply (const juce::String& n, int f, int k, float v)
    {
        impl->select (f); impl->preset (n);
        if (k > 0) { impl->pushUndo(); tblops::chebSet (impl->frame(), k, v); impl->touch(); impl->commit(); }
        repaint();
    }
    void TableEditor::paint (juce::Graphics& g) { impl->paintAll (g); }
    void TableEditor::resized() { impl->layout(); }
    void TableEditor::timerCallback() { if (impl->dirty) impl->commit(); else stopTimer(); }
    void TableEditor::changeListenerCallback (juce::ChangeBroadcaster*)
    {
        if (! isVisible() || impl->dirty || impl->selfWrite || impl->mode != 0) return;
        auto* sl = impl->mem.get (impl->filter ? SoundMemory::FilterTable : SoundMemory::ShaperTable, impl->os);
        if (sl != nullptr && sl->data.size() >= 512 && sl->data != impl->d) { impl->fromBuiltIn = false; impl->load(); repaint(); }
    }
    void TableEditor::paramChanged (int num, float v)
    {
        if (isVisible() && num == impl->posId() && impl->frames() > 0)
        {
            int f = juce::jlimit (0, impl->frames() - 1, juce::roundToInt (v * (float) (impl->frames() - 1)));
            if (f != impl->cur) { impl->cur = f; impl->harmDirty = true; repaint(); }
        }
    }
    bool TableEditor::isInterestedInFileDrag (const juce::StringArray& f) { for (auto& n : f) if (juce::File (n).hasFileExtension ("wav;aif;aiff;flac;ogg;mp3;vitaltable")) return true; return false; }
    void TableEditor::fileDragEnter (const juce::StringArray&, int, int) { impl->dropOver = true; repaint(); }
    void TableEditor::fileDragExit (const juce::StringArray&) { impl->dropOver = false; repaint(); }
    void TableEditor::filesDropped (const juce::StringArray& f, int, int) { impl->dropOver = false; if (f.size() > 0) impl->loadFile (juce::File (f[0])); repaint(); }
    void TableEditor::mouseDown (const juce::MouseEvent& e)
    {
        auto pt = e.getPosition(); auto& I = *impl;
        if (I.strip.contains (pt)) { I.mode = 3; mouseDrag (e); return; }
        if (I.harm.contains (pt)) { I.pushUndo(); I.mode = 2; mouseDrag (e); return; }
        if (! I.canvas.contains (pt)) { I.mode = 0; return; }
        I.pushUndo(); I.mode = 1; I.lastIdx = -1; mouseDrag (e);
    }
    void TableEditor::mouseDrag (const juce::MouseEvent& e)
    {
        auto& I = *impl;
        if (I.mode == 3) { I.select ((e.getPosition().x - I.strip.getX()) * I.frames() / juce::jmax (1, I.strip.getWidth())); return; }
        if (I.mode == 2)
        {
            auto hr = I.harm.toFloat().reduced (6.0f, 16.0f);
            const int k = juce::jlimit (0, tblops::NH - 1, (int) ((e.position.x - hr.getX()) / (hr.getWidth() / (float) tblops::NH)));
            float v = juce::jlimit (-1.0f, 1.0f, (hr.getCentreY() - e.position.y) / (hr.getHeight() * 0.5f));
            if (std::abs (v) < 0.03f) v = 0.0f;
            I.harmonics(); tblops::chebSet (I.frame(), k + 1, v); I.hv[(size_t) k] = v; I.fromBuiltIn = false; I.dirty = true; repaint (); if (! isTimerRunning()) startTimer (250);
            return;
        }
        if (I.mode != 1) return;
        auto r = I.canvas.toFloat().reduced (10.0f, 8.0f);
        float t = juce::jlimit (0.0f, 1.0f, (e.position.x - r.getX()) / r.getWidth());
        float v = juce::jlimit (-1.0f, 1.0f, 1.0f - 2.0f * (e.position.y - r.getY()) / r.getHeight());
        int idx = juce::roundToInt (t * 511.0f);
        float* f = I.frame();
        if (I.rast > 0)    // raster: the value snaps to 1/16 of the range and holds over a whole grid cell
        {
            static const int rv[5] = { 0, 8, 16, 32, 64 }; const int nc = rv[I.rast];
            v = juce::jlimit (-1.0f, 1.0f, std::round (v * 8.0f) / 8.0f);
            const int c = juce::jmin (nc - 1, (int) (t * (float) nc));
            const int a = c * 512 / nc, b = (c + 1) * 512 / nc - 1;
            for (int i = a; i <= b; ++i) f[i] = v;
            I.lastIdx = idx; I.lastV = v; I.fromBuiltIn = false; I.touch(); return;
        }
        if (I.lastIdx < 0) { f[idx] = v; I.lastV = v; }
        else
        {
            int a = I.lastIdx, b = idx; float va = I.lastV, vb = v;
            if (a > b) { std::swap (a, b); std::swap (va, vb); }
            for (int i = a; i <= b; ++i) f[i] = b == a ? vb : va + (vb - va) * (float) (i - a) / (float) (b - a);
        }
        I.lastIdx = idx; I.lastV = v; I.fromBuiltIn = false; I.touch();
    }
    void TableEditor::mouseUp (const juce::MouseEvent&) { impl->lastIdx = -1; impl->mode = 0; impl->harmDirty = true; if (impl->dirty) impl->commit(); repaint(); }
    void TableEditor::mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails& w) { impl->select (impl->cur + (w.deltaY > 0 ? -1 : 1)); }

    // ====================================================================================================================== ModeEditor
    struct ModeEditor::Impl
    {
        Impl (ModeEditor& o, Ctx& c, SoundMemory& m, int osc) : owner (o), ctx (c), mem (m), os (osc)
        {
            auto add = [this] (const juce::String& t, std::function<void()> fn, bool accent = false)
            {
                auto* b = buttons.add (new Btn()); b->text = t; b->click = std::move (fn); b->accent = accent; owner.addAndMakeVisible (b); return b;
            };
            closeBtn = add ("CLOSE", [this] { flush(); owner.setVisible (false); if (owner.onClose) owner.onClose(); }, true);
            add ("RESET ALL", [this] { std::fill (v.begin(), v.end(), 1.0f); changed(); });
            add ("ODD MODES", [this] { for (int i = 0; i < 16; ++i) v[(size_t) i * 3 + 1] = (i % 2 == 0) ? 1.0f : 0.0f; changed(); });
            add ("EVEN MODES", [this] { for (int i = 0; i < 16; ++i) v[(size_t) i * 3 + 1] = (i % 2 == 1) ? 1.0f : 0.0f; changed(); });
            add ("STRETCH", [this] { for (int i = 0; i < 16; ++i) v[(size_t) i * 3] = juce::jlimit (0.5f, 2.0f, v[(size_t) i * 3] * (1.0f + 0.012f * (float) i)); changed(); });
            add ("SQUEEZE", [this] { for (int i = 0; i < 16; ++i) v[(size_t) i * 3] = juce::jlimit (0.5f, 2.0f, v[(size_t) i * 3] / (1.0f + 0.012f * (float) i)); changed(); });
            add ("RANDOMISE", [this] { juce::Random r; for (int i = 0; i < 16; ++i) { v[(size_t) i * 3] = std::pow (2.0f, (r.nextFloat() - 0.5f) * 0.3f); v[(size_t) i * 3 + 1] = r.nextFloat() * 1.6f + 0.1f; v[(size_t) i * 3 + 2] = std::pow (2.0f, (r.nextFloat() - 0.5f) * 3.0f); } changed(); });
            add ("DECAY TILT", [this] { for (int i = 0; i < 16; ++i) v[(size_t) i * 3 + 2] = juce::jlimit (0.1f, 4.0f, v[(size_t) i * 3 + 2] * std::pow (0.85f, (float) i * 0.5f)); changed(); });
            tabA = add ("PHYSICAL A", [this] { openSet (0); }); tabB = add ("PHYSICAL B", [this] { openSet (1); });
            v.assign (48, 1.0f);
        }
        int idx() const { return os * 3 + set; }
        void openSet (int s)
        {
            flush(); set = s;
            v.assign (48, 1.0f);
            if (auto* sl = mem.get (SoundMemory::ModeEdit, idx()); sl && sl->data.size() == 48) v = sl->data;
            owner.repaint();
        }
        bool isDefault() const { return std::all_of (v.begin(), v.end(), [] (float x) { return std::abs (x - 1.0f) < 1.0e-4f; }); }
        void commit()
        {
            dirty = false;
            if (isDefault()) mem.clear (SoundMemory::ModeEdit, idx()); else mem.set (SoundMemory::ModeEdit, idx(), "EDIT", {}, v);
        }
        void flush() { if (dirty) commit(); owner.stopTimer(); }
        void changed() { dirty = true; owner.repaint(); if (! owner.isTimerRunning()) owner.startTimer (120); }

        // base values of the mode set from the parameters (before the edits)
        struct Base { float f[16], a[16]; };
        Base base() const
        {
            Base b {};
            auto P = [&] (const char* k) { return ctx.get (set == 2 ? oscId (os, oscKey (k)) : phys::phyId (os, phys::key (k))); };
            int model; float hit, inh, tune;
            if (set == 0)      { model = juce::roundToInt (P ("phmodA")); hit = P ("phhitA"); inh = P ("phinhA"); tune = 0.0f; }
            else if (set == 1) { model = juce::roundToInt (P ("phmodB")); hit = P ("phhitB"); inh = P ("phinhB"); tune = P ("phtunB"); }
            else               { model = juce::roundToInt (P ("rsmod")); hit = P ("rshit"); inh = P ("rsinh"); tune = P ("rstune"); }
            model = juce::jlimit (0, 8, model);
            const float f0 = 220.0f * std::pow (2.0f, tune / 12.0f);
            float amax = 1.0e-4f;
            for (int i = 0; i < 16; ++i)
            {
                float r = phys::RAT[model][i] * (1.0f + inh * 0.004f * (float) (i * i));
                b.f[i] = f0 * r;
                b.a[i] = std::abs (std::sin (3.14159265f * hit * (float) (i + 1))) / std::pow ((float) (i + 1), phys::AEXP[model]);
                amax = juce::jmax (amax, b.a[i]);
            }
            for (float& a : b.a) a /= amax;
            return b;
        }

        // layout: spectrum on top, then three editable rows (frequency, gain, decay), mode numbers / Hz at the bottom
        juce::Rectangle<int> area, spec, rows[3];
        void layout()
        {
            auto b = owner.getLocalBounds().reduced (12, 8);
            auto head = b.removeFromTop (28);
            closeBtn->setBounds (head.removeFromRight (80).reduced (0, 2));
            const bool phy = ctx.get (oscId (os, oscKey ("type"))) > 2.5f && ctx.get (oscId (os, oscKey ("type"))) < 3.5f;
            tabA->setVisible (phy); tabB->setVisible (phy);
            head.removeFromRight (10); tabB->setBounds (head.removeFromRight (110).reduced (0, 2)); head.removeFromRight (4); tabA->setBounds (head.removeFromRight (110).reduced (0, 2));
            tabA->accent = set == 0; tabB->accent = set == 1;
            auto tools = b.removeFromBottom (34);
            for (int i = 1, x = tools.getX(); i <= 7; ++i, x += 104) buttons[i]->setBounds (x, tools.getY() + 4, 98, 26);
            b.removeFromBottom (6);
            area = b;
            auto c = b.withTrimmedLeft (86).withTrimmedBottom (26);
            spec = c.removeFromTop (juce::jmin (130, c.getHeight() / 3)); c.removeFromTop (8);
            const int rh = (c.getHeight() - 16) / 3;
            for (int i = 0; i < 3; ++i) { rows[i] = c.removeFromTop (rh); c.removeFromTop (8); }
        }
        float colX (int i) const { return (float) rows[0].getX() + ((float) i + 0.5f) * (float) rows[0].getWidth() / 16.0f; }
        // editable value <-> normalised position (0 bottom .. 1 top)
        static float toPos (int row, float x)
        {
            if (row == 0) return juce::jlimit (0.0f, 1.0f, 0.5f + std::log2 (juce::jmax (0.01f, x)) / 2.0f);        // 0.5 .. 2 on a log scale (centre = 1)
            if (row == 1) return juce::jlimit (0.0f, 1.0f, x / 2.0f);                                                  // 0 .. 2
            return juce::jlimit (0.0f, 1.0f, 0.5f + std::log2 (juce::jmax (0.01f, x)) / 6.64f);                        // 0.1 .. 10 on a log scale (centre = 1)
        }
        static float fromPos (int row, float p)
        {
            p = juce::jlimit (0.0f, 1.0f, p);
            if (row == 0) return std::pow (2.0f, (p - 0.5f) * 2.0f);
            if (row == 1) return p * 2.0f;
            return std::pow (2.0f, (p - 0.5f) * 6.64f);
        }
        void paintAll (juce::Graphics& g)
        {
            auto all = owner.getLocalBounds();
            paintCard (g, all.toFloat());
            static const char* setName[3] = { "Physical resonator A", "Physical resonator B", "Resonator stage" };
            header (g, all, juce::String ("Resonator editor  -  OSC ") + juce::String (os + 1) + "  -  " + setName[set] + (isDefault() ? "" : "  (edited)"));
            auto b = base();
            // spectrum
            paintInset (g, spec.toFloat(), 4.0f);
            {
                const float fLo = 30.0f, fHi = 16000.0f;
                auto xOf = [&] (float f) { return (float) spec.getX() + 8.0f + std::log (f / fLo) / std::log (fHi / fLo) * ((float) spec.getWidth() - 16.0f); };
                g.setColour (juce::Colours::white.withAlpha (0.07f));
                for (float f : { 100.0f, 1000.0f, 10000.0f }) { g.drawVerticalLine ((int) xOf (f), (float) spec.getY(), (float) spec.getBottom()); }
                g.setColour (dim); g.setFont (mono (8.0f, false));
                g.drawText ("100", (int) xOf (100) + 3, spec.getBottom() - 14, 40, 12, juce::Justification::left); g.drawText ("1k", (int) xOf (1000) + 3, spec.getBottom() - 14, 40, 12, juce::Justification::left);
                g.drawText ("10k", (int) xOf (10000) + 3, spec.getBottom() - 14, 40, 12, juce::Justification::left);
                g.drawText ("MODES: KEY A3 = 220 Hz + TUNE   (grey = unedited)", spec.reduced (8, 4), juce::Justification::topLeft);
                for (int i = 0; i < 16; ++i)
                {
                    const float fe = b.f[i] * v[(size_t) i * 3], ge = b.a[i] * v[(size_t) i * 3 + 1];
                    const float hmax = (float) spec.getHeight() - 30.0f;
                    if (b.f[i] < 18000.0f) { g.setColour (juce::Colour (0xff8a909a).withAlpha (0.35f)); g.drawLine (xOf (b.f[i]), (float) spec.getBottom() - 6, xOf (b.f[i]), (float) spec.getBottom() - 6 - hmax * b.a[i], 2.0f); }
                    if (fe < 18000.0f) { g.setColour (juce::Colour (0xffff3e30)); g.drawLine (xOf (fe), (float) spec.getBottom() - 6, xOf (fe), (float) spec.getBottom() - 6 - hmax * juce::jmin (1.0f, ge * 0.5f + 0.0f) , 3.0f); }
                }
            }
            static const char* rowName[3] = { "FREQUENCY\nx0.5 .. x2", "GAIN\n0 .. 2", "DECAY\nx0.1 .. x10" };
            for (int r = 0; r < 3; ++r)
            {
                auto rc = rows[r];
                paintInset (g, rc.toFloat(), 4.0f);
                g.setColour (orange); g.setFont (font (8.0f, true).withExtraKerningFactor (0.15f));
                g.drawFittedText (rowName[r], area.getX(), rc.getY(), 82, rc.getHeight(), juce::Justification::centredLeft, 2);
                // centre line (value 1)
                const float y1 = (float) rc.getBottom() - toPos (r, 1.0f) * (float) rc.getHeight();
                g.setColour (juce::Colours::white.withAlpha (0.18f)); g.drawHorizontalLine ((int) y1, (float) rc.getX(), (float) rc.getRight());
                for (int i = 0; i < 16; ++i)
                {
                    const float x = colX (i), w = (float) rc.getWidth() / 16.0f * 0.62f;
                    const float val = v[(size_t) i * 3 + (size_t) r];
                    const float y = (float) rc.getBottom() - toPos (r, val) * (float) rc.getHeight();
                    const bool edited = std::abs (val - 1.0f) > 1.0e-3f;
                    g.setColour (edited ? juce::Colour (0xffff3e30).withAlpha (0.85f) : juce::Colour (0xff777c85).withAlpha (0.65f));
                    if (r == 1) g.fillRect (juce::Rectangle<float> (x - w * 0.5f, y, w, (float) rc.getBottom() - y));
                    else g.fillRect (juce::Rectangle<float> (x - w * 0.5f, juce::jmin (y, y1), w, juce::jmax (2.0f, std::abs (y - y1))));
                    g.setColour (juce::Colours::white.withAlpha (0.85f)); g.fillRect (juce::Rectangle<float> (x - w * 0.5f, y - 1.0f, w, 2.0f));
                }
            }
            g.setColour (dim); g.setFont (mono (8.0f, false));
            for (int i = 0; i < 16; ++i)
            {
                auto cell = juce::Rectangle<float> (colX (i) - 24.0f, (float) rows[2].getBottom() + 3, 48.0f, 22.0f);
                g.drawText (juce::String (i + 1), cell.withHeight (10), juce::Justification::centred);
                const float fe = b.f[i] * v[(size_t) i * 3];
                g.drawText (fe >= 1000.0f ? juce::String (fe / 1000.0f, 2) + "k" : juce::String (juce::roundToInt (fe)), cell.withTrimmedTop (10), juce::Justification::centred);
            }
            g.drawFittedText ("drag across the bars to draw  -  double-click a bar to reset it\nthe sound follows while you draw", juce::Rectangle<int> (area.getX() + 730, area.getBottom() + 6, area.getWidth() - 730, 30), juce::Justification::centredRight, 2);
        }
        int hitRow (juce::Point<int> p) const { for (int r = 0; r < 3; ++r) if (rows[r].expanded (0, 4).contains (p)) return r; return -1; }
        void draw (const juce::MouseEvent& e)
        {
            if (dragRow < 0) return;
            auto rc = rows[dragRow];
            int col = juce::jlimit (0, 15, (int) ((e.position.x - (float) rc.getX()) / ((float) rc.getWidth() / 16.0f)));
            float p = ((float) rc.getBottom() - e.position.y) / (float) rc.getHeight();
            float val = fromPos (dragRow, p);
            if (std::abs (p - toPos (dragRow, 1.0f)) < 0.015f) val = 1.0f;      // snap to "unchanged"
            v[(size_t) col * 3 + (size_t) dragRow] = val;
            changed();
        }
        ModeEditor& owner; Ctx& ctx; SoundMemory& mem; int os; int set = 0;
        std::vector<float> v; bool dirty = false; juce::OwnedArray<Btn> buttons; Btn *closeBtn = nullptr, *tabA = nullptr, *tabB = nullptr; int dragRow = -1;
    };

    ModeEditor::ModeEditor (Ctx& c, SoundMemory& m, int osc) : impl (new Impl (*this, c, m, osc)) { c.addListener (this); setVisible (false); setName ("modeEditor"); }
    ModeEditor::~ModeEditor() { impl->ctx.removeListener (this); }
    void ModeEditor::open (int set) { impl->set = set; impl->openSet (set); setVisible (true); toFront (false); resized(); repaint(); }
    void ModeEditor::paint (juce::Graphics& g) { impl->paintAll (g); }
    void ModeEditor::resized() { impl->layout(); }
    void ModeEditor::timerCallback() { if (impl->dirty) impl->commit(); stopTimer(); }
    void ModeEditor::paramChanged (int, float) { if (isVisible()) repaint(); }
    void ModeEditor::mouseDown (const juce::MouseEvent& e) { impl->dragRow = impl->hitRow (e.getPosition()); impl->draw (e); }
    void ModeEditor::mouseDrag (const juce::MouseEvent& e) { impl->draw (e); }
    void ModeEditor::mouseUp (const juce::MouseEvent&) { impl->dragRow = -1; impl->flush(); }
    void ModeEditor::mouseDoubleClick (const juce::MouseEvent& e)
    {
        int r = impl->hitRow (e.getPosition()); if (r < 0) return;
        int col = juce::jlimit (0, 15, (int) ((e.position.x - (float) impl->rows[r].getX()) / ((float) impl->rows[r].getWidth() / 16.0f)));
        impl->v[(size_t) col * 3 + (size_t) r] = 1.0f; impl->changed();
    }
}
