"""Path/acceptance boundaries for the shared synthetic fixture, without NAS access."""

import importlib.util
import base64
import errno
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


DRIVER = Path(__file__).resolve().parents[1] / "scripts/nas-audit-fixture.py"
SPEC = importlib.util.spec_from_file_location("audit_fixture", DRIVER)
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_live_paths_are_derived_and_confined(self):
        workspace = self.root / "nas-audit-test_123"
        workspace.mkdir(mode=0o700)
        with patch.object(fixture, "WORKSPACE_PARENT", self.root):
            self.assertEqual(fixture.workspace_paths(workspace), (
                workspace / "private/source", workspace / "evidence",
                Path("/mnt/storage/99_tmp/nas-audit-test_123/dataset"),
            ))

    def test_invalid_and_symlink_workspaces_are_rejected(self):
        real = self.root / "nas-audit-real"
        real.mkdir()
        alias = self.root / "nas-audit-alias"
        alias.symlink_to(real, target_is_directory=True)
        invalid = [Path("nas-audit-relative"), self.root / "ordinary-data",
                   self.root / "nas-audit-missing", alias, real / "nested"]
        with patch.object(fixture, "WORKSPACE_PARENT", self.root):
            for candidate in invalid:
                with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                    fixture.workspace_paths(candidate)

    def test_nonempty_claimed_fixture_is_refused_before_source_creation(self):
        final = self.root / "final"
        final.mkdir()
        payload = final / "keep"
        payload.write_bytes(b"existing content")
        source = self.root / "private/source"
        with patch.object(fixture, "FINAL", final / "dataset"), patch.object(fixture, "SOURCE", source), \
                patch.object(fixture, "WORKSPACE", self.root):
            with self.assertRaisesRegex(RuntimeError, "nonempty"):
                fixture.seed()
        self.assertEqual(payload.read_bytes(), b"existing content")
        self.assertFalse(source.exists())

    def test_help_needs_no_installed_fixture_or_helper(self):
        result = subprocess.run([sys.executable, str(DRIVER), "--help"], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--workspace", result.stdout)

    def copied_native_fixture(self, with_acl=False):
        source, final = self.root / "source", self.root / "final"
        private = source / fixture.PRIVATE
        private.mkdir(parents=True)
        (private / "payload").write_bytes(b"owned synthetic bytes\n")
        os.link(private / "payload", private / "linked-payload")
        os.setxattr(private / "payload", "user.fixture", b"retained")
        if with_acl:
            subprocess.run(["setfacl", "-m", "u:1234:---", str(private)], check=True)
        entries = []
        for path in [source, *sorted(source.rglob("*"))]:
            info = path.stat()
            entries.append({"path": str(path.relative_to(source)),
                            "type": "directory" if path.is_dir() else "file",
                            "uid": info.st_uid, "gid": info.st_gid,
                            "mode": info.st_mode & 0o7777, "mtime_ns": info.st_mtime_ns,
                            "xattrs": {name: base64.b64encode(os.getxattr(path, name)).decode()
                                       for name in os.listxattr(path)}})
        final.mkdir(mode=0o700)
        with patch.object(fixture, "SOURCE", source), fixture.directory_handle(final) as root_fd:
            claim = fixture.copy_records(root_fd, entries)
        return source, final, claim

    def test_native_copy_preserves_bytes_metadata_xattrs_and_hardlinks(self):
        source, final, _ = self.copied_native_fixture()
        for original in [source, *source.rglob("*")]:
            copied = final / original.relative_to(source)
            before, after = original.stat(), copied.stat()
            self.assertEqual((before.st_uid, before.st_gid, before.st_mode, before.st_mtime_ns),
                             (after.st_uid, after.st_gid, after.st_mode, after.st_mtime_ns))
            if original.is_file():
                self.assertEqual(original.read_bytes(), copied.read_bytes())
                self.assertEqual(os.getxattr(copied, "user.fixture"), b"retained")
        first, second = final / fixture.PRIVATE / "payload", final / fixture.PRIVATE / "linked-payload"
        self.assertEqual(first.stat().st_ino, second.stat().st_ino)
        self.assertEqual(first.stat().st_nlink, 2)

    def test_symlink_swap_cannot_redirect_root_repair(self):
        _, final, claim = self.copied_native_fixture()
        outside = self.root / "outside"
        outside.mkdir(mode=0o700)
        (outside / "payload").write_bytes(b"unrelated data")
        previous = outside.stat()
        private = final / fixture.PRIVATE
        with fixture.directory_handle(final) as root_fd:
            private.rename(self.root / "moved-private")
            private.symlink_to(outside, target_is_directory=True)
            with patch.object(fixture.os, "fchown") as chown, patch.object(fixture.os, "fchmod") as chmod:
                with self.assertRaises(OSError) as error:
                    fixture.repair_claimed(root_fd, claim)
                self.assertIn(error.exception.errno, (errno.ELOOP, errno.ENOTDIR))
                chown.assert_not_called()
                chmod.assert_not_called()
        self.assertEqual(outside.stat().st_mode, previous.st_mode)
        self.assertEqual((outside / "payload").read_bytes(), b"unrelated data")

    def test_hardlink_substitution_cannot_redirect_root_repair(self):
        _, final, claim = self.copied_native_fixture()
        outside = self.root / "unrelated-file"
        outside.write_bytes(b"leave untouched")
        previous = outside.stat()
        payload = final / fixture.PRIVATE / "payload"
        payload.unlink()
        os.link(outside, payload)
        with fixture.directory_handle(final) as root_fd, patch.object(fixture.os, "fchown") as chown:
            with self.assertRaisesRegex(RuntimeError, "identity changed"):
                fixture.repair_claimed(root_fd, claim)
            chown.assert_not_called()
        self.assertEqual(outside.stat().st_mode, previous.st_mode)
        self.assertEqual(outside.read_bytes(), b"leave untouched")

    def test_cleanup_removes_only_the_claimed_objects(self):
        _, final, claim = self.copied_native_fixture()
        with fixture.directory_handle(final) as root_fd:
            fixture.cleanup_claimed(root_fd, claim)
        self.assertEqual(list(final.iterdir()), [])

    def test_extra_hardlink_stops_repair_before_metadata_changes(self):
        _, final, claim = self.copied_native_fixture()
        os.link(final / fixture.PRIVATE / "payload", self.root / "extra-link")
        with fixture.directory_handle(final) as root_fd, patch.object(fixture.os, "fchown") as chown:
            with self.assertRaisesRegex(RuntimeError, "unexpected backing hardlinks"):
                fixture.repair_claimed(root_fd, claim)
            chown.assert_not_called()

    def test_cleanup_preserves_unexpected_directory_contents(self):
        _, final, claim = self.copied_native_fixture()
        foreign = final / fixture.PRIVATE / "unrelated"
        foreign.mkdir()
        (foreign / "keep").write_bytes(b"do not delete")
        with fixture.directory_handle(final) as root_fd:
            with self.assertRaisesRegex(RuntimeError, "unexpected cleanup entries"):
                fixture.cleanup_claimed(root_fd, claim)
        self.assertEqual((foreign / "keep").read_bytes(), b"do not delete")
        self.assertTrue((final / fixture.PRIVATE / "payload").exists())

    def test_cleanup_rejects_substituted_directory(self):
        _, final, claim = self.copied_native_fixture()
        private = final / fixture.PRIVATE
        private.rename(self.root / "owned-private")
        private.mkdir()
        (private / "keep").write_bytes(b"foreign replacement")
        with fixture.directory_handle(final) as root_fd:
            with self.assertRaisesRegex(RuntimeError, "cleanup object identity changed"):
                fixture.cleanup_claimed(root_fd, claim)
        self.assertEqual((private / "keep").read_bytes(), b"foreign replacement")

    def test_cleanup_rechecks_entries_after_sealing(self):
        _, final, claim = self.copied_native_fixture()
        private = final / fixture.PRIVATE
        moved = self.root / "moved-during-seal"
        original_chown = fixture.os.fchown
        swapped = False

        def swap_before_first_seal(fd, uid, gid):
            nonlocal swapped
            if not swapped:
                private.rename(moved)
                private.mkdir()
                swapped = True
            return original_chown(fd, uid, gid)

        with fixture.directory_handle(final) as root_fd, \
                patch.object(fixture.os, "fchown", side_effect=swap_before_first_seal):
            with self.assertRaisesRegex(RuntimeError, "cleanup entry identity changed"):
                fixture.cleanup_claimed(root_fd, claim)
        self.assertTrue(private.is_dir())
        self.assertEqual(list(private.iterdir()), [])
        self.assertEqual((moved / "payload").read_bytes(), b"owned synthetic bytes\n")

    def test_invalid_live_cli_path_fails_before_helper_import(self):
        with patch.object(fixture.importlib.util, "spec_from_file_location") as load:
            with self.assertRaises(ValueError):
                fixture.main(["seed", "--workspace", str(self.root)])
            load.assert_not_called()

    @unittest.skipUnless(shutil.which("setfacl"), "local ACL utility required")
    def test_descriptor_repair_removes_acl_and_preserves_payload(self):
        _, final, claim = self.copied_native_fixture(with_acl=True)
        private = final / fixture.PRIVATE
        self.assertIn("system.posix_acl_access", os.listxattr(private))
        # Ownership changes require root on arbitrary CI identities; exercise all other fd effects.
        with fixture.directory_handle(final) as root_fd, patch.object(fixture.os, "fchown") as chown:
            fixture.repair_claimed(root_fd, claim)
            self.assertEqual(len(chown.call_args_list), 3)
            self.assertTrue(all(call.args[1:] == (1000, 1000) for call in chown.call_args_list))
        self.assertNotIn("system.posix_acl_access", os.listxattr(private))
        self.assertEqual(private.stat().st_mode & 0o7777, 0o775)
        for name in ["payload", "linked-payload"]:
            self.assertEqual((private / name).read_bytes(), b"owned synthetic bytes\n")
            self.assertEqual((private / name).stat().st_mode & 0o7777, 0o644)
            self.assertEqual(os.getxattr(private / name, "user.fixture"), b"retained")

    def test_acceptance_checks_survive_python_optimization(self):
        header = {"uid": 1000, "gid": 1000, "groups": [], "ledger_sha256": "same",
                  "tools": {"python": "3.13.5", "b3sum": "1.8.1", "helper_sha256": "same"}}
        before = [header, {"status": "denied_or_unresolved", "errno": 13},
                  {"status": "differences", "failures": 1}]
        after = [header, {"type": "file", "status": "read"}, {"type": "file", "status": "read"},
                 {"status": "accepted"}]
        verified = [header, {"status": "accepted"}]
        # A changed tool stack must not be accepted, even with Python assertions disabled.
        after[0] = {**header, "tools": {**header["tools"], "b3sum": "different"}}
        for name, records in [("access-before", before), ("access-after", after), ("verify-after", verified)]:
            (self.root / f"{name}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records))
        code = """
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location('fixture', sys.argv[1])
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
fixture.EVIDENCE = pathlib.Path(sys.argv[2])
fixture.check()
"""
        result = subprocess.run([sys.executable, "-O", "-c", code, str(DRIVER), str(self.root)],
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tool/helper versions changed", result.stderr)


if __name__ == "__main__":
    unittest.main()
