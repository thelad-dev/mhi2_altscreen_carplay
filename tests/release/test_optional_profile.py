"""Optional profile vw-mu1367-k4525: outside the required package, installer refuses installation.

Host-only (BUILD/HOST evidence): synthetic inputs, no OEM bytes, no unit run. The profile data
is a placeholder (selector digest and firmware check are MISSING_INPUT).
"""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/release"))
sys.path.insert(0, str(ROOT / "tools"))
import build_modular as bm  # noqa: E402
import check_profiles  # noqa: E402
import validate_modular_package as vmp  # noqa: E402

OPT = "vw-mu1367-k4525"
REQUIRED = {"skoda-mu1440-p4526", "seat-mu1409-p4708", "seat-mu1447-p4709"}
SELECT = ROOT / "installer/select-profile.ksh"
LIST = ROOT / "installer/config/profiles.list"


class OptionalProfileData(unittest.TestCase):
    def test_profile_is_optional_and_not_installable(self):
        docs = check_profiles.load_profiles()
        self.assertEqual(set(check_profiles.required_ids(docs)), REQUIRED)
        self.assertEqual(check_profiles.optional_ids(docs), [OPT])
        sel = docs[OPT]["selector"]
        self.assertEqual(docs[OPT]["release_inclusion"], "optional")
        # Installation stays off until the selector digest is unit-measured on the vehicle.
        if sel["evidence"] != "unit_measured":
            self.assertIs(sel["install_enabled"], False)

    def test_module_index_lists_optional_separately(self):
        index = json.loads((ROOT / "modules/module-index.json").read_text(encoding="utf-8"))
        self.assertEqual(set(index["profiles"]), REQUIRED)
        self.assertEqual(index["optional_profiles"], [OPT])

    def test_validator_constants_follow_profile_json(self):
        docs = check_profiles.load_profiles()
        self.assertEqual(vmp.PROFILES, set(check_profiles.required_ids(docs)))
        self.assertEqual(vmp.OPTIONAL_PROFILES, set(check_profiles.optional_ids(docs)))

    def test_committed_list_carries_row_that_mirrors_profile_json(self):
        rows = {r[1]: r for r in (l.split() for l in LIST.read_text().splitlines()
                                  if l and not l.startswith("#"))}
        sel = check_profiles.load_profiles()[OPT]["selector"]
        self.assertEqual(rows[OPT][0], sel["digest"])
        self.assertEqual(rows[OPT][3], "1" if sel["install_enabled"] else "0")


class OptionalProfilePackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        t = Path(cls.td.name)
        cls.native, cls.inst, cls.hmi = t / "bo", t / "inst", t / "hmi"
        bm.fake_native(cls.native)
        bm.fake_installer(cls.inst)
        bm.fake_hmi(cls.hmi)
        cls.t = t

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def build(self, name, **kw):
        files, meta = bm.assemble(self.native, ROOT, self.inst, hmi_dir=self.hmi, allow_dirty=True,
                                  allow_stale=True, **kw)
        return bm.write_zip(files, self.t / name), files, meta

    def test_default_package_excludes_optional_profile(self):
        _, files, meta = self.build("default.zip")
        self.assertEqual(set(meta["profiles"]), REQUIRED)
        self.assertFalse(any(n.startswith("profiles/%s/" % OPT) for n in files))
        listing = files["installer/config/profiles.list"][0].decode()
        self.assertNotIn(OPT, listing)
        vmp.validate(self.t / "default.zip", True)

    def test_optional_profile_needs_single_profile_scope(self):
        with self.assertRaises(bm.AssembleError):
            self.build("x.zip", profiles=[OPT])
        with self.assertRaises(bm.AssembleError):
            self.build("x.zip", profiles=sorted(REQUIRED) + [OPT])

    def test_single_profile_package_is_valid_and_install_disabled(self):
        _, files, meta = self.build("opt.zip", profiles=[OPT], scope=bm.SCOPE_VALUE)
        self.assertEqual(meta["profiles"], [OPT])
        sel = check_profiles.load_profiles()[OPT]["selector"]
        self.assertIs(meta["profile_info"][OPT]["install_enabled"], sel["install_enabled"])
        rows = [l.split() for l in files["installer/config/profiles.list"][0].decode().splitlines()
                if l and not l.startswith("#")]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0][0], rows[0][1]), (sel["digest"], OPT))
        vmp.validate(self.t / "opt.zip", True)

    def test_optional_profile_in_default_package_is_rejected_by_validator(self):
        # A package that declares the optional profile without the single-profile scope violates
        # the required three-profile contract.
        files = vmp.fixture_files(OPT, enabled={OPT: False})  # synthetic rows, independent of profile data
        sealed = vmp.seal(files, [OPT], None)
        path = self.t / "bad.zip"
        vmp.write_zip(path, sealed)
        with self.assertRaisesRegex(vmp.PackageError, "unexpected profile set"):
            vmp.validate(path)


class SelectorRefusesOptionalProfile(unittest.TestCase):
    """The shipped selector must stop before any write while the profile row is install-disabled
    (exit 6) and for an unknown hash (exit 4). A fake hash helper reports the row's digest."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.jxe = self.tmp / "lsd.jxe"
        self.jxe.write_bytes(b"synthetic")

    def helper(self, digest):
        tool = self.tmp / ("hash-%s" % digest[:4])
        tool.write_text("#!/bin/sh\necho %s  \"$1\"\n" % digest)
        tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
        return tool

    def select(self, digest):
        env = {"PATH": os.environ["PATH"], "MIBR_SHA256": str(self.helper(digest))}
        return subprocess.run(["sh", str(SELECT), str(LIST), "--jxe", str(self.jxe),
                               "--train", "MHI2_ER_VWG13_K4525"],
                              capture_output=True, text=True, env=env)

    def test_disabled_row_is_refused(self):
        row = [l.split() for l in LIST.read_text().splitlines() if " %s " % OPT in l][0]
        if row[3] != "0":
            self.skipTest("profile is install-enabled; disabled-row refusal covered by tests/deployment")
        r = self.select(row[0])
        self.assertEqual((r.returncode, r.stdout), (6, ""))
        self.assertIn("DISABLED profile=" + OPT, r.stderr)

    def test_unknown_digest_is_refused(self):
        r = self.select("f" * 64)
        self.assertEqual((r.returncode, r.stdout), (4, ""))


if __name__ == "__main__":
    unittest.main()
