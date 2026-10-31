// Headless screenshot harness: njo_shot <outDir> [scale]  renders every page of the editor to PNG (software renderer, no display needed).
#include "../NjoEq.h"
#include "../NjoTer.h"
#include "../NjoWg.h"
#include "../NjoShaper.h"
#include "../NjoKick.h"
#include "../pages/Editors.h"
#include "../NjoPhys.h"
#include "../NjoEditor.h"
#include "../NjoMock.h"
#include "../NjoFreq.h"

static void save (juce::Component& c, const juce::File& f, float scale)
{
    auto img = c.createComponentSnapshot (c.getLocalBounds(), true, scale);
    juce::PNGImageFormat png;
    f.deleteFile();
    juce::FileOutputStream out (f);
    if (out.openedOk()) png.writeImageToStream (img, out);
}

template <class T> static T* findComp (juce::Component& c, const char* name)
{
    if (c.getName() == name && c.getParentComponent() && c.getParentComponent()->isVisible()) if (auto* t = dynamic_cast<T*> (&c)) return t;
    for (auto* ch : c.getChildren()) if (auto* r = findComp<T> (*ch, name)) return r;
    return nullptr;
}

int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    juce::File dir (argc > 1 ? argv[1] : "shots");
    dir.createDirectory();
    float scale = argc > 2 ? (float) std::atof (argv[2]) : 1.0f;
    njo::MockBackend be;
    njo::EditorContent ed (be);
    ed.setBounds (0, 0, njo::BASE_W, njo::BASE_H);
    auto pump = [] { juce::MessageManager::getInstance()->runDispatchLoopUntil (50); };
    pump();
    be.setParam (njo::fmId (0, 1), 60); be.setParam (njo::fmId (2, 2), 35); be.setParam (njo::pmId (1, 3), 100); be.setParam (njo::pdId (0, 2), 45); be.setParam (njo::pdId (3, 4), 8);
    be.setParam (njo::oscId (1, njo::oscKey ("ftype")), 30); be.setParam (njo::oscId (1, njo::oscKey ("wfpos")), 0.35f); be.setParam (njo::oscId (1, njo::oscKey ("fon")), 1);
    be.setParam (njo::oscId (1, njo::oscKey ("dtype")), 7); be.setParam (njo::oscId (1, njo::oscKey ("wdpos")), 0.3f);
    be.setParam (njo::oscId (0, njo::oscKey ("freq")), 0.55f);
    ed.context().modAssign (24, 12, 0.6f); ed.context().modAssign (25, 180, 0.4f);
    {
        auto& P = ed.context().freqShapes->points (0);
        P = { { 0, 0.95f, 0 }, { 0.12f, 0.7f, 0 }, { 0.25f, 0.5f, 0 }, { 0.5f, 0.3f, 0 }, { 1, 0.1f, 0 } };
    }
    const char* names[] = { "osc1", "osc2", "osc3", "osc4", "osc5", "osc6", "fm", "rmam", "global" };
    for (int i = 0; i < 9; ++i) { ed.setSynthPage (i); pump(); save (ed, dir.getChildFile (juce::String (names[i]) + ".png"), scale); }
    {
        auto& cx = ed.context();
        ed.setSynthPage (9); pump(); save (ed, dir.getChildFile ("flt.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("ftype")), 30.0f); cx.set (njo::oscId (0, njo::oscKey ("wfwarp")), 0.5f); cx.set (njo::oscId (0, njo::oscKey ("wfcont")), 0.4f); cx.set (njo::oscId (0, njo::oscKey ("wftilt")), -0.3f); ed.setSynthPage (9); pump(); save (ed, dir.getChildFile ("flt_wf.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("ftype")), 0.0f);
        ed.setSynthPage (15); pump(); save (ed, dir.getChildFile ("dist.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("rson")), 1.0f); cx.set (njo::oscId (0, njo::oscKey ("rsmod")), 6.0f); cx.set (njo::oscId (0, njo::oscKey ("rsdec")), 2.0f); cx.set (njo::oscId (0, njo::oscKey ("dpos")), 3.0f); ed.setSynthPage (21); pump(); save (ed, dir.getChildFile ("reso.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("dtype")), 7.0f); ed.setSynthPage (15); pump(); save (ed, dir.getChildFile ("dist_wd.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("dtype")), 0.0f);
        // Physical source
        cx.set (njo::oscId (0, njo::oscKey ("type")), 3.0f); cx.set (njo::phys::phyId (0, njo::phys::key ("phmodA")), 6.0f); cx.set (njo::phys::phyId (0, njo::phys::key ("phmodB")), 3.0f);
        ed.setSynthPage (0); pump(); save (ed, dir.getChildFile ("osc1_phys.png"), scale);
        // Juno DCO source
        cx.set (njo::oscId (0, njo::oscKey ("type")), 4.0f); cx.set (njo::phys::phyId (0, njo::phys::key ("jpulse")), 0.7f); cx.set (njo::phys::phyId (0, njo::phys::key ("jwidth")), 0.3f);
        cx.set (njo::phys::phyId (0, njo::phys::key ("jpwm")), 0.4f); cx.set (njo::phys::phyId (0, njo::phys::key ("jsub")), 0.5f); cx.set (njo::phys::phyId (0, njo::phys::key ("jsaw")), 0.8f); cx.set (njo::phys::phyId (0, njo::phys::key ("jstype")), 1.0f); cx.set (njo::phys::phyId (0, njo::phys::key ("jbtype")), 3.0f); cx.set (njo::phys::phyId (0, njo::phys::key ("jstype")), 1.0f); cx.set (njo::phys::phyId (0, njo::phys::key ("jbtype")), 3.0f);
        ed.setSynthPage (0); pump(); save (ed, dir.getChildFile ("osc1_juno.png"), scale);
        // Kick source
        cx.set (njo::oscId (0, njo::oscKey ("type")), 5.0f); cx.set (njo::kick::kickId (0, njo::kick::key ("kmode")), 1.0f); cx.set (njo::kick::kickId (0, njo::kick::key ("kdrive")), 0.5f);
        ed.setSynthPage (0); pump(); save (ed, dir.getChildFile ("osc1_kick.png"), scale);
        // Wave Terrain source
        cx.set (njo::oscId (0, njo::oscKey ("type")), 2.0f); cx.set (njo::oscId (0, njo::oscKey ("tterr")), 5.0f); cx.set (njo::ter::terId (0, njo::ter::key ("tterr2")), 10.0f); cx.set (njo::ter::terId (0, njo::ter::key ("tmorph")), 0.4f);
        cx.set (njo::oscId (0, njo::oscKey ("twarp")), 0.3f); cx.set (njo::ter::terId (0, njo::ter::key ("tratio")), 3.0f); cx.set (njo::ter::terId (0, njo::ter::key ("tcx")), 0.2f);
        ed.setSynthPage (0); pump(); save (ed, dir.getChildFile ("osc1_terrain.png"), scale);
        // Waveguide source: the drum model and the bowed string
        cx.set (njo::oscId (0, njo::oscKey ("type")), 6.0f); cx.set (njo::wg::wgId (0, njo::wg::key ("wmodel")), 4.0f); cx.set (njo::wg::wgId (0, njo::wg::key ("wsnare")), 0.4f); cx.set (njo::wg::wgId (0, njo::wg::key ("wglide")), 0.6f);
        ed.setSynthPage (0); pump(); save (ed, dir.getChildFile ("osc1_waveguide_drum.png"), scale);
        cx.set (njo::wg::wgId (0, njo::wg::key ("wmodel")), 1.0f);
        ed.setSynthPage (0); pump(); save (ed, dir.getChildFile ("osc1_waveguide_bowed.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("type")), 0.0f);
    }
    {
        // the editors (opened by hand: the buttons need a mouse)
        auto& cx = ed.context();
        cx.set (njo::oscId (0, njo::oscKey ("ftype")), 30.0f);
        ed.setSynthPage (9); pump();
        if (auto* t = findComp<njo::TableEditor> (ed, "tableEditor")) { t->open(); pump(); save (ed, dir.getChildFile ("edit_wf.png"), scale); t->setVisible (false); }
        cx.set (njo::oscId (0, njo::oscKey ("dtype")), 7.0f);
        ed.setSynthPage (15); pump();
        if (auto* t = findComp<njo::TableEditor> (ed, "tableEditor")) { t->open(); pump(); save (ed, dir.getChildFile ("edit_wd.png"), scale); t->setVisible (false); }
        cx.set (njo::oscId (0, njo::oscKey ("type")), 3.0f);
        ed.setSynthPage (0); pump();
        if (auto* m = findComp<njo::ModeEditor> (ed, "modeEditor")) { m->open (1); pump(); save (ed, dir.getChildFile ("edit_modes.png"), scale); m->setVisible (false); }
        cx.set (njo::oscId (0, njo::oscKey ("type")), 0.0f); cx.set (njo::oscId (0, njo::oscKey ("ftype")), 0.0f); cx.set (njo::oscId (0, njo::oscKey ("dtype")), 0.0f);
    }
    ed.setSynthPage (0); ed.setStripTab (1); pump (); save (ed, dir.getChildFile ("frq_strip.png"), scale); ed.setStripTab (0);
    {
        // FX page: empty rack (type grid), a chain of three effects, and one screenshot per effect type
        auto& cx = ed.context();
        ed.setGroup (njo::EditorContent::Effects); pump(); save (ed, dir.getChildFile ("fx_empty.png"), scale);
        const int base = njo::fxRacks()[0].id;
        auto setFx = [&] (int slot, int type)
        {
            const int b = base + slot * 10;
            cx.set (b, (float) type);
            if (type > 0)
            {
                auto& t = njo::fxTypes()[(size_t) type];
                cx.set (b + 1, 1.0f); cx.set (b + 2, t.mix); cx.set (b + 3, type == 9 ? 1.0f : 0.0f);
                for (size_t k = 0; k < t.params.size(); ++k) cx.set (b + 4 + (int) k, t.params[k].def);
            }
        };
        for (int t = 1; t <= 12; ++t)
        {
            setFx (0, t); if (t == 12) cx.set (base + 3, 8.0f); pump();
            save (ed, dir.getChildFile ("fx_type" + juce::String (t) + ".png"), scale);
        }
        setFx (0, 9); setFx (1, 3); setFx (2, 8); setFx (3, 11); pump();
        save (ed, dir.getChildFile ("fx.png"), scale);
        // tempo sync and the trance gate
        setFx (0, 7); cx.set (base + 3, 5.0f); cx.set (base + 4, 0.5f); cx.set (base + 5, 1.0f); cx.set (base + 6, 0.3f); cx.set (base + 7, 10.5f / 24.0f); cx.set (njo::fxSyncId (0), 4.0f); pump();
        save (ed, dir.getChildFile ("fx_gate.png"), scale);
        cx.set (base + 3, 7.0f); pump(); save (ed, dir.getChildFile ("fx_trem_rnd.png"), scale);
        setFx (0, 3); cx.set (base + 3, 4.0f); cx.set (njo::fxSyncId (0), 12.0f); pump(); save (ed, dir.getChildFile ("fx_delay_sync.png"), scale);
        setFx (0, 10); cx.set (base + 3, 1.0f); pump(); save (ed, dir.getChildFile ("fx_eq_tilt.png"), scale);
        cx.set (njo::fxSyncId (0), 0.0f);
        {   // parametric EQ with a handful of bands, incl. a harmonic bell and a comb
            using B = njo::eq::Band;
            njo::eq::Bands bs {};
            auto put = [&] (int i, int type, float hz, float db, float q, int harm = 0, int hset = 0, int ch = 0) { B b; b.used = true; b.on = true; b.type = type; b.hz = hz; b.db = db; b.q = q; b.harm = harm; b.hset = hset; b.ch = ch; bs[(size_t) i] = b; };
            put (0, 4, 80, 0, 0.7071f); put (1, 0, 110, 6, 3.0f, 6); put (2, 0, 420, -4, 1.4f); put (3, 0, 3200, 3, 0.9f, 0, 0, 3); put (4, 2, 10000, 4, 0.7f); put (5, 11, 220, 3, 1.0f);
            ed.soundMemory().set (njo::SoundMemory::EqBands, 0, "EQ", {}, njo::eq::encode (bs));
            setFx (0, 13); pump(); save (ed, dir.getChildFile ("fx_peq.png"), scale);
        }
        setFx (0, 14); cx.set (base + 3, 0.0f); cx.set (base + 4, 0.55f); pump(); save (ed, dir.getChildFile ("fx_sat_tube.png"), scale);
        cx.set (base + 3, 8.0f); pump(); save (ed, dir.getChildFile ("fx_sat_fold.png"), scale);
        ed.soundMemory().set (njo::SoundMemory::EqBands, 0, "WS", {}, njo::shaper::encode (njo::shaper::preset (5)));
        setFx (0, 15); pump(); save (ed, dir.getChildFile ("fx_shaper.png"), scale);
        ed.soundMemory().set (njo::SoundMemory::EqBands, 0, "WS", {}, njo::shaper::encode (njo::shaper::preset (3)));
        cx.set (base + 3, 1.0f); pump(); save (ed, dir.getChildFile ("fx_shaper_mirror.png"), scale);
        for (int sl = 0; sl < 4; ++sl) setFx (sl, 0);
        pump();
    }
    ed.setGroup (njo::EditorContent::Modulation); pump(); save (ed, dir.getChildFile ("mod.png"), scale);
    {   // more than 20 slots: Physical / Alpha Juno destinations, second page of the matrix
        auto& cx = ed.context();
        for (int k = 0; k < 24; ++k) cx.modAssign (1 + k % 10, 258 + 31 * (k % 6) + (k * 3) % 31, 0.1f + 0.03f * k);
        pump(); ed.setMatrixPage (0); pump(); save (ed, dir.getChildFile ("mod_p1.png"), scale);
        ed.setMatrixPage (1); pump(); save (ed, dir.getChildFile ("mod_p2.png"), scale); ed.setMatrixPage (0);
    }
    ed.setModTab (1); pump(); save (ed, dir.getChildFile ("frq_mod.png"), scale);
    return 0;
}
