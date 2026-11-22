#!/usr/bin/env python3
"""Replaces the generated getEndpointHandleForName (a chain of ~9000 string compares, called once per parameter when the patch loads: ~40 million
compares) by a hash table lookup.  Idempotent.  python3 tools/perf/fast_handles.py <generated .cpp> ..."""
import re, sys
for path in sys.argv[1:]:
    s = open(path).read()
    m = re.search(r"^( *)static constexpr uint32_t getEndpointHandleForName \(std::string_view endpointName\)\n\1\{\n(.*?)\1    return 0;\n\1\}\n", s, re.S | re.M)
    if not m: print(path, "already patched or no match"); continue
    I = m.group(1)
    rows = re.findall(r'if \(endpointName == "([^"]+)"\)\s+return static_cast<uint32_t> \((EndpointHandles::\w+)\);\n', m.group(2))
    assert rows and len(rows) == m.group(2).count("if (endpointName"), (len(rows), m.group(2).count("if (endpointName"))
    body = I + "static uint32_t getEndpointHandleForName (std::string_view endpointName)\n" + I + "{\n" + I + "    static const std::unordered_map<std::string_view, uint32_t> table = {\n" \
         + "".join(I + '        { "%s", static_cast<uint32_t> (%s) },\n' % r for r in rows) \
         + I + "    };\n\n" + I + "    auto it = table.find (endpointName);\n" + I + "    return it != table.end() ? it->second : 0;\n" + I + "}\n"
    s = s[:m.start()] + body + s[m.end():]
    if "#include <unordered_map>" not in s: s = "#include <unordered_map>\n#include <string_view>\n" + s
    open(path, "w").write(s); print(path, "patched", len(rows), "endpoints")
