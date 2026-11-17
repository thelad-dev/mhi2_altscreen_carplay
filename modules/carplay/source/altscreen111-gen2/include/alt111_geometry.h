#ifndef MIBR_ALT111_GEOMETRY_H
#define MIBR_ALT111_GEOMETRY_H

/* Compiled SafeArea presets per Stream-111 display size. Header-only and free
 * of I/O so host tests can include it without the QNX interposer.
 *
 * A preset is only a compiled starting point. Precedence at run time stays:
 * menu choice > stored registry value > platform defaults.conf > this table.
 * A size without a row falls back to the full canvas for every area.
 *
 * Index = ViewArea index: 0 = wide (initial), 1 = voll, 2 = center.
 *
 * 1010x376: unchanged values of the MU1440 reference (SOURCE: the previously
 *   hard-wired special case; the 58/70 px bands are the only measured OEM
 *   overlay bands in this repository).
 *
 * 800x480 (VW MU1367 / AID 12.3 candidate): derived, not scaled from 1010x376.
 *   Inputs: [Unverifiziert] no calibration photo, DMDT value or vehicle trace
 *   exists for this size; 800x480 itself is Prior Art (OneB1t baseline,
 *   Omonob 791 profile).
 *   Rules:
 *   1. The OEM overlay bands (top status line, bottom lane bar) are fixed
 *      panel elements. [Spekulation] They keep their absolute pixel height
 *      on the taller canvas, so the measured 58/70 px are taken over and
 *      rounded outwards to the 16 px H.264 macroblock grid (800 = 50 x 16,
 *      480 = 30 x 16): top 64, bottom 80 -> band height 336. Outward rounding
 *      only shrinks the safe area, the conservative direction.
 *   2. The center band keeps its absolute 256 px width (16 macroblocks) and is
 *      centered on the canvas: x = (800 - 256) / 2 = 272 (17 macroblocks).
 *   3. Nesting center in voll in wide in canvas, as in the 1010x376 table.
 *   4. Every rectangle satisfies the load-time checks (w >= 100, h >= 60,
 *      inside the owning ViewArea).
 *   These are provisional. Calibrate on the vehicle and override via the menu
 *   or the platform defaults file; no claim is made about the real cluster
 *   layout. */
struct alt111_geom_rect { int x, y, w, h; };
struct alt111_geom_preset {
    int width, height;
    struct alt111_geom_rect safe[3];
};

static const struct alt111_geom_preset alt111_geom_presets[] = {
    { 1010, 376, { { 0, 0, 1010, 376 }, { 0, 58, 1010, 248 }, { 370, 58, 256, 248 } } },
    {  800, 480, { { 0, 0,  800, 480 }, { 0, 64,  800, 336 }, { 272, 64, 256, 336 } } }
};

static inline const struct alt111_geom_preset *alt111_geom_find(int width, int height)
{
    unsigned i;
    for (i = 0; i < sizeof(alt111_geom_presets) / sizeof(alt111_geom_presets[0]); ++i)
        if (alt111_geom_presets[i].width == width && alt111_geom_presets[i].height == height)
            return &alt111_geom_presets[i];
    return (const struct alt111_geom_preset *)0;
}

#endif
