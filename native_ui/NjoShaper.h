// Waveshaper (FX type 15): the node model shared by the editor and the DSP (tools/fx/build_sat.py). Stored in the sound memory like the EQ bands:
// data[0] = node count / 16, then x, y, curve per node (all -1 .. 1). Segment shape between two nodes: t^(2^(3 curve)), sorted by x, held outside the end nodes.
#pragma once
#include <juce_core/juce_core.h>
#include <algorithm>
#include <cmath>
#include <vector>

namespace njo::shaper
{
    constexpr int MAXN = 16;
    struct Node { float x = 0.0f, y = 0.0f, c = 0.0f; };
    using Nodes = std::vector<Node>;

    inline std::vector<float> encode (Nodes n)
    {
        std::sort (n.begin(), n.end(), [] (const Node& a, const Node& b) { return a.x < b.x; });
        if ((int) n.size() > MAXN) n.resize (MAXN);
        std::vector<float> v (240, 0.0f);
        v[0] = (float) n.size() / 16.0f;
        for (size_t i = 0; i < n.size(); ++i)
        {
            v[1 + 3 * i] = juce::jlimit (-1.0f, 1.0f, n[i].x); v[2 + 3 * i] = juce::jlimit (-1.0f, 1.0f, n[i].y); v[3 + 3 * i] = juce::jlimit (-1.0f, 1.0f, n[i].c);
        }
        return v;
    }
    inline Nodes decode (const std::vector<float>& v)
    {
        Nodes n;
        if (v.size() < 4) return n;
        const int cnt = juce::jlimit (0, MAXN, juce::roundToInt (v[0] * 16.0f));
        for (int i = 0; i < cnt && (size_t) (3 + 3 * i) < v.size(); ++i)
            n.push_back ({ juce::jlimit (-1.0f, 1.0f, v[(size_t) (1 + 3 * i)]), juce::jlimit (-1.0f, 1.0f, v[(size_t) (2 + 3 * i)]), juce::jlimit (-1.0f, 1.0f, v[(size_t) (3 + 3 * i)]) });
        std::sort (n.begin(), n.end(), [] (const Node& a, const Node& b) { return a.x < b.x; });
        return n;
    }
    // exactly the DSP's table function (fewer than 2 nodes: identity)
    inline double eval (const Nodes& n, double x)
    {
        if (n.size() < 2) return x;
        if (x <= n.front().x) return n.front().y;
        for (size_t i = 0; i + 1 < n.size(); ++i)
            if (x <= n[i + 1].x)
            {
                const double w = n[i + 1].x - n[i].x, t = w > 1e-5 ? (x - n[i].x) / w : 1.0;
                return n[i].y + (n[i + 1].y - n[i].y) * std::pow (juce::jlimit (0.0, 1.0, t), std::pow (2.0, n[i].c * 3.0));
            }
        return n.back().y;
    }
    // the shaped function for a mode (0 curve, 1 odd mirror, 2 rectified)
    inline double shape (const Nodes& n, int mode, double u)
    {
        if (mode == 1) return u < 0 ? -eval (n, -u) : eval (n, u);
        if (mode == 2) return eval (n, std::abs (u));
        return eval (n, u);
    }
    inline Nodes preset (int i)
    {
        switch (i)
        {
            case 0: return { { -1, -1, 0 }, { 1, 1, 0 } };                                                                                // identity
            case 1: return { { -1, -0.8f, 0 }, { -0.5f, -0.75f, 0 }, { 0.0f, 0.0f, 0 }, { 0.5f, 0.75f, 0 }, { 1, 0.8f, 0 } };               // soft knee
            case 2: return { { -1, -0.7f, 0 }, { -0.35f, -0.7f, 0.0f }, { 0.35f, 0.7f, 0 }, { 1, 0.7f, 0 } };                              // hard clip
            case 3: return { { -1, 0.0f, 0 }, { -0.75f, -1.0f, 0 }, { -0.25f, 1.0f, 0 }, { 0.25f, -1.0f, 0 }, { 0.75f, 1.0f, 0 }, { 1, 0.0f, 0 } };   // fold
            case 4: return { { -1, -1, 0 }, { -0.5f, -1, 0 }, { -0.5f, -0.33f, 0 }, { 0.0f, -0.33f, 0 }, { 0.0f, 0.33f, 0 }, { 0.5f, 0.33f, 0 }, { 0.5f, 1, 0 }, { 1, 1, 0 } };   // staircase
            case 5: return { { -1, -0.3f, 0.5f }, { 0.0f, 0.0f, 0.0f }, { 1, 1.0f, -0.5f } };                                              // asymmetric
            default: return { { -1, 1, 0 }, { 0, -1, 0.6f }, { 1, 1, -0.6f } };                                                          // wavy
        }
    }
    inline const char* presetName (int i) { static const char* const n[] = { "Identity", "Soft knee", "Hard clip", "Fold", "Staircase", "Asymmetric", "Valley" }; return n[juce::jlimit (0, 6, i)]; }
}
