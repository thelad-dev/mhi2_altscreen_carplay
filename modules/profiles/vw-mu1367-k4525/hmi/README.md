# vw-mu1367-k4525 / hmi

Adapter scaffold for the optional VW MU1367 (firmware train K4525) profile. It is **not activated**: no profile selector digest exists for it, nothing builds or installs it, and nothing here is vehicle-tested.

What is here:

- `oem-anchors.json` reuses the MU1440 anchor set (`anchors_from`). [Unverifiziert] Whether those exact anchors match this firmware is undecided until the real `lsd.jar` has been compared.
- `java/de/mibr/hmi/MibrVwMu1367Profile.java` extends the MU1440 adapter and only changes the profile id. View id, tile geometry and image offset are inherited and unverified.

MISSING_INPUT (nothing is substituted, no OEM file is stored in this repository):

- the firmware `lsd.jar` and its SHA-256 (`hmi.api_jar_sha256`)
- the J9/Java toolchain used to compile against it

The common Java menu logic and the MIBR/3 client stay owned once by `modules/menu/source`. This profile is optional and not part of the required three-profile beta. An empty or scaffold-only directory is not a built adapter and not evidence of any target-side behavior.
