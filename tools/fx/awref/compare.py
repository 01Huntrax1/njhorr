#!/usr/bin/env python3
"""Compares the Airwindows ports (FX types 19..26) with the ORIGINAL C++ code of the Airwindows plugins (MIT licence, Chris Johnson).
The originals are compiled with a tiny stub of the VST SDK (audioeffectx.h) and run on the plugin's own dry output.
  git clone --depth 1 https://github.com/airwindows/airwindows /tmp/airwindows
  python3 tools/fx/awref/compare.py --host <dsp_host built with -DDSP_FX> --awsrc /tmp/airwindows/plugins/LinuxVST/src
Expect relative RMS errors below about 1e-2. Differences that are NOT errors: ToTape flutter after the first random step (different random generator), and
Channel / DC: the plugin chain removes the DC that the Channel dielectric high-pass produces (compare with a high-passed reference)."""
import argparse, subprocess, os, sys, tempfile
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); ap.add_argument("--awsrc", required=True); A = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
HOST = A.host; TMP = tempfile.mkdtemp(prefix="awref"); RATE = 48000
for pl in ("PurestDrive", "Spiral2", "Drive", "Tube2", "Density2", "Console7Channel", "Channel9", "ToTape6", "MackEQ"):
    subprocess.run(["g++", "-O2", "-std=c++17", "-w", "-I" + HERE, "-I" + os.path.join(A.awsrc, pl), '-DHDR="%s.cpp"' % pl, '-DHDR2="%sProc.cpp"' % pl, "-DPLUG=" + pl, "-x", "c++", os.path.join(HERE, "harness.cpp"), "-o", os.path.join(TMP, "ref_" + pl)], check=True)
def base(slot): return 541 + 10 * slot
def fx(slot, ty, mode=0, mix=1.0, p=(0.5,) * 6):
    b = base(slot)
    return ["p %d %d" % (b, ty), "p %d 1" % (b + 1), "p %d %s" % (b + 2, mix), "p %d %d" % (b + 3, mode)] + ["p %d %s" % (b + 4 + i, v) for i, v in enumerate(p)]
def runf(cmds, inp, n):
    script=os.path.join(TMP,"s.txt"); out=os.path.join(TMP,"o.f32")
    open(script,"w").write("\n".join(list(cmds)+["inf "+inp,"run %.6f"%(n/RATE)])+"\n")
    subprocess.run([HOST,script,out],check=True)
    return np.fromfile(out,dtype=np.float32).reshape(-1,2)
N=RATE*2
t=np.arange(N)/RATE
rng=np.random.default_rng(1)
def mk(kind,amp):
    if kind=="saw": x=amp*(2*((t*110)%1.0)-1)
    elif kind=="noise": x=amp*rng.uniform(-1,1,N)
    else: x=amp*np.sin(2*np.pi*220*t)*(0.5+0.5*np.sin(2*np.pi*3*t))
    return x.astype(np.float32)
CASES = {
 19: ("PurestDrive", lambda p,m:[p[0]], 1),
 20: ("Spiral2", lambda p,m:[p[0],p[1],p[2],p[3],1.0], 4),
 21: ("Drive", lambda p,m:[p[0],p[1],p[2],1.0], 3),
 22: ("Tube2", lambda p,m:[p[0],p[1]], 2),
 23: ("Density2", lambda p,m:[p[0],p[1],p[2],1.0], 3),
 24: ("Console7Channel", lambda p,m:[p[0]], 1),
 25: ("Channel9", lambda p,m:[(m+0.5)/5,p[0],p[1]], 2),
 26: ("ToTape6", lambda p,m:[p[0],p[1],p[2],p[3],p[4],1.0], 5),
 27: ("MackEQ", lambda p,m:[p[0],p[1],p[2],p[3],1.0], 4),
}
PS = [(0.6,0.2,0.6,0.8,0.5),(0.4,0.0,0.5,1.0,0.5),(0.5,0.5,0.5,0.5,0.5)]
for kind,amp in (("noise",0.3),("mod",0.4)):
    x=mk(kind,amp); inp=os.path.join(TMP,"in.f32"); np.stack([x,x],1).tofile(inp)
    dry=runf([],inp,N); dp=os.path.join(TMP,"dry.f32"); dry.astype(np.float32).tofile(dp)
    for ty,(nm,mkp,n) in CASES.items():
        for pi,pp in enumerate(PS):
            for m in ((0,3) if ty==25 else (0,)):
                p=list(pp[:n])+[0.5]*(6-n)
                o=runf(fx(0,ty,m,1.0,tuple(p)),inp,N)
                rf=os.path.join(TMP,"r.f32")
                subprocess.run([os.path.join(TMP,"ref_"+nm),"48000",dp,rf]+["%g"%v for v in mkp(pp,m)],check=True)
                r=np.fromfile(rf,dtype=np.float32).reshape(-1,2)
                k=int(0.4*RATE); a=o[k:,0]; b=r[k:len(o),0]
                err=np.abs(a-b).max(); rms=np.sqrt(np.mean((a-b)**2))/max(np.sqrt(np.mean(b**2)),1e-9)
                print("%-16s %-5s p%d m%d |ref| %.3f maxerr %.2e rel-rms %.2e %s"%(nm,kind,pi,m,np.abs(b).max(),err,rms,"" if rms<1e-2 else " <<<<"))
