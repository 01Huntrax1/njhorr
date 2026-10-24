"""Benchmark scripts for tools/osc/dsp_host: writes idle / one / heavy / heavyfm scripts to /tmp/bench.
Run each with: dsp_host /tmp/bench/heavy.txt out.f32 (time it, or use valgrind --tool=callgrind for deterministic instruction counts);
compare the output files of two builds to check that an optimisation did not change the audio."""
import os; os.makedirs("/tmp/bench", exist_ok=True)
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L
K={p[1]:p[0] for p in L.PARAMS}
def P(o,k,v): return "p %d %s"%(L.pid(o,K[k]),v)
notes=[48,52,55,60,64,67,72,76]
def sc(name,pre,n=8,secs=4):
    lines=["wt 0 saw","wt 1 saw","wt 2 saw","wt 3 saw","wt 4 saw","wt 5 saw"]+pre+["run 0.05"]
    lines+=["on %d 100"%x for x in notes[:n]]+["run %g"%secs]
    open("/tmp/bench/%s.txt"%name,"w").write("\n".join(lines)+"\n")
sc("idle",[],0)
sc("one",[P(0,"level",0.5)])
heavy=[]
for o in range(6): heavy+=[P(o,"level",0.3),P(o,"uvox",7),P(o,"fon",1),P(o,"ftype",o*4),P(o,"fcut",3000),P(o,"dtype",1+o%6)]
sc("heavy",heavy)
fm=heavy[:]
for s in range(6):
    for d in range(6):
        if s!=d: fm+=["p %d 20"%L.fm_id(s,d) if hasattr(L,'fm_id') else "p %d 20"%(L.FM_BASE+6*s+d)]
sc("heavyfm",fm)
