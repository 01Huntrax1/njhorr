#!/usr/bin/env python3
"""Adds the Juno DCO source to patch/index.js (run once, after apply_phys_ui.py)."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "osc"))
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "jsaw" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
old_types = '["Wavetable", "Sampler", "Plaits", "Physical"]'
s = s.replace(old_types, json.dumps(L.SRC_TYPES))
s = re.sub(r'(\[\d+, "OSC \d Source", 0, )3(, 0)', r"\g<1>4\2", s)
rep("const PHY_K = %s;" % json.dumps({p[1]: p[0] for p in L.PHY if p[0] < 16}), "const PHY_K = %s;" % json.dumps({p[1]: p[0] for p in L.PHY}))
rows = []
for o in range(L.OSC_COUNT):
    for p in L.PHY:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        if j < 16: continue
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.phy_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), json.dumps(labels), json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j] + ",\n" + ",\n".join(rows) + s[j:]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    b = 6 + 9 * o
    for key, d in (("jwidth", 3), ("jpwm", 4), ("jsub", 5)):
        t[str(L.phy_id(o, [q[0] for q in L.PHY if q[1] == key][0]))] = [b + d, 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
rep('const type = Math.max(0, Math.min(3, Math.round(this.oscVal(o, "type"))));', 'const type = Math.max(0, Math.min(4, Math.round(this.oscVal(o, "type"))));')
rep('''                + `<div class="o-uh">Resonator B</div>`''', '''                + `<div class="o-uh">Resonator B</div>`''')
rep('''            ${sh("3", `<div class="o-uh">Exciter</div>`''', '''            ${sh("4", `<div class="o-uh">Oscillator</div>` + ["jsaw", "jpulse", "jsub", "jnoise", "jcurve", "jdrift"].map(p).join("") + `<div class="o-uh">Pulse width</div>` + ["jwidth", "jpwm", "jpwmr", "jrange"].map(p).join(""), "cgrid o-g3 o-phy")}
            ${sh("3", `<div class="o-uh">Exciter</div>`''')
rep('''        } else if (type === 3) {
            // mode spectrum''', '''        } else if (type === 4) {
            // two cycles of the DCO mix (saw + pulse + sub, not band-limited), noise as a level bar
            const V = key => { const id = phyId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const range = Math.round(V("jrange")), cyc = 2, cv = V("jcurve") * 4, wd = Math.max(0.05, Math.min(0.95, V("jwidth")));
            const arr = new Array(W);
            for (let x = 0; x < W; x++) {
                const t = x / W * cyc, ph = t - Math.floor(t), sp = (t / 2) - Math.floor(t / 2);
                let saw = 2 * ph - 1;
                if (cv > 0.01) saw = 2 * (Math.exp(cv * ph) - 1) / (Math.exp(cv) - 1) - 1;
                const pul = ph < wd ? 1 : -1, sub = sp < 0.5 ? 1 : -1;
                arr[x] = (saw * V("jsaw") + pul * V("jpulse") + sub * V("jsub")) * 0.55;
            }
            trace(arr, "#ff3b30", 2);
            ctx.fillStyle = "rgba(255,160,64,0.5)"; ctx.fillRect(W - 14, H - 6 - V("jnoise") * (H - 12), 8, V("jnoise") * (H - 12));
            if (info) info.textContent = "JUNO DCO / " + ["16'", "8'", "4'"][range] + " / WIDTH " + Math.round(wd * 100) + " %" + (V("jpwm") > 0 ? " / PWM " + V("jpwmr").toFixed(1) + " HZ" : "");
        } else if (type === 3) {
            // mode spectrum''')
rep('    if (s.unit === "s") return', '    if (s.unit === "Hz" && s.num >= PHY_BASE && s.num < PHY_BASE + PHY_STRIDE * OSC_N) return v.toFixed(2) + " Hz";\n    if (s.unit === "s") return')
open(P, "w").write(s)
print("ok", len(rows))
