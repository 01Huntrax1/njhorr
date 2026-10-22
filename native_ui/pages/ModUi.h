// Small helpers shared by ModEditors and MatrixPanel.
#pragma once
#include "../NjoPages.h"

namespace njo
{
    // compact dropdown: dark button with the current option and a red triangle, grouped popup menu
    class MiniSelect : public juce::Component
    {
    public:
        std::function<int()> getIndex;
        std::function<void (int)> setIndex;
        std::function<juce::String()> textOverride;
        juce::StringArray names; std::vector<std::pair<int, juce::String>> groups;
        int extraItem = -1; juce::String extraName;       // optional last menu item (id 1000), e.g. "Drawn"
        bool dimmed = false;

        void paint (juce::Graphics& g) override
        {
            auto r = getLocalBounds().toFloat().reduced (0, 0.5f);
            theme::paintButton (g, r, false, hover, false, 3.0f);
            int idx = getIndex ? getIndex() : 0;
            g.setColour (theme::ink.withAlpha (dimmed ? 0.45f : 1.0f)); g.setFont (theme::font (11.0f, true));
            auto t = textOverride ? textOverride() : (names.size() ? names[juce::jlimit (0, names.size() - 1, idx)] : juce::String());
            g.drawText (t, r.reduced (7, 0).toNearestInt(), juce::Justification::centredLeft, true);
            juce::Path p; auto a = juce::Rectangle<float> (r.getRight() - 15, r.getCentreY() - 3, 9, 6);
            p.addTriangle (a.getX(), a.getY(), a.getRight(), a.getY(), a.getCentreX(), a.getBottom());
            g.setColour (theme::red.withAlpha (dimmed ? 0.45f : 1.0f)); g.fillPath (p);
        }
        void mouseEnter (const juce::MouseEvent&) override { hover = true; repaint(); }
        void mouseExit (const juce::MouseEvent&) override { hover = false; repaint(); }
        void mouseDown (const juce::MouseEvent&) override
        {
            juce::PopupMenu m; size_t gi = 0; int cur = getIndex ? getIndex() : 0;
            for (int i = 0; i < names.size(); ++i)
            {
                while (gi < groups.size() && groups[gi].first == i) { if (groups[gi].second.isNotEmpty()) m.addSectionHeader (groups[gi].second); ++gi; }
                m.addItem (i + 1, names[i], true, cur == i);
            }
            if (extraItem >= 0) m.addItem (1000, extraName, true, cur == extraItem);
            juce::Component::SafePointer<MiniSelect> self (this);
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (this).withMinimumWidth (getWidth()).withMaximumNumColumns (3),
                             [self] (int r) { if (self != nullptr && r > 0 && self->setIndex) self->setIndex (r == 1000 ? self->extraItem : r - 1); if (self) self->repaint(); });
        }
    private:
        bool hover = false;
    };
}
