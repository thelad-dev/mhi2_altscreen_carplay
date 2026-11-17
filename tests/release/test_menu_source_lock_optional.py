"""Optional-profile handling of the fail-closed menu source lock."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/release/verify_menu_source_lock.py"
SPEC = importlib.util.spec_from_file_location("verify_menu_source_lock", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

OPTIONAL_ROOT = module.OPTIONAL_HMI_ROOTS[0]


class OptionalProfileLockTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.write("modules/menu/source/java/Menu.java", "class Menu {}\n")
        self.write("settings/registry.json", "{}\n")
        for root in module.HMI_ROOTS:
            profile = root.split("/")[2]
            self.write(f"modules/profiles/{profile}/profile.json", "{}\n")
            self.write(f"{root}/README.md", "HMI source\n")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")

    def write(self, path, content):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=True, text=True,
            capture_output=True,
        ).stdout.strip()

    def make_lock(self, optional):
        objects = {
            "modules/menu/source": self.git("rev-parse", "HEAD:modules/menu/source"),
            "settings/registry.json": self.git("rev-parse", "HEAD:settings/registry.json"),
        }
        roots = module.HMI_ROOTS + ((OPTIONAL_ROOT,) if optional else ())
        for root in roots:
            for path in self.git("ls-tree", "-r", "--name-only", "HEAD", "--", root).splitlines():
                objects[path] = self.git("rev-parse", "HEAD:" + path)
        for root in module.HMI_ROOTS:
            profile_path = root[:-len("/hmi")] + "/profile.json"
            objects[profile_path] = self.git("rev-parse", "HEAD:" + profile_path)
        lock = {"schema": 2, "hmi_roots": list(module.HMI_ROOTS), "git_objects": objects}
        if optional:
            lock["optional_hmi_roots"] = [OPTIONAL_ROOT]
        return lock

    def add_optional(self):
        self.write(OPTIONAL_ROOT + "/README.md", "optional HMI\n")
        self.git("add", ".")
        self.git("commit", "-qm", "optional profile HMI")

    def test_absent_optional_profile_passes_without_lock_key(self):
        self.assertEqual(module.verify(self.repo, self.make_lock(False))["status"], "PASS")

    def test_optional_profile_present_and_locked_passes(self):
        self.add_optional()
        result = module.verify(self.repo, self.make_lock(True))
        self.assertEqual(result["status"], "PASS")
        self.assertIn(OPTIONAL_ROOT, result["hmi_roots"])

    def test_optional_profile_present_but_unlocked_blocks(self):
        self.add_optional()
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_OPTIONAL_PROFILE_UNLOCKED"):
            module.verify(self.repo, self.make_lock(False))

    def test_optional_profile_locked_but_missing_blocks(self):
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_PROFILE_MISSING"):
            module.verify(self.repo, self.make_lock(True))

    def test_optional_file_change_blocks_stale_lock(self):
        self.add_optional()
        lock = self.make_lock(True)
        self.write(OPTIONAL_ROOT + "/README.md", "changed\n")
        self.git("add", ".")
        self.git("commit", "-qm", "change optional HMI")
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_LOCK_STALE"):
            module.verify(self.repo, lock)

    def test_optional_new_file_blocks_path_set(self):
        self.add_optional()
        lock = self.make_lock(True)
        self.write(OPTIONAL_ROOT + "/extra.txt", "x\n")
        self.git("add", ".")
        self.git("commit", "-qm", "extra file")
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_HMI_PATH_SET_MISMATCH"):
            module.verify(self.repo, lock)

    def test_unknown_optional_root_is_rejected(self):
        lock = self.make_lock(False)
        lock["optional_hmi_roots"] = ["modules/profiles/other/hmi"]
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_LOCK_OPTIONAL_ROOTS_INVALID"):
            module.verify(self.repo, lock)


if __name__ == "__main__":
    unittest.main()
