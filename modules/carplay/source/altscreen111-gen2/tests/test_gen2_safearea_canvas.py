#!/usr/bin/env python3
"""Host test: gen2_safearea.sh takes its canvas size from altscreen111.conf (default 1010x376).

HOST-ONLY: runs the script in a sandbox with stubbed mount/sync under bash and dash.
It does not prove behavior on the QNX ksh; the target-shell gate covers that separately.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[5]
SCRIPT = ROOT / "modules/navigation/runtime/gen2_safearea.sh"
BASE_CONF = ROOT / "modules/carplay/runtime/auto-direct/altscreen111.conf"
AID123_CONF = ROOT / "modules/carplay/runtime/auto-direct/altscreen111-800x480.conf"
SHELLS = [s for s in ("bash", "dash") if shutil.which(s)]


def run(shell, mibr, stub, *args):
    env = {"PATH": f"{stub}:/usr/bin:/bin", "MIBR_ROOT": str(mibr)}
    p = subprocess.run([shell, str(SCRIPT), *args], env=env, capture_output=True, text=True)
    out = dict(line.split("=", 1) for line in p.stdout.splitlines() if "=" in line)
    return p.returncode, out, p.stdout


def sandbox(conf_text=None):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gen2-safearea-"))
    stub = tmp / "stub"
    stub.mkdir()
    for name in ("mount", "sync"):
        (stub / name).write_text("#!/bin/sh\nexit 0\n")
        (stub / name).chmod(0o755)
    mibr = tmp / "mibr"
    (mibr / "config/cockpit").mkdir(parents=True)
    (mibr / "config/carplay").mkdir(parents=True)
    if conf_text is not None:
        (mibr / "config/carplay/altscreen111.conf").write_text(conf_text)
    return tmp, mibr, stub


def stored(mibr):
    return (mibr / "config/cockpit/mibr-carplay111-safearea.conf").read_text().split()


for shell in SHELLS:
    # No config: the 1010x376 reference stays.
    tmp, mibr, stub = sandbox()
    rc, out, _ = run(shell, mibr, stub, "status")
    assert rc == 0 and (out["full_width"], out["full_height"], out["full_source"]) == ("1010", "376", "default"), out
    rc, out, _ = run(shell, mibr, stub, "full")
    assert rc == 0 and stored(mibr) == ["x=0", "y=0", "w=1010", "h=376"]
    rc, out, _ = run(shell, mibr, stub, "set", "10", "130", "990", "140")  # skoda-mu1440 voll
    assert rc == 0
    rc, out, _ = run(shell, mibr, stub, "set", "0", "0", "1011", "376")
    assert rc == 11 and out["GEN2_SAFEAREA"].startswith("FAIL_RANGE"), out
    shutil.rmtree(tmp)

    # The shipped default conf names 1010x376 explicitly: same result, source altscreen111.conf.
    tmp, mibr, stub = sandbox(BASE_CONF.read_text())
    rc, out, _ = run(shell, mibr, stub, "status")
    assert rc == 0 and (out["full_width"], out["full_height"], out["full_source"]) == ("1010", "376", "altscreen111.conf"), out
    shutil.rmtree(tmp)

    # 800x480 variant.
    tmp, mibr, stub = sandbox(AID123_CONF.read_text())
    rc, out, _ = run(shell, mibr, stub, "status")
    assert rc == 0 and (out["full_width"], out["full_height"], out["configured"]) == ("800", "480", "0"), out
    assert out["w"] == "800" and out["h"] == "480", out
    rc, out, _ = run(shell, mibr, stub, "full")
    assert rc == 0 and stored(mibr) == ["x=0", "y=0", "w=800", "h=480"]
    rc, out, _ = run(shell, mibr, stub, "inset", "0", "64", "0", "80")
    assert rc == 0 and stored(mibr) == ["x=0", "y=64", "w=800", "h=336"]
    rc, out, _ = run(shell, mibr, stub, "bottom", "80")
    assert rc == 0 and stored(mibr) == ["x=0", "y=0", "w=800", "h=400"]
    rc, out, _ = run(shell, mibr, stub, "set", "272", "64", "256", "336")
    assert rc == 0
    rc, out, _ = run(shell, mibr, stub, "status")
    assert out["configured_in_range"] == "1", out
    rc, out, _ = run(shell, mibr, stub, "set", "0", "0", "1010", "376")  # 1010x376 values on 800x480
    assert rc == 11 and out["GEN2_SAFEAREA"].startswith("FAIL_RANGE"), out
    rc, out, _ = run(shell, mibr, stub, "bottom", "480")
    assert rc != 0
    # A rectangle stored for 1010x376 is reported as out of range, not silently trusted.
    (mibr / "config/cockpit/mibr-carplay111-safearea.conf").write_text("x=10\ny=130\nw=990\nh=140\n")
    rc, out, _ = run(shell, mibr, stub, "status")
    assert rc == 0 and out["configured_in_range"] == "0", out
    rc, out, _ = run(shell, mibr, stub, "clear")
    assert rc == 0 and out["fallback"] == "full_canvas_800x480", out
    shutil.rmtree(tmp)

    # Broken canvas size: stop, write nothing.
    for bad in ("ALTSCREEN111_WIDTH=abc\nALTSCREEN111_HEIGHT=480\n",
                "ALTSCREEN111_WIDTH=800\n",
                "ALTSCREEN111_WIDTH=99999\nALTSCREEN111_HEIGHT=480\n",
                "ALTSCREEN111_WIDTH=800\nALTSCREEN111_HEIGHT=0\n"):
        tmp, mibr, stub = sandbox(bad)
        rc, out, _ = run(shell, mibr, stub, "full")
        assert rc == 14 and out["GEN2_SAFEAREA"].startswith("FAIL_CANVAS_SIZE"), (bad, rc, out)
        assert not (mibr / "config/cockpit/mibr-carplay111-safearea.conf").exists()
        shutil.rmtree(tmp)

    # A config without a trailing newline is still read.
    tmp, mibr, stub = sandbox("ALTSCREEN111_WIDTH=800\nALTSCREEN111_HEIGHT=480")
    rc, out, _ = run(shell, mibr, stub, "status")
    assert rc == 0 and out["full_height"] == "480", out
    shutil.rmtree(tmp)

print(f"GEN2_SAFEAREA_CANVAS_TEST=PASS shells={','.join(SHELLS)}")
sys.exit(0)
