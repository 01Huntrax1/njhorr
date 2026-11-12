// INSPIRATOR page of the SEQ / ARP group: mode tabs, seeds, style / key / scale buttons, chord cards, a piano roll of the generated
// pattern (streamed by the DSP, see Backend::insPush), the knob row and the MIDI In switch.  Parameters 7000-7140 (7129-7140: locks, voicing, generators, import).
#pragma once
#include "ModUi.h"
#include <map>
#include <juce_audio_basics/juce_audio_basics.h>

namespace njo
{
    using namespace theme;

    namespace insp
    {
        inline const char* const kKeys[12] = { "C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B" };
        inline const int kScale[7][7] = { { 0, 2, 4, 5, 7, 9, 11 }, { 0, 2, 3, 5, 7, 8, 10 }, { 0, 2, 3, 5, 7, 9, 10 }, { 0, 2, 4, 5, 7, 9, 10 },
                                          { 0, 1, 3, 5, 7, 8, 10 }, { 0, 2, 4, 6, 7, 9, 11 }, { 0, 2, 3, 5, 7, 8, 11 } };
        inline const char* const kRoman[7] = { "I", "II", "III", "IV", "V", "VI", "VII" };
        inline const char* const kStyleCode[14] = { "pop", "rock", "hiphop", "trap", "lofi", "house", "techno", "jazz", "neosoul", "reggaeton", "dnb", "afro", "funk", "dub" };
        inline const char* const kScaleCode[7] = { "maj", "min", "dor", "mix", "phr", "lyd", "hmin" };
        inline bool minorish (int scale) { return scale == 1 || scale == 2 || scale == 4 || scale == 6; }

        // name and roman numeral of a chord from the DSP's chord info (root + 16 third + 256 fifth + 4096 seventh + 65536 level + 262144 degree + 2097152 shape)
        inline void describe (int ci, int scale, juce::String& name, juce::String& roman)
        {
            const int root = ci & 15, third = (ci >> 4) & 15, fifth = (ci >> 8) & 15, seventh = (ci >> 12) & 15, lvl = (ci >> 16) & 3, deg = (ci >> 18) & 7, shape = (ci >> 21) & 7;
            const bool minor = third == 3, dim = minor && fifth == 6, aug = ! minor && fifth == 8;
            name = kKeys[root % 12];
            if (shape == 4) name << "sus2";
            else if (shape == 5) name << "sus4";
            else
            {
                if (dim && lvl == 0) name << "dim";
                else
                {
                    if (minor) name << "m";
                    if (aug) name << "aug";
                    if (lvl >= 1 && shape != 6)
                    {
                        if (dim && seventh == 10) name << "7b5";
                        else if (seventh == 11) name << (lvl >= 2 ? "maj9" : "maj7");
                        else name << (lvl >= 2 ? "9" : "7");
                    }
                    if (shape == 6) name << "add9";
                }
            }
            if (shape == 7)
            {
                static const char* bm[7] = { "bVII", "bVI", "iv", "bIII", "V/vi", "V/ii", "V/V" };
                static const char* bn[7] = { "V7", "IV", "bII", "I", "V/V", "V/iv", "vii\xc2\xb0" "7" };
                roman = minorish (scale) ? bn[juce::jlimit (0, 6, deg)] : bm[juce::jlimit (0, 6, deg)];
                return;
            }
            roman = kRoman[juce::jlimit (0, 6, deg)];
            if (minor) roman = roman.toLowerCase();
            if (dim) roman << juce::String (juce::CharPointer_UTF8 ("\xc2\xb0"));
            if (lvl >= 1 && shape != 4 && shape != 5) roman << (lvl >= 2 ? "9" : "7");
        }

        // the generated pattern as a standard MIDI file (96 ticks per quarter note, one loop long) in the temp folder; empty when there is no pattern yet
        inline juce::File exportMidi (const Backend::InsPattern& p, const juce::String& title)
        {
            if (p.count <= 0) return {};
            const int loop = juce::jmax (1, p.numBars * p.stepsBar * 24);
            juce::MidiMessageSequence seq;
            seq.addEvent (juce::MidiMessage::textMetaEvent (3, title), 0.0);
            seq.addEvent (juce::MidiMessage::tempoMetaEvent (500000), 0.0);
            seq.addEvent (juce::MidiMessage::timeSignatureMetaEvent (juce::jmax (1, p.stepsBar / 4), 4), 0.0);
            const int ch = p.mode == 4 ? 10 : 1;
            for (int n = 0; n < p.count; ++n)
            {
                const int t0 = juce::jlimit (0, loop - 1, p.grid[(size_t) n] + p.off[(size_t) n]);
                const int t1 = juce::jmax (t0 + 1, juce::jmin (loop, t0 + p.len[(size_t) n]));
                seq.addEvent (juce::MidiMessage::noteOn (ch, p.pitch[(size_t) n], (juce::uint8) juce::jlimit (1, 127, p.vel[(size_t) n])), (double) t0);
                seq.addEvent (juce::MidiMessage::noteOff (ch, p.pitch[(size_t) n]), (double) t1);
            }
            seq.addEvent (juce::MidiMessage::endOfTrack(), (double) loop);
            seq.updateMatchedPairs();
            juce::MidiFile mf; mf.setTicksPerQuarterNote (96); mf.addTrack (seq);
            auto dir = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("Njohrr");
            dir.createDirectory();
            auto f = dir.getChildFile (juce::File::createLegalFileName (title) + ".mid");
            f.deleteFile();
            if (auto os = f.createOutputStream()) { mf.writeTo (*os); return f; }
            return {};
        }

