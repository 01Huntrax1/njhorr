// Global page: Voice, Amp EG, Pitch EG and Output cards (12 column grid like the web UI: 2 / 3 / 2 / 5).
#include "../NjoPages.h"

namespace njo
{
    using namespace theme;

    struct GlobalPage::Impl
    {
        struct Card { const char* title; int col0, span, cols; std::vector<int> ids; juce::Rectangle<int> r; };
        explicit Impl (GlobalPage& p, Ctx& c) : owner (p), ctx (c)
        {
            cards = { { "VOICE", 0, 2, 1, { 2, 3, 63 }, {} },
                      { "AMP EG", 2, 3, 2, { 18, 19, 20, 21, 22 }, {} },
                      { "PITCH EG", 5, 2, 1, { 45, 46 }, {} },
                      { "OUTPUT", 7, 5, 3, { 29, 190, 36, 880, 881, 522 }, {} } };
            for (auto& card : cards)
                for (int id : card.ids)
                {
                    auto w = makeWidget (ctx, id, true);
                    w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                    owner.addAndMakeVisible (*w);
                    widgets.push_back (std::move (w));
                }
        }
        GlobalPage& owner; Ctx& ctx;
        std::vector<Card> cards;
        std::vector<std::unique_ptr<ParamWidget>> widgets;
    };

    GlobalPage::GlobalPage (Ctx& c) : impl (new Impl (*this, c)) {}
    GlobalPage::~GlobalPage() = default;

    void GlobalPage::resized()
    {
        auto b = getLocalBounds();
        const int gap = 8, total = b.getWidth() - gap * 11;
        float colW = total / 12.0f;
        size_t wi = 0;
        for (auto& card : impl->cards)
        {
            int x = (int) std::round (card.col0 * (colW + gap)), w = (int) std::round (card.span * colW + (card.span - 1) * gap);
            card.r = { x, 0, w, b.getHeight() };
            auto inner = card.r.reduced (10, 0).withTrimmedTop (34).withTrimmedBottom (10);
            int n = (int) card.ids.size(), cols = card.cols, rows = (n + cols - 1) / cols;
            int cw = inner.getWidth() / cols;
            int ch = juce::jmin (96, inner.getHeight() / juce::jmax (1, rows));
            for (int i = 0; i < n; ++i, ++wi)
            {
                auto& wd = *impl->widgets[wi];
                int cx = inner.getX() + (i % cols) * cw + cw / 2, top = inner.getY() + (i / cols) * ch;
                bool btn = wd.spec().kind == "btn";
                int ww = btn ? juce::jmin (cw - 8, 120) : juce::jmin (cw - 4, 84), hh = btn ? 46 : juce::jmin (ch - 4, 66);
                wd.setBounds (cx - ww / 2, top + 2, ww, hh);
            }
        }
    }

    void GlobalPage::paint (juce::Graphics& g)
    {
        for (auto& card : impl->cards)
        {
            paintCard (g, card.r.toFloat());
            g.setColour (red); g.fillRect (juce::Rectangle<float> ((float) card.r.getX() + 12, 13.0f, 7, 7));
            g.setFont (impact (11.0f)); g.setColour (ink);
            g.drawText (card.title, card.r.getX() + 24, 8, card.r.getWidth() - 36, 16, juce::Justification::centredLeft);
        }
    }
}
