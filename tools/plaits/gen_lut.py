#!/usr/bin/env python3
"""Extracts constant tables from the original Plaits / stmlib sources and writes them as Cmajor const arrays.
usage: gen_lut.py <name> [<name> ...]   (writes luts/<name>.part; names as in plaits/resources.cc or stmlib/dsp/units.cc)
The original sources are expected in $PLAITS_SRC (default: the eurorack checkout in the scratchpad)."""
import os, re, sys
SRC = os.environ.get("PLAITS_SRC", "/tmp/claude-0/-home-claude/c011a536-b544-58c8-a399-01d9f993fa60/scratchpad/eurorack")
HERE = os.path.dirname(os.path.abspath(__file__))
FILES = [SRC + "/plaits/resources.cc", SRC + "/stmlib/dsp/units.cc", SRC + "/stmlib/dsp/atan.cc"]

def find(name):
    for f in FILES:
        t = open(f).read()
        m = re.search(r"(?:const|extern const)\s+(?:PROGMEM\s+)?(float|int8_t|uint8_t|int16_t|uint16_t|int32_t|uint32_t)\s+" + re.escape(name) + r"\s*\[[^\]]*\]\s*(?:=|\{)\s*\{?(.*?)\};", t, re.S)
        if m:
            return m.group(1), m.group(2)
    raise SystemExit("table not found: " + name)

def emit(name):
    ty, body = find(name)
    body = re.sub(r"//[^\n]*", "", body)
    vals = [v.strip() for v in body.replace("\n", " ").split(",") if v.strip()]
    if ty == "float":
        out = [(v if v.endswith("f") else v + "f") for v in (x.rstrip("f") + "f" for x in vals)]
        ctype = "float"
    else:
        out = [str(int(v, 0)) for v in vals]
        ctype = "int"
    lines = []
    for i in range(0, len(out), 8):
        lines.append("        " + ", ".join(out[i:i + 8]))
    return "    const %s[%d] %s =\n    (\n%s\n    );\n" % (ctype, len(out), name, ",\n".join(lines))

if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "luts"), exist_ok=True)
    for n in sys.argv[1:]:
        open(os.path.join(HERE, "luts", n + ".part"), "w").write(emit(n))
        print("wrote", n)
