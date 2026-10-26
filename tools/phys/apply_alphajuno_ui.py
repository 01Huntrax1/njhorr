#!/usr/bin/env python3
"""Updates patch/index.js for the Alpha Juno source with wave variants (run once, after apply_juno_ui.py)."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "osc"))
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "jstype" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
m = re.search(r"const PHY_K = (\{.*?\});", s)
s = s[:m.start(1)] + json.dumps({p[1]: p[0] for p in L.PHY}) + s[m.end(1):]
rows = []
for o in range(L.OSC_COUNT):
    for p in L.PHY:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        if j < 26: continue
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.phy_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), json.dumps(labels), json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j] + ",\n" + ",\n".join(rows) + s[j:]
a = s.index('            ${sh("4", `<div class="o-uh">Oscillator</div>`'); b = s.index("\n", a)
s = s[:a] + '''            ${sh("4", `<div class="o-uh">Waves</div>` + ["jstype", "jptype", "jbtype", "jsaw", "jpulse", "jsub"].map(p).join("") + `<div class="o-uh">Pulse width</div>` + ["jwidth", "jpwm", "jpwmr", "jpwms", "jrange"].map(p).join("")
                + `<div class="o-uh">Character</div>` + ["jnoise", "jcurve", "jdrift", "jvib"].map(p).join(""), "cgrid o-g3 o-phy o-juno")}''' + s[b:]
rep("  .o-phy > .o-uh { grid-column: 1 / -1; margin-top: 4px; } .page[data-src] .o-phy > .control.sel { grid-column: 1 / -1; }", "  .o-phy > .o-uh { grid-column: 1 / -1; margin-top: 4px; } .page[data-src] .o-phy:not(.o-juno) > .control.sel { grid-column: 1 / -1; }")
# display: waves by type
a = s.index("            const range = Math.round(V(\"jrange\")), cyc = 2")
b = s.index("            trace(arr, \"#ff3b30\", 2);", a)
s = s[:a] + '''            const range = Math.round(V("jrange")), cyc = 2, cv = V("jcurve") * 4, wd = Math.max(0.05, Math.min(0.95, V("jwidth")));
            const stp = Math.round(V("jstype")), ptp = Math.round(V("jptype")), btp = Math.round(V("jbtype"));
            const fr = x => x - Math.floor(x), ramp = q => 2 * q - 1;
            const arr = new Array(W);
            for (let x = 0; x < W; x++) {
                const t = x / W * cyc, ph = fr(t), q2 = fr(t / 2), q4 = fr(t / 4);
                let saw;
                if (stp === 1) saw = (ph < wd ? ramp(ph / wd) : -1) + (1 - wd);
                else if (stp === 2) saw = 0.75 * ramp(ph) + 0.25 * ramp(fr(ph * 2));
                else if (stp === 3) saw = 0.7 * ramp(ph) + 0.3 * ramp(fr(ph * 3));
                else { saw = cv > 0.01 ? 2 * (Math.exp(cv * ph) - 1) / (Math.exp(cv) - 1) - 1 : ramp(ph); if (stp === 4) saw = Math.tanh(1.7 * saw) * 1.12; }
                const pul = ph < (ptp === 0 ? wd : (ptp === 1 ? 0.25 : 0.125)) ? 1 : -1;
                const sq = (q, w) => q < w ? 1 : -1;
                const sub = [sq(q2, 0.5), sq(q2, 0.25), sq(q4, 0.5), sq(q4, 0.25), 0.5 * (sq(q2, 0.5) + sq(q4, 0.5)), q2 < 0.5 ? 4 * q2 - 1 : 3 - 4 * q2][btp];
                arr[x] = (saw * V("jsaw") + pul * V("jpulse") + sub * V("jsub")) * 0.55;
            }
''' + s[b:]
rep('info.textContent = "JUNO DCO / "', 'info.textContent = "ALPHA JUNO / " + ["SAW 1", "SAW 2", "SAW 3", "SAW 4", "SAW 5"][stp] + " + PULSE " + (ptp + 1) + " + SUB " + (btp + 1) + " / "') if 'info.textContent = "JUNO DCO / "' in s else None
open(P, "w").write(s)
print("ok", len(rows))
