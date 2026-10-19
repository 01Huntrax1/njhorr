#!/usr/bin/env python3
"""Compares the Cmajor port of one engine with the original C++ (tools/plaits/ref/ref.cc).
usage: compare.py <engine> [--blocks N] [--tol T] [--cases "note,harm,timb,morph;..."] [--noise]
Builds the test patch (tools/plaits/build.py test), compiles it with cmaj + g++, renders the cases with both, prints max error per case.
--noise: for engines using the random generator; compares RMS and spectrum shape instead of samples."""
import argparse, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get("SP", "/tmp/claude-0/-home-claude/c011a536-b544-58c8-a399-01d9f993fa60/scratchpad")
CMAJ = "/home/claude/cmajor-lang/cmajor/build/tools/command/cmaj"
REF = os.environ.get("PLAITS_REF", SP + "/ref")

def build(tag):
    d = "/tmp/pl_build_" + tag
    subprocess.check_call([sys.executable, os.path.join(HERE, "build.py"), "test", d])
    r = subprocess.run([CMAJ, "generate", "--target=cpp", "--output=" + d + "/gen.h", d + "/PlaitsTest.cmajorpatch"], capture_output=True, text=True)
    if "error" in (r.stdout + r.stderr):
        print((r.stdout + r.stderr)[:3000]); sys.exit(2)
    subprocess.check_call(["g++", "-O1", "-std=c++17", "-w", '-DDSP_HEADER="%s/gen.h"' % d, os.path.join(HERE, "test", "host.cpp"), "-o", d + "/host"])
    return d + "/host"

def load(path, blocks):
    a = np.fromfile(path, dtype=np.float32)
    a = a[: blocks * 24].reshape(-1, 2, 12)
    return a[:, 0, :].ravel(), a[:, 1, :].ravel()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", type=int)
    ap.add_argument("--blocks", type=int, default=400)
    ap.add_argument("--tol", type=float, default=2e-3)
    ap.add_argument("--cases", default="60,0.5,0.5,0.5;48,0.1,0.2,0.9;72,0.9,0.8,0.1;36,0.3,0.0,0.5;84,0.0,1.0,1.0")
    ap.add_argument("--trig", type=int, default=1000000)
    ap.add_argument("--noise", action="store_true")
    ap.add_argument("--aux", action="store_true", help="also compare the aux output")
    ap.add_argument("--no-build", action="store_true")
    a = ap.parse_args()
    host = "/tmp/pl_build_%d/host" % a.engine if a.no_build else build(str(a.engine))
    if a.no_build is False: pass
    REFF = "/tmp/pl_ref_%d.f32" % a.engine
    CMF = "/tmp/pl_cm_%d.f32" % a.engine
    ok = True
    for c in a.cases.split(";"):
        note, h, t, m = [float(x) for x in c.split(",")]
        subprocess.check_call([REF, str(a.engine), str(note), str(h), str(t), str(m), str(a.blocks), REFF, str(a.trig)])
        subprocess.check_call([host, str(a.engine), str(note), str(h), str(t), str(m), str(a.blocks), CMF, str(a.trig)])
        ro, ra = load(REFF, a.blocks)
        co, ca = load(CMF, a.blocks)
        def stat(x, y):
            err = float(np.max(np.abs(x - y)))
            rms = float(np.sqrt(np.mean(x ** 2))) + 1e-12
            return err, rms, float(np.sqrt(np.mean(y ** 2)))
        if a.noise:
            def spec(x):
                s = np.abs(np.fft.rfft(x * np.hanning(len(x)))); b = np.array_split(s, 16)
                return np.array([np.mean(v) for v in b]) + 1e-9
            sr, sc = spec(ro), spec(co)
            dev = float(np.max(np.abs(20 * np.log10(sr / sc))))
            e, r1, r2 = stat(ro, co)
            good = abs(r1 - r2) / r1 < 0.15 and dev < 4.0
            print("%s note=%g h=%g t=%g m=%g  rms ref=%.4f cm=%.4f  spectrum dev=%.1f dB" % ("ok  " if good else "FAIL", note, h, t, m, r1, r2, dev))
        else:
            e, r1, r2 = stat(ro, co)
            good = e <= a.tol
            msg = "%s note=%g h=%g t=%g m=%g  max err=%.2e (rms ref=%.4f cm=%.4f)" % ("ok  " if good else "FAIL", note, h, t, m, e, r1, r2)
            if a.aux:
                e2, _, _ = stat(ra, ca); good2 = e2 <= a.tol; good = good and good2; msg += "  aux err=%.2e" % e2
            print(msg)
        ok = ok and good
    sys.exit(0 if ok else 1)