        // dragging from here (or from the piano roll) hands the MIDI file to the host: drop it on a piano roll or the playlist
        struct MidiDrag : juce::Component
        {
            std::function<void()> start; bool hover = false;
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (1.0f);
                paintButton (g, r, false, hover, false, 3.0f);
                g.setColour (ink); g.setFont (font (9.0f, true));
                g.drawText (juce::String (juce::CharPointer_UTF8 ("\xe2\xa0\xbf  DRAG MIDI")), r.toNearestInt(), juce::Justification::centred);
            }
            void mouseEnter (const juce::MouseEvent&) override { hover = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { hover = false; repaint(); }
            void mouseDrag (const juce::MouseEvent& e) override { if (e.getDistanceFromDragStart() > 6 && start) start(); }
            void setHelp() { setMouseCursor (juce::MouseCursor::DraggingHandCursor); }
        };

        struct SelGrid : juce::Component, Ctx::Listener
        {
            Ctx& ctx; int id, cols; std::vector<juce::String> opts; std::vector<int> vals; int hover = -1; float fs = 9.0f;
            SelGrid (Ctx& c, int pid, int ncols, std::vector<juce::String> o, std::vector<int> v = {}) : ctx (c), id (pid), cols (ncols), opts (std::move (o)), vals (std::move (v))
            {
                if (vals.empty()) for (int i = 0; i < (int) opts.size(); ++i) vals.push_back (i);
                ctx.addListener (this);
            }
            ~SelGrid() override { ctx.removeListener (this); }
            void paramChanged (int n, float) override { if (n == id) repaint(); }
            juce::Rectangle<int> cell (int i) const
            {
                const int n = (int) opts.size(), rows = (n + cols - 1) / cols;
                const int cw = getWidth() / cols, ch = getHeight() / rows;
                return { (i % cols) * cw, (i / cols) * ch, cw - 4, ch - 4 };
            }
            void paint (juce::Graphics& g) override
            {
                const int cur = juce::roundToInt (ctx.get (id));
                for (int i = 0; i < (int) opts.size(); ++i)
                {
                    auto r = cell (i);
                    const bool on = vals[(size_t) i] == cur;
                    paintButton (g, r.toFloat(), on, hover == i, false, 3.0f);
                    g.setColour (on ? juce::Colours::white : ink); g.setFont (font (fs, true));
                    g.drawText (opts[(size_t) i], r, juce::Justification::centred);
                }
            }
            int at (juce::Point<int> p) const { for (int i = 0; i < (int) opts.size(); ++i) if (cell (i).contains (p)) return i; return -1; }
            void mouseMove (const juce::MouseEvent& e) override { const int h = at (e.getPosition()); if (h != hover) { hover = h; repaint(); } }
            void mouseExit (const juce::MouseEvent&) override { hover = -1; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override
            {
                const int i = at (e.getPosition());
                if (i >= 0) { ctx.begin (id); ctx.set (id, (float) vals[(size_t) i]); ctx.end (id); }
            }
        };

        struct SeedBox : juce::Component, Ctx::Listener
        {
            Ctx& ctx; int id, maxV, digits; juce::String caption, none; juce::TextEditor ed; int dragStart = 0; float dragY = 0;
            SeedBox (Ctx& c, int pid, int mx, int dg, juce::String cap, juce::String noneText = {}) : ctx (c), id (pid), maxV (mx), digits (dg), caption (cap), none (noneText)
            {
                ctx.addListener (this);
                ed.setJustification (juce::Justification::centred); ed.setFont (font (16.0f, true)); ed.setInputRestrictions (4, "0123456789");
                ed.onReturnKey = [this] { commit(); }; ed.onEscapeKey = [this] { ed.setVisible (false); }; ed.onFocusLost = [this] { if (ed.isVisible()) commit(); };
                addChildComponent (ed);
            }
            ~SeedBox() override { ctx.removeListener (this); }
            void paramChanged (int n, float) override { if (n == id) repaint(); }
            void setV (int v) { v = juce::jlimit (0, maxV, v); ctx.begin (id); ctx.set (id, (float) v); ctx.end (id); }
            void commit() { setV (ed.getText().getIntValue()); ed.setVisible (false); }
            void resized() override { ed.setBounds (getLocalBounds().reduced (6, 10)); }
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (1.0f);
                paintButton (g, r, false, false, false, 4.0f);
                const int v = juce::roundToInt (ctx.get (id));
                g.setColour (ink); g.setFont (font (none.isNotEmpty() && v == 0 ? 11.0f : 17.0f, true));
                g.drawText (none.isNotEmpty() && v == 0 ? none : juce::String (v).paddedLeft ('0', digits), r.toNearestInt().withTrimmedBottom (14), juce::Justification::centred);
                g.setColour (dim); g.setFont (font (8.0f, true));
                g.drawText (caption, r.toNearestInt().withTrimmedTop (r.getHeight() * 0.62f), juce::Justification::centred);
            }
            void mouseDown (const juce::MouseEvent& e) override { dragStart = juce::roundToInt (ctx.get (id)); dragY = (float) e.y; ctx.begin (id); }
            void mouseDrag (const juce::MouseEvent& e) override { ctx.set (id, (float) juce::jlimit (0, maxV, dragStart + juce::roundToInt ((dragY - (float) e.y) / 3.0f * (maxV > 200 ? 3.0f : 1.0f)))); }
            void mouseUp (const juce::MouseEvent&) override { ctx.end (id); }
            void mouseDoubleClick (const juce::MouseEvent&) override { ed.setText (juce::String (juce::roundToInt (ctx.get (id))), false); ed.setVisible (true); ed.grabKeyboardFocus(); ed.selectAll(); }
        };

