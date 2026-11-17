#!/usr/bin/env python3
"""Host test: 800x480 geometry files stay consistent with the compiled table and with the 1010x376 default.

HOST-ONLY: no vehicle behavior is exercised.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[5]
HEADER = ROOT / "modules/carplay/source/altscreen111-gen2/include/alt111_geometry.h"
VW_CONF = ROOT / "modules/navigation/source/platform-defaults/vw-mu1367.conf"
BASE_CONF = ROOT / "modules/carplay/runtime/auto-direct/altscreen111.conf"
AID123_CONF = ROOT / "modules/carplay/runtime/auto-direct/altscreen111-800x480.conf"
SKODA_CONF = ROOT / "modules/navigation/source/platform-defaults/skoda-mu1440.conf"


def kv(path):
    out = {}
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def table():
    text = HEADER.read_text()
    rows = {}
    for m in re.finditer(r"\{\s*(\d+),\s*(\d+),\s*\{(.*?)\}\s*\}\s*[,\n]", text, re.S):
        rects = [tuple(int(v) for v in r) for r in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}", m.group(3))]
        if len(rects) == 3:
            rows[(int(m.group(1)), int(m.group(2)))] = rects
    return rows


def rect(value):
    r = tuple(int(v) for v in value.split(","))
    assert len(r) == 4, value
    return r


def inside(a, b):
    return a[0] >= b[0] and a[1] >= b[1] and a[0] + a[2] <= b[0] + b[2] and a[1] + a[3] <= b[1] + b[3]


rows = table()
assert (1010, 376) in rows and (800, 480) in rows, rows.keys()

# vw-mu1367.conf == compiled 800x480 table (view 0 = wide, 1 = voll, 2 = center)
vw = kv(VW_CONF)
assert set(vw) == {"safe_wide", "safe_voll", "safe_center"}, vw  # no invented input mapping
w, h = 800, 480
wide, voll, center = rect(vw["safe_wide"]), rect(vw["safe_voll"]), rect(vw["safe_center"])
assert [wide, voll, center] == rows[(800, 480)], (wide, voll, center, rows[(800, 480)])
canvas = (0, 0, w, h)
assert inside(wide, canvas) and inside(voll, wide) and inside(center, voll)
for name, r in (("wide", wide), ("voll", voll), ("center", center)):
    assert r[2] >= 100 and r[3] >= 60, name  # load-time minimum of the GEN2 library
    assert all(v % 16 == 0 for v in r), name  # 16 px macroblock grid (800 = 50 x 16, 480 = 30 x 16)
assert voll[1] >= 58 and h - (voll[1] + voll[3]) >= 70  # measured 1010x376 OEM bands are kept, never shrunk
assert center[2] == 256 and center[0] * 2 + center[2] == w

# not a scaled copy of any existing profile
for other in (SKODA_CONF,):
    o = kv(other)
    for key in ("safe_wide", "safe_voll", "safe_center"):
        assert rect(o[key]) != rect(vw[key]), (other.name, key)
ref = rows[(1010, 376)]
for scaled in ((round(v * 800 / 1010) for v in ref[1]), (round(v * 480 / 376) for v in ref[1])):
    assert tuple(scaled) != voll

# the 800x480 launcher config differs from the 1010x376 default in the size lines only
base, alt = kv(BASE_CONF), kv(AID123_CONF)
assert set(base) == set(alt)
diff = {k for k in base if base[k] != alt[k]}
assert diff == {"ALTSCREEN111_WIDTH", "ALTSCREEN111_HEIGHT"}, diff
assert (base["ALTSCREEN111_WIDTH"], base["ALTSCREEN111_HEIGHT"]) == ("1010", "376")  # default unchanged
assert (alt["ALTSCREEN111_WIDTH"], alt["ALTSCREEN111_HEIGHT"]) == ("800", "480")
assert alt["ALTSCREEN111_FPS"] == "30"
print("GEOMETRY_PROFILE_FILES_TEST=PASS")
sys.exit(0)
