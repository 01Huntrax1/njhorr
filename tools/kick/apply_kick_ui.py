#!/usr/bin/env python3
"""Adds the Kick source to patch/index.js (specs, mod destinations, fallback UI section, display).  Run once, after tools/phys/apply_juno_ui.py."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "osc"))
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "KICK_K" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
# Source selector: dropdown with the new entry
s = s.replace('["Wavetable", "Sampler", "Plaits", "Physical", "Alpha Juno"]', json.dumps(L.SRC_TYPES))
s = re.sub(r'(\[\d+, "OSC \d Source", 0, )4(, 0, "", )"btn"', r'\g<1>5\2"sel"', s)
rep('const phyId = (o, key) => PHY_BASE + PHY_STRIDE * o + PHY_K[key];',
    'const phyId = (o, key) => PHY_BASE + PHY_STRIDE * o + PHY_K[key];\nconst KICK_BASE = %d, KICK_STRIDE = %d;\nconst KICK_K = %s;\nconst kickId = (o, key) => KICK_BASE + KICK_STRIDE * o + KICK_K[key];'
    % (L.KICK_BASE, L.KICK_STRIDE, json.dumps({p[1]: p[0] for p in L.KICK})))
rows = []
for o in range(L.OSC_COUNT):
    for p in L.KICK:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.kick_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), json.dumps(labels), json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j] + ",\n" + ",\n".join(rows) + s[j:]
# mod destinations 444..539
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s)
d = json.loads(m.group(1)); assert len(d) == L.KICK_DST_BASE, len(d)
for o in range(L.OSC_COUNT):
    for p in L.KICK: d.append("OSC %d %s" % (o + 1, p[2]))
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s)
g = json.loads(m.group(1))
for o in range(L.OSC_COUNT): g.append([L.kickdst(o, 0), "OSC %d Kick" % (o + 1)])
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    for p in L.KICK:
        if p[8] == "sld": t[str(L.kick_id(o, p[0]))] = [L.kickdst(o, p[0]), 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
rep('const type = Math.max(0, Math.min(4, Math.round(this.oscVal(o, "type"))));', 'const type = Math.max(0, Math.min(5, Math.round(this.oscVal(o, "type"))));')
# fallback UI
rep('        const p = key => this.controlHTML(phyId(o, key), true);\n', '        const p = key => this.controlHTML(phyId(o, key), true);\n        const kk = key => this.controlHTML(kickId(o, key), true);\n')
rep('''            ${sh("3", `<div class="o-uh">Exciter</div>`''', '''            ${sh("5", `<div class="o-uh">Body</div>` + ["kmode", "ksweep", "kstime", "kscurve", "kdec", "ktone", "kchar", "ktune"].map(kk).join("") + `<div class="o-uh">Click / noise / sub</div>` + ["kclick", "kcltone", "kcldec", "knoise", "ksub", "kpunch"].map(kk).join("")
                + `<div class="o-uh">Drive</div>` + ["kdrive", "kdtype"].map(kk).join(""), "cgrid o-g3 o-phy o-kick")}
            ${sh("3", `<div class="o-uh">Exciter</div>`''')
rep('''        } else if (type === 4) {
            // two cycles of the DCO mix''', '''        } else if (type === 5) {
            // the body of the kick: pitch fall and decay over 250 ms at a 60 Hz note
            const V = key => { const id = kickId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const sw = V("ksweep"), tp = Math.max(0.0005, V("kstime") * 0.001 / (1 + 3 * V("kscurve"))), dec = V("kdec") * 0.001, arr = new Array(W);
            let ph = 0; const T = 0.25;
            for (let x = 0; x < W; x++) {
                const t = x / W * T, f = 60 * Math.pow(2, sw * Math.exp(-t / tp));
                ph += f * T / W;
                arr[x] = Math.sin(2 * Math.PI * ph) * Math.exp(-t * 4.6 / dec) * (1 + V("kpunch") * 3 * Math.exp(-t / 0.006)) * 0.6;
            }
            trace(arr, "#ff3b30", 2);
            if (info) info.textContent = "KICK / " + ["CLASSIC", "808", "PUNCH", "HARDSTYLE"][Math.round(V("kmode"))] + " / SWEEP " + sw.toFixed(1) + " OCT / DECAY " + Math.round(dec * 1000) + " MS";
        } else if (type === 4) {
            // two cycles of the DCO mix''')
open(P, "w").write(s)
print("ok", len(rows))
