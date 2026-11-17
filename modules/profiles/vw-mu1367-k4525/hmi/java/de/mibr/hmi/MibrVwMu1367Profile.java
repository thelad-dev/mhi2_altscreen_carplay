package de.mibr.hmi;

/**
 * VW MU1367 (K4525) profile scaffold. Not activated.
 *
 * Everything except the id is inherited from the MU1440 adapter. The
 * inherited internalViewId, tile geometry, dropdown strategy and image index
 * offset are unverified for this firmware until the real lsd.jar has been
 * compared (MISSING_INPUT); override them here only with measured values.
 */
public class MibrVwMu1367Profile extends MibrSkodaMu1440Profile {
    public String id() { return "vw-mu1367-k4525"; }
}