        struct Action : juce::Component
        {
            juce::String text, sub; bool accent = false, hover = false; std::function<void()> click;
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (1.0f);
                paintButton (g, r, accent, hover, false, 4.0f);
                g.setColour (accent ? juce::Colours::white : ink); g.setFont (font (11.0f, true));
                g.drawText (text, r.toNearestInt().withTrimmedBottom (sub.isEmpty() ? 0 : 12), juce::Justification::centred);
                if (sub.isNotEmpty()) { g.setColour (accent ? juce::Colours::white.withAlpha (0.8f) : dim); g.setFont (font (8.0f, true)); g.drawText (sub, r.toNearestInt().withTrimmedTop (r.getHeight() * 0.6f), juce::Justification::centred); }
            }
            void mouseEnter (const juce::MouseEvent&) override { hover = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { hover = false; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && click) click(); }
        };

        // lock toggles above the roll: one button per bar (bit b of parameter 7129)
        struct LockBars : juce::Component, Ctx::Listener
        {
            Ctx& ctx;
            explicit LockBars (Ctx& c) : ctx (c) { ctx.addListener (this); }
            ~LockBars() override { ctx.removeListener (this); }
            void paramChanged (int n, float) override { if (n == 7129) repaint(); }
            int count() const { return juce::jlimit (1, 8, ctx.be.ins.numBars); }
            juce::Rectangle<int> cell (int i) const { const int n = count(), w = getWidth() / n; return { i * w, 0, w - 6, getHeight() }; }
            void paint (juce::Graphics& g) override
            {
                const int mask = juce::roundToInt (ctx.get (7129));
                for (int i = 0; i < count(); ++i)
                {
                    const bool on = ((mask >> i) & 1) != 0;
                    auto r = cell (i);
                    paintButton (g, r.toFloat(), on, false, false, 3.0f);
                    g.setColour (on ? juce::Colours::white : dim); g.setFont (font (8.5f, true));
                    g.drawText (juce::String (on ? "BAR " : "lock bar ") + juce::String (i + 1) + (on ? " LOCKED" : ""), r, juce::Justification::centred);
                }
            }
            void mouseUp (const juce::MouseEvent& e) override
            {
                for (int i = 0; i < count(); ++i)
                    if (cell (i).contains (e.getPosition()))
                    {
                        const int mask = juce::roundToInt (ctx.get (7129)) ^ (1 << i);
                        ctx.begin (7129); ctx.set (7129, (float) mask); ctx.end (7129);
                    }
            }
        };

        // a dropped MIDI file as 96-ticks-per-quarter notes: pairs (grid * 128 + pitch, len * 128 + vel), sorted by time
        struct ImportedNotes { std::vector<int> grid, len, pitch, vel; int bars = 1; };
        inline bool readMidiFile (const juce::File& f, int barTicks, ImportedNotes& out)
        {
            juce::FileInputStream in (f);
            juce::MidiFile mf;
            if (! in.openedOk() || ! mf.readFrom (in)) return false;
            const int tpq = mf.getTimeFormat();
            if (tpq <= 0) return false;
            struct N { int g, l, p, v; };
            std::vector<N> v;
            for (int t = 0; t < mf.getNumTracks(); ++t)
            {
                juce::MidiMessageSequence seq (*mf.getTrack (t));
                seq.updateMatchedPairs();
                for (int i = 0; i < seq.getNumEvents(); ++i)
                {
                    auto* e = seq.getEventPointer (i);
                    if (! e->message.isNoteOn() || e->noteOffObject == nullptr) continue;
                    const int g = (int) std::lround (e->message.getTimeStamp() * 96.0 / tpq / 6.0) * 6;
                    const int l = juce::jmax (6, (int) std::lround ((e->noteOffObject->message.getTimeStamp() - e->message.getTimeStamp()) * 96.0 / tpq));
                    v.push_back ({ g, juce::jmin (l, 1000), e->message.getNoteNumber(), juce::jlimit (1, 127, (int) e->message.getVelocity()) });
                }
            }
            if (v.empty()) return false;
            std::stable_sort (v.begin(), v.end(), [] (const N& a, const N& b) { return a.g < b.g; });
            int lastOnset = 0;
            for (auto& n : v) lastOnset = juce::jmax (lastOnset, n.g);
            const int needBars = lastOnset / juce::jmax (1, barTicks) + 1;
            out.bars = needBars <= 1 ? 1 : needBars <= 2 ? 2 : needBars <= 4 ? 4 : 8;
            for (auto& n : v)
                if (n.g < out.bars * barTicks && (int) out.grid.size() < 512)
                { out.grid.push_back (n.g); out.len.push_back (n.l); out.pitch.push_back (n.p); out.vel.push_back (n.v); }
            return ! out.grid.empty();
        }

        inline void sendImport (Backend& be, const ImportedNotes& n)
        {
            const int total = (int) n.grid.size();
            for (int off = 0; off < total; off += 128)
            {
                const int cnt = juce::jmin (128, total - off);
                juce::Array<juce::var> d;
                for (int i = 0; i < 128; ++i)
                {
                    const bool ok = i < cnt; const int k = off + i;
                    d.add ((double) (ok ? n.grid[(size_t) k] * 128 + n.pitch[(size_t) k] : 0));
                    d.add ((double) (ok ? n.len[(size_t) k] * 128 + n.vel[(size_t) k] : 0));
                }
                auto* o = new juce::DynamicObject();
                o->setProperty ("offset", off); o->setProperty ("count", cnt); o->setProperty ("total", total); o->setProperty ("bars", n.bars);
                o->setProperty ("data", juce::var (d));
                be.sendEvent ("insImport", juce::var (o));
            }
        }

