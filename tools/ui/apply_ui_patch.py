import re,sys
P="patch/index.js"
s=open(P).read()
def rep(old,new,cnt=1):
    global s
    assert s.count(old)==cnt,(old[:60],s.count(old))
    s=s.replace(old,new)

consts=open("tools/ui/js_consts.txt").read()
methods=open("tools/ui/js_methods.txt").read()

# 1. constants before SPECS, waves, specs
rep("const SPECS = (() => {","const LFO_STATE_KEY = \"njo.lfo\";\nconst LFO_MODES = [\"Free\", \"Trig\", \"Env\"];\n"+consts+"\nconst SPECS = (() => {")
rep('const MOD_WAVES = ["Sin", "Tri", "Sqr", "S&H", "Up", "Dn"];','const MOD_WAVES = ["Sin", "Tri", "Sqr", "S&H", "Up", "Dn", "Drawn"];')
rep('L.push([247 + 2 * i, "LFO " + (i + 1) + " Wave", 0, 5, 0, "", "btn", MOD_WAVES]);',
 'L.push([247 + 2 * i, "LFO " + (i + 1) + " Wave", 0, 6, 0, "", "btn", MOD_WAVES]);\n'
 '        const lb = 882 + 5 * i, ln = "LFO " + (i + 1);\n'
 '        L.push([lb,     ln + " Mode",   0, 2, 0, "", "btn", LFO_MODES, 1, "Mode"]);\n'
 '        L.push([lb + 1, ln + " Delay",  0, 5000, 0, "ms", "sld", null, 1, "Delay"]);\n'
 '        L.push([lb + 2, ln + " Rise",   0, 5000, 0, "ms", "sld", null, 1, "Rise"]);\n'
 '        L.push([lb + 3, ln + " Smooth", 0, 1, 0, "", "sld", null, 1, "Smooth"]);\n'
 '        L.push([lb + 4, ln + " Phase",  0, 1, 0, "", "sld", null, 1, "Phase"]);')

# 2. page html: replace lfo/env/mod pages with strip pieces
i=s.index("    // LFO page: 10 LFOs (wave selector + rate)")
j=s.index("    getHTML () {")
old=s[i:j]
mi=old.index("    // mod page")
modold=old[mi:]
mod_new=modold.replace("modPageHTML () {","matrixHTML () {").replace('return `<section class="card m-mtx"><h2>Mod Matrix</h2><div class="mtx2">${cols}</div></section>`;','return `<div class="mtx2">${cols}</div>`;')
assert mod_new!=modold
s=s[:i]+methods+mod_new+s[j:]

rep("        const lfoPage = this.lfoPageHTML();\n        const envPage = this.envPageHTML();\n        const modPage = this.modPageHTML();\n","        const strip = this.modStripHTML();\n")
rep('    <div class="page p-lfo">${lfoPage}</div>\n    <div class="page p-env">${envPage}</div>\n    <div class="page p-mod">${modPage}</div>\n','')
rep('    <div class="page p-fx">${fxPage}</div>\n  </div>\n','    <div class="page p-fx">${fxPage}</div>\n  </div>\n  ${strip}\n')

# 3. tabs: top groups + osc sub tabs
oldtabs=re.search(r'<div class="tabs">.*?</div>\n    <div class="vu">',s,re.S).group(0)
newtabs=('<div class="tabs"><button type="button" class="tab on" data-group="osc">OSC</button><button type="button" class="tab" data-group="flt">FILTER</button><button type="button" class="tab" data-group="fx">FX</button><button type="button" class="tab" data-group="mix">MIXER</button></div>\n    <div class="vu">')
s=s.replace(oldtabs,newtabs)
rep('  <div class="hz"></div>\n  ${MGR_HTML}','  <div class="hz"></div>\n  <div class="subtabs">'
 '<button type="button" class="stab on" data-page="sound">SYNTH</button><button type="button" class="stab" data-page="smp">SAMPLER 1</button><button type="button" class="stab" data-page="s2">SAMPLER 2</button>'
 '<button type="button" class="stab" data-page="wt1">WT 1</button><button type="button" class="stab" data-page="wt2">WT 2</button><button type="button" class="stab" data-page="wt3">WT 3</button></div>\n  ${MGR_HTML}')

rep('''    buildTabs () {
        this.querySelectorAll(".tab").forEach(t => {
            t.setAttribute("tabindex", "-1");
            t.addEventListener("click", () => { this.setPage(t.dataset.page); t.blur(); });
        });
        this.setPage("sound");
    }
''','''    buildTabs () {
        this._oscPage = "sound";
        this.querySelectorAll(".tab").forEach(t => {
            t.setAttribute("tabindex", "-1");
            t.addEventListener("click", () => { this.setGroup(t.dataset.group); t.blur(); });
        });
        this.querySelectorAll(".stab").forEach(t => {
            t.setAttribute("tabindex", "-1");
            t.addEventListener("click", () => { this._oscPage = t.dataset.page; this.setGroup("osc"); t.blur(); });
        });
        this.setGroup("osc");
    }

    setGroup (g) {
        this._group = g;
        this.setAttribute("data-group", g);
        this.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.dataset.group === g));
        this.setPage(g === "osc" ? this._oscPage : g);
    }
''')
rep('''        this.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.dataset.page === p));
        for (let e''','''        this.querySelectorAll(".stab").forEach(t => t.classList.toggle("on", t.dataset.page === p));
        for (let e''')
rep('  eisenpuls-view[data-page="lfo"] .p-lfo { display: grid; }\n  eisenpuls-view[data-page="env"] .p-env { display: grid; }\n  eisenpuls-view[data-page="mod"] .p-mod { display: grid; }\n','')
open(P,"w").write(s)
print("ok")
