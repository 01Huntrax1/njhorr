#!/usr/bin/env python3
"""Idempotent: the Bus 1 / Bus 2 effect racks are removed, marker FX-NOBUS.
Everything an oscillator sends to Bus 1 or Bus 2 now plays through the Main rack (old presets keep sounding); the bus racks and the Bus Level
parameters (880 / 881, ids kept so presets load) are no longer processed. The slot parameters of racks 1 / 2 stay in the file, unused."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'FX-NOBUS' in src:
    print('already applied'); sys.exit(0)
old = '''            // ----- FX racks: Bus 1 and Bus 2 feed the Main rack, which feeds the output -----
            float<2> bus1 = fxRunRack (1, float<2> (busInL.at (1), busInR.at (1))) * busLevel1;
            float<2> bus2 = fxRunRack (2, float<2> (busInL.at (2), busInR.at (2))) * busLevel2;
            float<2> rack = fxRunRack (0, float<2> (busInL.at (0) + bus1[0] + bus2[0], busInR.at (0) + bus1[1] + bus2[1]));
'''
new = '''            // ----- FX-NOBUS: one FX rack (Main); what an oscillator routes to Bus 1 / Bus 2 plays through it as well -----
            float<2> rack = fxRunRack (0, float<2> (busInL.at (0) + busInL.at (1) + busInL.at (2), busInR.at (0) + busInR.at (1) + busInR.at (2)));   // FX-NOBUS-SUM
'''
assert src.count(old) == 1
src = src.replace(old, new)
open(P, 'w').write(src)
print('ok')