        struct ChordCards : juce::Component
        {
            Ctx& ctx; int hover = -1;
            explicit ChordCards (Ctx& c) : ctx (c) {}
            int count() const { return juce::jlimit (1, 8, ctx.be.ins.numBars); }
            juce::Rectangle<int> card (int i) const { const int n = count(), w = getWidth() / n; return { i * w, 0, w - 6, getHeight() }; }
            void paint (juce::Graphics& g) override
            {
                const int scale = juce::roundToInt (ctx.get (7004));
                for (int i = 0; i < count(); ++i)
                {
                    auto r = card (i); juce::String nm, rn;
                    describe (ctx.be.ins.cInfo[i], scale, nm, rn);
                    const int ov = juce::roundToInt (ctx.get (7012 + i));
                    paintButton (g, r.toFloat(), false, hover == i, false, 4.0f);
                    g.setColour (dim); g.setFont (font (8.0f, true));
                    g.drawText (juce::String (i + 1), r.withTrimmedLeft (8).withTrimmedTop (4).removeFromTop (10), juce::Justification::centredLeft);
                    g.setColour ((ov % 64) != 0 ? orange : ink); g.setFont (font (17.0f, true));
                    g.drawText (nm, r.withTrimmedBottom (14), juce::Justification::centred);
                    g.setColour (dim); g.setFont (font (9.0f));
                    g.drawText (rn + (((ctx.be.ins.pushMask >> i) & 1) != 0 ? juce::String (juce::CharPointer_UTF8 ("  \xe2\x80\xba")) : juce::String()), r.withTrimmedTop (r.getHeight() - 18), juce::Justification::centred);
                }
            }
            void mouseMove (const juce::MouseEvent& e) override { int h = -1; for (int i = 0; i < count(); ++i) if (card (i).contains (e.getPosition())) h = i; if (h != hover) { hover = h; repaint(); } }
            void mouseExit (const juce::MouseEvent&) override { hover = -1; repaint(); }
            void setOv (int i, int v) { ctx.begin (7012 + i); ctx.set (7012 + i, (float) juce::jlimit (0, 255, v)); ctx.end (7012 + i); }
            void mouseUp (const juce::MouseEvent& e) override
            {
                int i = -1; for (int k = 0; k < count(); ++k) if (card (k).contains (e.getPosition())) i = k;
                if (i < 0) return;
                const int old = juce::roundToInt (ctx.get (7012 + i)), pushBits = old / 64 * 64;
                const int key = juce::roundToInt (ctx.get (7003)), scale = juce::roundToInt (ctx.get (7004));
                juce::PopupMenu m;
                m.addItem (1, "Automatic", true, old % 64 == 0);
                static const char* shp[7] = { "follows Complexity", "Triad", "Seventh", "Ninth", "Sus2", "Sus4", "Add9" };
                for (int d = 0; d < 7; ++d)
                {
                    juce::PopupMenu sub;
                    for (int s = 0; s < 7; ++s) sub.addItem (100 + d * 8 + s, shp[s], true, old % 64 == 1 + d + 8 * s);
                    const int rootSemi = (key + kScale[juce::jlimit (0, 6, scale)][d]) % 12;
                    m.addSubMenu (juce::String (kRoman[d]) + "  (" + kKeys[(rootSemi + 12) % 12] + ")", sub);
                }
                juce::PopupMenu bor;
                static const char* bm[7] = { "bVII", "bVI", "iv", "bIII", "V/vi", "V/ii", "V/V" };
                static const char* bn[7] = { "V7", "IV", "bII", "I", "V/V", "V/iv", "vii dim7" };
                for (int b = 0; b < 7; ++b) bor.addItem (300 + b, minorish (scale) ? bn[b] : bm[b], true, old % 64 == 1 + b + 56);
                m.addSubMenu ("Borrowed chord", bor);
                juce::PopupMenu push;
                push.addItem (400, "Automatic", true, pushBits == 0); push.addItem (401, "Always early", true, pushBits == 64); push.addItem (402, "Never early", true, pushBits == 128);
                m.addSubMenu ("Push (arrive an eighth early)", push);
                juce::Component::SafePointer<ChordCards> sp (this);
                m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (this), [sp, i, old, pushBits] (int r)
                {
                    if (sp == nullptr || r <= 0) return;
                    if (r == 1) sp->setOv (i, pushBits);
                    else if (r >= 400) sp->setOv (i, (old % 64) + 64 * (r - 400));
                    else if (r >= 300) sp->setOv (i, pushBits + 1 + (r - 300) + 56);
                    else if (r >= 100) { const int d = (r - 100) / 8, s = (r - 100) % 8; sp->setOv (i, pushBits + 1 + d + 8 * s); }
                });
            }
        };

        struct Roll : juce::Component
        {
            Ctx& ctx; std::function<void()> start;
            explicit Roll (Ctx& c) : ctx (c) { setMouseCursor (juce::MouseCursor::DraggingHandCursor); }
            void mouseDrag (const juce::MouseEvent& e) override { if (e.getDistanceFromDragStart() > 6 && start) start(); }
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat();
                g.setColour (juce::Colour (0xff0d0e10)); g.fillRoundedRectangle (r, 4.0f);
                const auto& p = ctx.be.ins;
                int lo = 127, hi = 0;
                for (int n = 0; n < p.count; ++n) { lo = juce::jmin (lo, p.pitch[(size_t) n]); hi = juce::jmax (hi, p.pitch[(size_t) n]); }
                if (p.count == 0) { lo = 48; hi = 72; }
                lo = juce::jmax (0, lo - 2); hi = juce::jmin (127, juce::jmax (hi + 2, lo + 11));
                const int rows = hi - lo + 1; const float rh = r.getHeight() / (float) rows;
                for (int k = lo; k <= hi; ++k)
                {
                    const int pc = k % 12; const bool black = pc == 1 || pc == 3 || pc == 6 || pc == 8 || pc == 10;
                    g.setColour (black ? juce::Colour (0x22000000) : juce::Colour (0x0cffffff));
                    g.fillRect (r.getX(), r.getBottom() - (float) (k - lo + 1) * rh, r.getWidth(), rh);
                }
                const int steps = juce::jmax (1, p.numBars * p.stepsBar); const float sw = r.getWidth() / (float) steps;
                for (int s = 0; s <= steps; ++s)
                {
                    const bool bar = s % juce::jmax (1, p.stepsBar) == 0, beat = s % juce::jmax (1, p.beatSteps) == 0;
                    g.setColour (bar ? juce::Colour (0x66ffffff) : beat ? juce::Colour (0x26ffffff) : juce::Colour (0x10ffffff));
                    g.fillRect (r.getX() + (float) s * sw - (bar ? 0.5f : 0.0f), r.getY(), bar ? 1.4f : 0.8f, r.getHeight());
                }
                const float loopTicks = (float) (steps * 24);
                for (int n = 0; n < p.count; ++n)
                {
                    const float x = r.getX() + (float) p.grid[(size_t) n] / loopTicks * r.getWidth();
                    const float w = juce::jmax (3.0f, juce::jmin ((float) p.len[(size_t) n], loopTicks - (float) p.grid[(size_t) n]) / loopTicks * r.getWidth() - 1.0f);
                    const float y = r.getBottom() - (float) (p.pitch[(size_t) n] - lo + 1) * rh;
                    g.setColour (red.interpolatedWith (orange, (float) p.vel[(size_t) n] / 127.0f).withAlpha (0.45f + 0.55f * (float) p.vel[(size_t) n] / 127.0f));
                    g.fillRoundedRectangle (x, y + 1.0f, w, juce::jmax (2.0f, rh - 2.0f), 1.5f);
                }
                if (ctx.be.insPlayStep >= 0)
                {
                    g.setColour (juce::Colours::white.withAlpha (0.85f));
                    g.fillRect (r.getX() + (float) (ctx.be.insPlayStep % steps) * sw, r.getY(), 1.6f, r.getHeight());
                }
                else
                {
                    g.setColour (dim); g.setFont (font (8.5f));
                    g.drawText ("Press play in your DAW - or hold a note to audition. Drag the pattern into a piano roll", getLocalBounds().removeFromBottom (14).withTrimmedRight (8), juce::Justification::centredRight);
                }
            }
        };
    }

    struct InspPanel : juce::Component, Ctx::Listener, juce::Timer, juce::FileDragAndDropTarget
    {
        Ctx& ctx; juce::OwnedArray<ParamWidget> w; std::map<int, ParamWidget*> byId;
        insp::SelGrid modeG, styleG, keyG, scaleG, barsG, rateG, inG, onG, genG;
        insp::LockBars lockBars; insp::Action extraB, importB; juce::String importInfo; bool extras = false, fileHover = false;
        std::vector<int> extraIds;
        insp::SeedBox song, part, vari;
        insp::Action lockB, genB, copyB, pasteB; insp::MidiDrag dragB; bool dragging = false;
        insp::ChordCards cards; insp::Roll roll; juce::TextEditor code;
        unsigned lastVer = 0; int lastStep = -2;

        static std::vector<juce::String> names (std::initializer_list<const char*> l) { std::vector<juce::String> v; for (auto* s : l) v.push_back (s); return v; }

        explicit InspPanel (Ctx& c)
            : ctx (c),
              modeG (c, 7001, 5, names ({ "CHORDS", "LEAD", "BASS", "ARP", "DRUMS" })),
              styleG (c, 7002, 4, names ({ "Pop", "Rock", "Hip-Hop", "Trap", "Lo-Fi", "House", "Techno", "Jazz", "Neo-Soul", "Reggaeton", "D&B", "Afrobeats", "Funk", "Dub" })),
              genG (c, 7139, 3, names ({ "Classic", "Euclid", "Markov", "Cellular", "L-System", "Import" })),
              lockBars (c),
              keyG (c, 7003, 6, names ({ "C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B" })),
              scaleG (c, 7004, 4, names ({ "Major", "Minor", "Dorian", "Mixoly.", "Phrygi.", "Lydian", "Harm." })),
              barsG (c, 7008, 4, names ({ "1", "2", "4", "8" })),
              rateG (c, 7127, 3, names ({ "1/2", "1", "2" })),
              inG (c, 7010, 1, names ({ "Transpose", "Hold", "Off" })),
              onG (c, 7000, 2, names ({ "OFF", "ON" })),
              song (c, 7005, 9999, 4, "SONG"), part (c, 7006, 9999, 4, "PART"), vari (c, 7007, 99, 2, "VARIATION", "NONE"),
              cards (c), roll (c)
        {
            ctx.addListener (this);
            modeG.fs = 11.0f; onG.fs = 9.0f; inG.fs = 9.0f; genG.fs = 9.0f; styleG.fs = 8.5f;
            for (auto* x : { (juce::Component*) &modeG, (juce::Component*) &styleG, (juce::Component*) &keyG, (juce::Component*) &scaleG, (juce::Component*) &barsG, (juce::Component*) &rateG,
                             (juce::Component*) &inG, (juce::Component*) &onG, (juce::Component*) &song, (juce::Component*) &part, (juce::Component*) &vari,
                             (juce::Component*) &lockB, (juce::Component*) &genB, (juce::Component*) &genG, (juce::Component*) &lockBars, (juce::Component*) &extraB, (juce::Component*) &importB, (juce::Component*) &copyB, (juce::Component*) &pasteB, (juce::Component*) &dragB, (juce::Component*) &cards, (juce::Component*) &roll, (juce::Component*) &code })
                addAndMakeVisible (x);
            lockB.click = [this]
            {
                const int cur = juce::roundToInt (ctx.get (7011));
                const int nv = (cur % 2) != 0 ? 0 : 1 + 2 * juce::roundToInt (ctx.get (7002));
                ctx.begin (7011); ctx.set (7011, (float) nv); ctx.end (7011);
            };
            extraB.text = "EXTRAS";
            extraB.click = [this] { extras = ! extras; extraB.accent = extras; refresh(); };
            importB.text = "IMPORT MIDI"; importB.sub = "or drop a .mid file here";
            importB.click = [this]
            {
                auto fc = std::make_shared<juce::FileChooser> ("Import a MIDI file", juce::File(), "*.mid;*.midi");
                juce::Component::SafePointer<InspPanel> sp (this);
                fc->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles, [sp, fc] (const juce::FileChooser& r)
                { if (sp != nullptr && r.getResult().existsAsFile()) sp->importFile (r.getResult()); });
            };
            { auto st = ctx.be.getStored ("insImport"); if (st.isArray()) restoreImport (st); }
            dragB.setHelp();
            auto startDrag = [this]
            {
                if (dragging) return;
                static const char* md[5] = { "Chords", "Lead", "Bass", "Arp", "Drums" };
                auto f = insp::exportMidi (ctx.be.ins, juce::String ("Inspirator ") + md[mode()] + " " + makeCode());
                if (! f.existsAsFile()) return;
                dragging = true;
                juce::DragAndDropContainer::performExternalDragDropOfFiles ({ f.getFullPathName() }, false, this, [this] { dragging = false; });
            };
            dragB.start = startDrag; roll.start = startDrag;
            genB.text = "GENERATE"; genB.sub = "NEW IDEA"; genB.accent = true;
            genB.click = [this] { const int v = juce::Random::getSystemRandom().nextInt (10000); ctx.begin (7006); ctx.set (7006, (float) v); ctx.end (7006); };
            copyB.text = "Copy"; pasteB.text = "Paste";
            copyB.click = [this] { juce::SystemClipboard::copyTextToClipboard (makeCode()); };
            pasteB.click = [this] { applyCode (juce::SystemClipboard::getTextFromClipboard()); };
            code.setFont (font (11.0f, true)); code.setColour (juce::TextEditor::backgroundColourId, juce::Colour (0xff0d0e10)); code.setColour (juce::TextEditor::textColourId, ink);
            code.setColour (juce::TextEditor::outlineColourId, line); code.setReadOnly (false);
            code.onReturnKey = [this] { applyCode (code.getText()); };
            static const int ids[] = { 7009, 7114, 7089 };
            for (int id : ids) { auto* x = w.add (makeWidget (c, id, true).release()); x->setLook (true); byId[id] = x; addChildComponent (x); }
            for (int id : { 7130, 7131, 7132, 7133, 7134, 7135, 7136, 7137, 7138, 7140 }) { auto* x = w.add (makeWidget (c, id, true).release()); x->setLook (true); byId[id] = x; addChildComponent (x); }
            for (int id = 7044; id <= 7087; ++id) { auto* x = w.add (makeWidget (c, id, true).release()); x->setLook (true); byId[id] = x; addChildComponent (x); }
            static const char* lanes[12] = { "Kick", "Snare", "Clap", "Hat", "Open", "Rim", "Tom", "Ride", "Pedal", "Low", "High", "Crash" };
            for (int l = 0; l < 12; ++l)
                for (int id : { 7102 + l, (l < 8 ? 7036 + l : 7090 + l), 7115 + l })
                {
                    auto* x = w.add (makeWidget (c, id, true).release()); x->setLook (true); byId[id] = x; addChildComponent (x);
                    x->setLabelOverride (id == 7102 + l ? "dens" : id == 7115 + l ? "note" : "rand");
                }
            juce::ignoreUnused (lanes);
            refresh();
            startTimerHz (20);
        }
        ~InspPanel() override { ctx.removeListener (this); }

        int mode() const { return juce::jlimit (0, 4, juce::roundToInt (ctx.get (7001))); }
        juce::String makeCode() const
        {
            return juce::String (insp::kKeys[juce::jlimit (0, 11, juce::roundToInt (ctx.get (7003)))]) + "-" + insp::kScaleCode[juce::jlimit (0, 6, juce::roundToInt (ctx.get (7004)))] + "-"
                   + insp::kStyleCode[juce::jlimit (0, 13, juce::roundToInt (ctx.get (7002)))] + "-" + juce::String (1 << juce::jlimit (0, 3, juce::roundToInt (ctx.get (7008)))) + "-" + juce::String (juce::roundToInt (ctx.get (7005)));
        }
        // ---- MIDI import: file drop / chooser -> quantised notes -> DSP (Generator = Import), stored with the project ----
        bool isInterestedInFileDrag (const juce::StringArray& f) override { for (auto& n : f) if (n.endsWithIgnoreCase (".mid") || n.endsWithIgnoreCase (".midi")) return true; return false; }
        void fileDragEnter (const juce::StringArray&, int, int) override { fileHover = true; repaint(); }
        void fileDragExit (const juce::StringArray&) override { fileHover = false; repaint(); }
        void filesDropped (const juce::StringArray& f, int, int) override { fileHover = false; for (auto& n : f) if (n.endsWithIgnoreCase (".mid") || n.endsWithIgnoreCase (".midi")) { importFile (juce::File (n)); break; } repaint(); }
        int barTicks() const { return juce::jmax (1, ctx.be.ins.stepsBar) * 24; }
        void applyImport (const insp::ImportedNotes& n, const juce::String& name)
        {
            insp::sendImport (ctx.be, n);
            juce::Array<juce::var> a; a.add (n.bars);
            for (size_t i = 0; i < n.grid.size(); ++i) { a.add (n.grid[i]); a.add (n.len[i]); a.add (n.pitch[i]); a.add (n.vel[i]); }
            ctx.be.setStored ("insImport", juce::var (a));
            importInfo = name + "  -  " + juce::String ((int) n.grid.size()) + " notes, " + juce::String (n.bars) + " bar" + (n.bars > 1 ? "s" : "");
            int bi = n.bars == 1 ? 0 : n.bars == 2 ? 1 : n.bars == 4 ? 2 : 3;
            setP (7008, bi); setP (7139, 5);
            repaint();
        }
        void importFile (const juce::File& f)
        {
            insp::ImportedNotes n;
            if (! insp::readMidiFile (f, barTicks(), n)) { importInfo = "could not read " + f.getFileName(); repaint(); return; }
            applyImport (n, f.getFileName());
        }
        void restoreImport (const juce::var& a)
        {
            if (a.size() < 5) return;
            insp::ImportedNotes n; n.bars = juce::jlimit (1, 8, (int) a[0]);
            for (int i = 1; i + 3 < a.size(); i += 4) { n.grid.push_back ((int) a[i]); n.len.push_back ((int) a[i + 1]); n.pitch.push_back ((int) a[i + 2]); n.vel.push_back ((int) a[i + 3]); }
            if (n.grid.empty()) return;
            insp::sendImport (ctx.be, n);
            importInfo = "imported pattern  -  " + juce::String ((int) n.grid.size()) + " notes, " + juce::String (n.bars) + " bars";
        }
        void setP (int id, int v) { ctx.begin (id); ctx.set (id, (float) v); ctx.end (id); }
        void applyCode (const juce::String& t)
        {
            auto p = juce::StringArray::fromTokens (t.trim(), "-", "");
            if (p.size() != 5) return;
            int k = -1, sc = -1, st = -1, b = -1;
            for (int i = 0; i < 12; ++i) if (p[0] == insp::kKeys[i]) k = i;
            for (int i = 0; i < 7; ++i) if (p[1] == insp::kScaleCode[i]) sc = i;
            for (int i = 0; i < 14; ++i) if (p[2] == insp::kStyleCode[i]) st = i;
            for (int i = 0; i < 4; ++i) if (p[3].getIntValue() == (1 << i)) b = i;
            if (k < 0 || sc < 0 || st < 0 || b < 0) return;
            setP (7003, k); setP (7004, sc); setP (7002, st); setP (7008, b); setP (7005, juce::jlimit (0, 9999, p[4].getIntValue()));
        }
        void refresh()
        {
            for (auto* x : w) x->setVisible (false);
            const int m = mode();
            std::vector<int> ids = { 7009, 7114, 7089 };
            if (m < 4) { for (int k : { 0, 1, 2, 3, 4, 5, 8, 6, 7 }) ids.push_back (7044 + 9 * m + k); }
            else for (int id : { 7080, 7081, 7082, 7086, 7087 }) ids.push_back (id);
            extraIds.clear();
            extraIds.push_back (7140);
            if (m == 0) for (int id : { 7130, 7131, 7132, 7133 }) extraIds.push_back (id);
            if (m == 1) for (int id : { 7135, 7136, 7138 }) extraIds.push_back (id);
            if (m == 2 || m == 4) extraIds.push_back (7134);
            extraIds.push_back (7137);
            if (extras) ids = extraIds;
            knobIds = ids;
            for (int id : ids) byId[id]->setVisible (true);
            genG.setVisible (extras); importB.setVisible (extras); lockBars.setVisible (m != 4);
            cards.setVisible (m != 4);
            if (m == 4) for (int l = 0; l < 12; ++l) for (int id : { 7102 + l, (l < 8 ? 7036 + l : 7090 + l), 7115 + l }) byId[id]->setVisible (true);
            if (m < 4)
            {
                static const char* lbl[9] = { "complexity", "density", "humanize", "octave", "range", "gate", "vel", "vel rand", "gate rand" };
                static const int order[9] = { 0, 1, 2, 3, 4, 5, 8, 6, 7 };
                for (int i = 0; i < 9; ++i) byId[7044 + 9 * m + order[i]]->setLabelOverride (juce::String (lbl[order[i] == 8 ? 8 : order[i]]));
                byId[7044 + 9 * m + 8]->setLabelOverride ("gate rand");
                byId[7044 + 9 * m + 6]->setLabelOverride ("velocity");
                byId[7044 + 9 * m + 7]->setLabelOverride ("vel rand");
            }
            byId[7009]->setLabelOverride ("swing"); byId[7114]->setLabelOverride ("push"); byId[7089]->setLabelOverride ("offset");
            code.setText (makeCode(), false);
            resized(); repaint();
        }
        std::vector<int> knobIds;
        void paramChanged (int n, float) override
        {
            if (n == 7001) refresh();
            else if (n == 7002 || n == 7003 || n == 7004 || n == 7005 || n == 7008) code.setText (makeCode(), false);
            if (n == 7011 || n == 7002) { resized(); lockB.repaint(); }
            if (n == 7139) repaint();
        }
        void timerCallback() override
        {
            if (! isShowing()) return;
            if (ctx.be.insVersion != lastVer) { lastVer = ctx.be.insVersion; cards.repaint(); roll.repaint(); }
            if (ctx.be.insPlayStep != lastStep) { lastStep = ctx.be.insPlayStep; roll.repaint(); }
        }
        void paint (juce::Graphics& g) override
        {
            g.setColour (red); g.setFont (impact (13.0f));
            g.drawText ("INSPIRATOR", 12, 2, 160, 18, juce::Justification::centredLeft);
            g.setColour (dim); g.setFont (font (8.0f, true));
            g.drawText ("MIDI GENERATOR  -  " + juce::String (ctx.be.ins.stepsBar / 4) + "/4", 112, 2, 200, 18, juce::Justification::centredLeft);
            for (auto& t : labels) { g.setColour (dim); g.setFont (font (8.0f, true)); g.drawText (t.text, t.r, juce::Justification::centredLeft); }
            g.setColour (dim); g.setFont (font (8.0f, true));
            g.drawText ("MIDI IN", midiLbl, juce::Justification::centredLeft);
            if (extras)
            {
                g.drawText ("GENERATOR", genG.getX(), genG.getY() - 11, 120, 10, juce::Justification::centredLeft);
                if (importInfo.isNotEmpty()) { g.setColour (ink); g.drawText (importInfo, importB.getRight() - 120, importB.getY(), 120, 12, juce::Justification::centredRight); }
            }
            if (fileHover) { g.setColour (red.withAlpha (0.18f)); g.fillRect (getLocalBounds()); g.setColour (red); g.drawRect (getLocalBounds(), 2); g.setFont (impact (22.0f)); g.drawText ("DROP MIDI FILE TO IMPORT", getLocalBounds(), juce::Justification::centred); }
            if (mode() == 4)
            {
                static const char* lanes[12] = { "KICK", "SNARE", "CLAP", "HAT", "O.HAT", "RIM", "M.TOM", "RIDE", "PEDAL", "L.TOM", "H.TOM", "CRASH" };
                for (int l = 0; l < 12; ++l) g.drawText (lanes[l], laneRects[l], juce::Justification::centred);
            }
        }
        struct Lbl { juce::String text; juce::Rectangle<int> r; };
        std::vector<Lbl> labels; juce::Rectangle<int> midiLbl, laneRects[12];
        void resized() override
        {
            auto b = getLocalBounds().reduced (10, 4);
            labels.clear();
            auto head = b.removeFromTop (20);
            onG.setBounds (head.removeFromRight (120).withTrimmedTop (0)); head.removeFromRight (8);
            dragB.setBounds (head.removeFromRight (110).reduced (0, 1)); head.removeFromRight (6);
            extraB.setBounds (head.removeFromRight (150).reduced (0, 1));
            b.removeFromTop (2);
            auto top = b.removeFromTop (60);
            modeG.setBounds (top.removeFromLeft (400)); top.removeFromLeft (6);
            song.setBounds (top.removeFromLeft (88).reduced (0, 2)); top.removeFromLeft (4);
            part.setBounds (top.removeFromLeft (88).reduced (0, 2)); top.removeFromLeft (6);
            lockB.text = (juce::roundToInt (ctx.get (7011)) % 2) != 0 ? "CHORDS" : "CHORDS"; lockB.sub = (juce::roundToInt (ctx.get (7011)) % 2) != 0 ? "LOCKED" : "FREE";
            lockB.accent = (juce::roundToInt (ctx.get (7011)) % 2) != 0;
            lockB.setBounds (top.removeFromLeft (92).reduced (0, 2)); top.removeFromLeft (4);
            vari.setBounds (top.removeFromLeft (92).reduced (0, 2)); top.removeFromLeft (6);
            genB.setBounds (top.reduced (0, 2));
            b.removeFromTop (6);
            auto bottom = b.removeFromBottom (112);
            if (extras) { auto gl = bottom.removeFromLeft (232); bottom.removeFromLeft (4); gl.removeFromTop (10); genG.setBounds (gl.removeFromTop (50)); importB.setBounds (gl.removeFromTop (46).reduced (0, 2)); }
            b.removeFromBottom (6);
            // left column
            auto left = b.removeFromLeft (258); b.removeFromLeft (8);
            auto sect = [&] (const juce::String& t, int h, juce::Component& c)
            {
                auto lr = left.removeFromTop (12); labels.push_back ({ t, lr });
                c.setBounds (left.removeFromTop (h)); left.removeFromTop (4);
            };
            sect ("STYLE", 112, styleG);
            sect ("KEY", 44, keyG);
            sect ("SCALE", 44, scaleG);
            {
                auto lr = left.removeFromTop (12); labels.push_back ({ "BARS", lr.removeFromLeft (130) }); labels.push_back ({ "CHORD RATE", lr });
                auto row = left.removeFromTop (28); left.removeFromTop (4);
                barsG.setBounds (row.removeFromLeft (130)); rateG.setBounds (row);
            }
            {
                auto lr = left.removeFromTop (12); labels.push_back ({ "SONG CODE", lr });
                auto row = left.removeFromTop (26);
                pasteB.setBounds (row.removeFromRight (56).reduced (1)); copyB.setBounds (row.removeFromRight (56).reduced (1)); code.setBounds (row.reduced (0, 1));
            }
            // right: chords (or lanes) and the roll
            const int m = mode();
            if (m != 4) { cards.setBounds (b.removeFromTop (74)); b.removeFromTop (6); }
            else
            {
                auto lanes = b.removeFromTop (172); b.removeFromTop (6);
                const int cw = lanes.getWidth() / 12;
                for (int l = 0; l < 12; ++l)
                {
                    auto col = lanes.removeFromLeft (cw);
                    laneRects[l] = col.removeFromTop (12);
                    int ids[3] = { 7102 + l, l < 8 ? 7036 + l : 7090 + l, 7115 + l };
                    for (int k = 0; k < 3; ++k) byId[ids[k]]->setBounds (col.removeFromTop (52).reduced (0, 0));
                }
            }
            if (m != 4) { lockBars.setBounds (b.removeFromTop (16)); b.removeFromTop (3); }
            roll.setBounds (b);
            // bottom: knobs + MIDI IN
            auto mi = bottom.removeFromRight (176); bottom.removeFromRight (8);
            midiLbl = mi.removeFromTop (12); inG.setBounds (mi);
            const int n = (int) knobIds.size();
            const int kw = juce::jmin (88, bottom.getWidth() / juce::jmax (1, n));
            int x = bottom.getX() + 4;
            for (int id : knobIds) { byId[id]->setBounds (x, bottom.getY() + 10, kw, bottom.getHeight() - 14); x += kw; }
            // reference: mode keys also transpose
        }
        void paintOverChildren (juce::Graphics&) override {}
    };
}
