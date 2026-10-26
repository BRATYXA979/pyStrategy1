#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает game-standalone.html из tools/template.html + tools/map-data.js."""
import re, json

with open('tools/map-data.js', encoding='utf-8') as f:
    src = f.read()
m = re.search(r'const MAP_DATA = (\{.*\});\s*$', src, re.S)
assert m, "MAP_DATA not found"
data = json.loads(m.group(1))
compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

with open('tools/template.html', encoding='utf-8') as f:
    tpl = f.read()

assert '@MAPDATA@' in tpl, "placeholder missing"
out = tpl.replace('@MAPDATA@', compact)

with open('game-standalone.html', 'w', encoding='utf-8') as f:
    f.write(out)

print("WRITTEN", len(out), "bytes;", out.count('"id":"'), "zone refs")
