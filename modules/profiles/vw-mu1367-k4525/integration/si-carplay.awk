# si-carplay.awk - smartphone_integrator.json CarPlay environment transform.
#
# Rewrites the first "envs":[ array of the "carplay" child (inside "children")
# to the exact eleven-entry U2 environment list (ten U2 entries plus the
# steering-wheel zoom flag). Derived from the SEAT MU1409 transform of this
# repository; the stock file is never shipped, only this transform.
#
# Profile vw-mu1367-k4525 (VW MU1367, AID 12.3 inch cluster): the default
# geometry here is 800x480, NOT the 1010x376 of the AID10 class profiles.
# [Unverifiziert] 800x480 comes from prior art (OneB1t baseline, Omonob 791),
# not from a measurement on this unit; the real map area is MISSING_INPUT.
# [Schlussfolgerung] The native library reads ALTSCREEN111_WIDTH/HEIGHT from
# this env list, so the profile binds the values here, not in shared code.
# SafeArea/ViewArea presets for 800x480 are derived separately (not scaled
# from 1010x376). No on-vehicle behavior is claimed.
#
# Usage: awk -f si-carplay.awk [-v hook=... -v altport=... -v teeport=...
#        -v width=... -v height=... -v fps=... -v autoshow=... -v url=...]
#        stock-smartphone_integrator.json > patched
# Defaults are the shipped altscreen111.conf values.
#
# Exit codes: 3 = carplay envs array not found, 6 = input already carries a
# CarPlay preload hook (not stock; refuse to patch twice).
BEGIN {
    if (hook == "") hook = "/mnt/app/eso/lib/libmibr_carplay111.so"
    if (altport == "") altport = "6031"
    if (teeport == "") teeport = "19820"
    if (width == "") width = "800"
    if (height == "") height = "480"
    if (fps == "") fps = "30"
    if (autoshow == "") autoshow = "0"
    if (url == "") url = "maps:/car/instrumentcluster"
    # Steering-wheel zoom bridge flag (GEN2, env-gated; Skoda never sets it). Default 0 (off) until the MU1367
    # wheel key codes are measured: [Unverifiziert] whether MU1367 uses the SEAT code mapping, so the SEAT path is not enabled by guess.
    if (seatzoom == "") seatzoom = "0"
    in_children = 0; in_carplay = 0; patched = 0; foreign = 0
}
{
    if ($0 ~ /libaltscreen111\.so/ || $0 ~ /libmibr_carplay111\.so/) foreign = 1
    if ($0 ~ /"children"[ \t]*:/) in_children = 1
    if (in_children && !in_carplay && $0 ~ /^[ \t]*"carplay"[ \t]*:/) in_carplay = 1
    if (in_carplay && !patched && $0 ~ /^[ \t]*"envs"[ \t]*:\[/) {
        indent = $0; sub(/"envs".*/, "", indent)
        print indent "\"envs\":[\"LD_PRELOAD=" hook "\", \"ALTSCREEN111_PORT=" altport "\", \"ALTSCREEN111_TEE_PORT=" teeport "\", \"ALTSCREEN111_WIDTH=" width "\", \"ALTSCREEN111_HEIGHT=" height "\", \"ALTSCREEN111_FPS=" fps "\", \"ALTSCREEN111_AUTO_SHOW=" autoshow "\", \"ALTSCREEN111_URL=" url "\", \"ALTSCREEN111_SEAT_WHEEL_ZOOM=" seatzoom "\", \"LD_LIBRARY_PATH=/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib\", \"IPL_CONFIG_DIR_DIO_MANAGER=/etc/eso/production\"],"
        patched = 1
        next
    }
    print
}
END {
    if (foreign) exit 6
    if (!patched) exit 3
}
