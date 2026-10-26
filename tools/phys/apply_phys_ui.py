#!/usr/bin/env python3
"""Adds the Physical source to patch/index.js (spec rows, page controls, mode display).  Run once on the index.js without it."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "osc")); sys.path.insert(0, HERE)
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "PHY_BASE" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)

# ratio tables (same as the DSP)
import importlib.util
src = open(os.path.join(HERE, "build_phys.py")).read()
ns = {}
exec(src[src.index("def circ"):src.index("rat = ")].replace("AEXP =", "AEXP ="), {"math": __import__("math")}, ns)
RAT, AEXP = ns["RAT"], ns["AEXP"]

# constants
keys = {p[1]: 64 + p[0] for p in L.PHY}   # k >= 64: physical block
consts = ("const PHY_BASE = %d, PHY_STRIDE = %d;\n" % (L.PHY_BASE, L.PHY_STRIDE)
          + "const PHY_K = %s;\n" % json.dumps({p[1]: p[0] for p in L.PHY})
          + "const phyId = (o, key) => PHY_BASE + PHY_STRIDE * o + PHY_K[key];\n"
          + "const PHY_MODELS = %s;\n" % json.dumps(L.PHY_MODELS)
          + "const PHY_RAT = %s;\nconst PHY_AEXP = %s;\n" % (json.dumps([[round(v, 4) for v in r] for r in RAT]), json.dumps(AEXP)))
rep("const OSC_SRC_TYPES = [\"Wavetable\", \"Sampler\", \"Plaits\"];", "const OSC_SRC_TYPES = %s;\n%s" % (json.dumps(L.SRC_TYPES), consts))
# source rows
s = re.sub(r'(\[\d+, "OSC \d Source", 0, )2(, 0, "", "btn", )\["Wavetable", "Sampler", "Plaits"\]', lambda m: m.group(1) + "3" + m.group(2) + json.dumps(L.SRC_TYPES), s)
rows = []
for o in range(L.OSC_COUNT):
    for p in L.PHY:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.phy_id(o, j), json.dumps("OSC %d Physical %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), json.dumps(labels), json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = [") ; j = s.index("\n];", i)
s = s[:j] + ",\n" + ",\n".join(rows) + s[j:]
# MOD targets: hit -> Position / Harm, material -> Warp 1 / Timbre, noise -> Warp 2 / Morph
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    b = 6 + 9 * o
    for key, d in (("phhitA", 3), ("phhitB", 3), ("phmatA", 4), ("phmatB", 4), ("phmix", 5)):
        t[str(L.phy_id(o, [q[0] for q in L.PHY if q[1] == key][0]))] = [b + d, 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
# type range
rep('const type = Math.max(0, Math.min(2, Math.round(this.oscVal(o, "type"))));', 'const type = Math.max(0, Math.min(3, Math.round(this.oscVal(o, "type"))));')
# page controls
rep('''            ${sh("2", ["pleng", "pharm", "ptimb", "pmorph"].map(c).join(""), "cgrid o-g3 o-pl")}
''', '''            ${sh("2", ["pleng", "pharm", "ptimb", "pmorph"].map(c).join(""), "cgrid o-g3 o-pl")}
            ${sh("3", `<div class="o-uh">Exciter</div>` + ["phmix", "phhard", "phntim"].map(p).join("") + `<div class="o-uh">Resonator A</div>` + ["phmodA", "phdecA", "phmatA", "phhitA", "phinhA"].map(p).join("")
                + `<div class="o-uh">Resonator B</div>` + ["phmodB", "phdecB", "phmatB", "phhitB", "phinhB", "phtunB"].map(p).join("") + `<div class="o-uh">Mix</div>` + ["phbal", "phser"].map(p).join(""), "cgrid o-g3 o-phy")}
''')
rep('''        const c = key => this.controlHTML(oscId(o, key), true);
        const sh = (list, inner, cls)''', '''        const c = key => this.controlHTML(oscId(o, key), true);
        const p = key => this.controlHTML(phyId(o, key), true);
        const sh = (list, inner, cls)''')
# value hook
rep("        if (n >= OSC_BASE && n < OSC_BASE + OSC_STRIDE * OSC_N) this.onOscValue(",
    "        if (n >= PHY_BASE && n < PHY_BASE + PHY_STRIDE * OSC_N && this._oscReady) this.drawOsc(Math.floor((n - PHY_BASE) / PHY_STRIDE));\n        if (n >= OSC_BASE && n < OSC_BASE + OSC_STRIDE * OSC_N) this.onOscValue(")
# display
rep('''        } else {
            const eng = Math.max(0, Math.min(PLAITS_ENGINES.length - 1, Math.round(this.oscVal(o, "pleng"))));''', '''        } else if (type === 3) {
            // mode spectrum of resonator A (red) and B (orange): position = frequency ratio on a log axis, height = amplitude
            const V = key => { const id = phyId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const bal = V("phbal"), tune = Math.pow(2, V("phtunB") / 12);
            ctx.fillStyle = "rgba(255,200,190,0.45)"; ctx.font = "bold " + Math.round(H * 0.07) + "px sans-serif";
            const xo = r => 14 + (W - 28) * Math.log2(Math.max(r, 0.5) / 0.5) / Math.log2(80 / 0.5);
            for (const f of [1, 2, 4, 8, 16, 32, 64]) { ctx.fillText(f + "x", xo(f) - 6, H - 3); ctx.fillRect(xo(f), 4, 1, H - 18); }
            for (const [res, col, mul, vol] of [["A", "#ff3b30", 1, 1 - bal], ["B", "#ffa040", tune, bal]]) {
                const md = Math.max(0, Math.min(8, Math.round(V("phmod" + res)))), hit = V("phhit" + res), inh = V("phinh" + res), mat = V("phmat" + res), dec = V("phdec" + res);
                let sum = 0; const am = [];
                for (let i = 0; i < 16; i++) { const a = Math.abs(Math.sin(Math.PI * hit * (i + 1))) / Math.pow(i + 1, PHY_AEXP[md]); am.push(a); sum += a * a; }
                const nr = 1 / Math.sqrt(Math.max(sum, 0.05));
                ctx.fillStyle = col; ctx.globalAlpha = 0.35 + 0.65 * Math.min(1, vol * 1.5);
                for (let i = 0; i < 16; i++) {
                    const r = PHY_RAT[md][i] * (1 + inh * 0.004 * i * i) * mul;
                    const t60 = Math.min(1, Math.pow(PHY_RAT[md][i], -1.6 * (1 - mat)));
                    const h = Math.min(1, am[i] * nr * 1.2) * (H - 24) * (0.35 + 0.65 * t60);
                    ctx.fillRect(xo(r * (res === "B" ? 1 : 1)) - 1.5 + (res === "B" ? 2 : 0), H - 16 - h, 3, h);
                }
                ctx.globalAlpha = 1;
            }
            if (info) info.textContent = "PHYSICAL / A " + PHY_MODELS[Math.round(V("phmodA"))].toUpperCase() + " + B " + PHY_MODELS[Math.round(V("phmodB"))].toUpperCase() + (V("phser") > 0.5 ? " / SERIAL" : "");
        } else {
            const eng = Math.max(0, Math.min(PLAITS_ENGINES.length - 1, Math.round(this.oscVal(o, "pleng"))));''')
# formats
rep('    if (s.unit === "ms") return', '    if (s.unit === "s") return v.toFixed(v < 10 ? 2 : 1) + " s";\n    if (s.unit === "ms") return')
open(P, "w").write(s)
print("ok")
