// Factory plants of the Hanenbow mode (Arp Mode 13, tools/mod/build_hanenbow.py): where the plant stands, how many leaves it has, at which height, how they are turned and which note
// each plays, plus where the tadpoles are launched from.  A plant sets the parameters Jump, Bounce, Scale, Spawn X, Spread, Hits, Step, Leaf Size, Aim, Stem X and the 8 leaves
// (ids 6700 + k and 6720 + 5 * l + j); everything else (Frogs, Speed, Gravity, Rest ...) stays as it is.  No GUI code: tested by native_ui/test/plants_test.cpp.
#pragma once
#include <string>
#include <utility>
#include <vector>

namespace njo::plants
{
    struct Leaf { int on; int side; float y; float angle; int note; };   // side 0 = left of the stem, 1 = right; angle 0.5 = horizontal, above = up
    struct Plant
    {
        const char* name; const char* group;
        float stem, spawn, spread, aim, jump, bounce, size, hits, step; int scale;
        Leaf leaf[8];
    };

    inline const std::vector<Plant>& all()
    {
        static const std::vector<Plant> p = {
            // name, group,        stem, spawn, spread, aim, jump, bounce, size, hits, step, scale,   leaves { on, side, y, angle, note } x 8
            { "Classic",           "Plants",   64,  7, 5, 30, 120, 60, 35, 2,  2, 8, { { 1, 0, 0.69f, 0.725f, 0 }, { 1, 1, 0.69f, 0.725f, 2 }, { 1, 0, 0.50f, 0.73f, 4 }, { 1, 1, 0.50f, 0.73f, 5 }, { 1, 0, 0.33f, 0.84f, 7 }, { 1, 1, 0.33f, 0.84f, 9 }, { 0, 0, 0.20f, 0.85f, 3 }, { 0, 1, 0.20f, 0.85f, 6 } } },
            { "Tall tree",         "Plants",   62,  7, 5, 28, 135, 60, 30, 2,  2, 8, { { 1, 0, 0.72f, 0.72f, 0 }, { 1, 1, 0.72f, 0.72f, 2 }, { 1, 0, 0.55f, 0.74f, 3 }, { 1, 1, 0.55f, 0.74f, 5 }, { 1, 0, 0.38f, 0.78f, 6 }, { 1, 1, 0.38f, 0.78f, 8 }, { 1, 0, 0.21f, 0.84f, 9 }, { 1, 1, 0.21f, 0.84f, 11 } } },
            { "Young shoot",       "Plants",   60,  7, 3, 24, 105, 70, 40, 3,  1, 9, { { 1, 0, 0.62f, 0.70f, 0 }, { 1, 1, 0.62f, 0.70f, 3 }, { 1, 0, 0.40f, 0.80f, 5 }, { 1, 1, 0.40f, 0.80f, 7 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 } } },
            { "Wide fan",          "Plants",   55,  6, 6, 35, 125, 65, 40, 2,  1, 8, { { 1, 0, 0.76f, 0.54f, 0 }, { 1, 1, 0.76f, 0.54f, 2 }, { 1, 0, 0.62f, 0.56f, 4 }, { 1, 1, 0.62f, 0.56f, 5 }, { 1, 0, 0.48f, 0.58f, 7 }, { 1, 1, 0.48f, 0.58f, 9 }, { 1, 0, 0.34f, 0.60f, 11 }, { 1, 1, 0.34f, 0.60f, 12 } } },
            { "Willow",            "Plants",   64,  7, 5, 30, 125, 60, 33, 3,  2, 9, { { 1, 0, 0.30f, 0.30f, 9 }, { 1, 1, 0.30f, 0.30f, 7 }, { 1, 0, 0.45f, 0.32f, 6 }, { 1, 1, 0.45f, 0.32f, 4 }, { 1, 0, 0.60f, 0.34f, 3 }, { 1, 1, 0.60f, 0.34f, 2 }, { 1, 0, 0.75f, 0.36f, 1 }, { 1, 1, 0.75f, 0.36f, 0 } } },
            { "Staircase",         "Shapes",   30,  6, 4, 42, 125, 55, 36, 1,  1, 8, { { 1, 1, 0.76f, 0.60f, 0 }, { 1, 1, 0.62f, 0.60f, 2 }, { 1, 1, 0.48f, 0.60f, 4 }, { 1, 1, 0.34f, 0.60f, 5 }, { 1, 1, 0.20f, 0.60f, 7 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 }, { 0, 0, 0.5f, 0.7f, 0 } } },
            { "Zigzag",            "Shapes",   64,  7, 4, 30, 125, 60, 33, 2,  2, 10, { { 1, 0, 0.76f, 0.70f, 0 }, { 1, 1, 0.66f, 0.70f, 3 }, { 1, 0, 0.56f, 0.70f, 5 }, { 1, 1, 0.46f, 0.70f, 7 }, { 1, 0, 0.36f, 0.70f, 10 }, { 1, 1, 0.26f, 0.70f, 12 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 } } },
            { "Bell flower",       "Shapes",   64,  8, 3, 30, 115, 75, 42, 4,  3, 5, { { 1, 0, 0.58f, 0.86f, 0 }, { 1, 1, 0.58f, 0.86f, 4 }, { 1, 0, 0.36f, 0.90f, 7 }, { 1, 1, 0.36f, 0.90f, 11 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 } } },
            { "Two low leaves",    "Sparse",   64,  7, 3, 30, 105, 60, 38, 1,  2, 9, { { 1, 0, 0.66f, 0.66f, 0 }, { 1, 1, 0.66f, 0.66f, 4 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 } } },
            { "Lone leaf",         "Sparse",   64,  7, 2, 32, 110, 80, 45, 1,  0, 2, { { 1, 0, 0.60f, 0.62f, 0 }, { 0, 1, 0.5f, 0.7f, 0 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 } } },
            { "Trampolines",       "Shapes",   64,  7, 4, 28, 125, 105, 34, 2,  1, 8, { { 1, 0, 0.74f, 0.52f, 0 }, { 1, 1, 0.74f, 0.52f, 3 }, { 1, 0, 0.54f, 0.52f, 5 }, { 1, 1, 0.54f, 0.52f, 7 }, { 1, 0, 0.34f, 0.52f, 9 }, { 1, 1, 0.34f, 0.52f, 12 }, { 0, 0, 0.5f, 0.7f, 0 }, { 0, 1, 0.5f, 0.7f, 0 } } },
        };
        return p;
    }

    // the parameter values of a plant as (id, value) pairs
    inline std::vector<std::pair<int, float>> values (const Plant& p)
    {
        std::vector<std::pair<int, float>> v = { { 6703, p.jump }, { 6704, p.bounce }, { 6705, (float) p.scale }, { 6712, p.spawn }, { 6713, p.spread }, { 6714, p.hits }, { 6715, p.step }, { 6716, p.size }, { 6717, p.aim }, { 6718, p.stem } };
        for (int l = 0; l < 8; ++l)
        {
            const auto& e = p.leaf[l]; const int b = 6720 + 5 * l;
            v.push_back ({ b, (float) e.on }); v.push_back ({ b + 1, (float) e.side }); v.push_back ({ b + 2, e.y }); v.push_back ({ b + 3, e.angle }); v.push_back ({ b + 4, (float) e.note });
        }
        return v;
    }
}
