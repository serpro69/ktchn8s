"""Disposable local fixtures; real UID-1000/RO-NFS acceptance lives in Molecule."""

import base64
from contextlib import redirect_stderr
import errno
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/nas-migration-audit.py"
SPEC = importlib.util.spec_from_file_location("nas_audit", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.source.mkdir()
        self.final = self.base / "final"
        self.final.mkdir()
        self.evidence = self.base / "evidence"
        self.evidence.mkdir()
        self.serial = 0
        self.assertIsNotNone(shutil.which("b3sum"), "run in nix develop with b3sum")

    def output(self, stem="output"):
        self.serial += 1
        return self.evidence / f"{stem}-{self.serial}.jsonl"

    def run_audit(self, *args, code=0, output=None):
        output = output or self.output()
        with redirect_stderr(io.StringIO()) as errors:
            result = audit.main([*map(str, args), "--run-id", "test-run", "--output", str(output)])
        self.assertEqual(result, code, errors.getvalue())
        if code == 2:
            self.assertFalse(output.exists(), errors.getvalue())
        else:
            rows = self.rows(output)
            self.assertEqual(rows[-1]["status"], "accepted" if code == 0 else "differences")
            self.assertEqual(rows[-1]["count"], len(rows) - 2)
        return output

    @staticmethod
    def rows(path):
        return [json.loads(line) for line in path.read_text().splitlines()]

    def inventory(self, root=None, source="A", code=0, **kwargs):
        return self.run_audit("inventory", "--root", root or self.source,
                              "--source-id", source, "--disk-id", "disk-" + source, code=code, **kwargs)

    def ledger(self, inventories, rows=None):
        if rows is None:
            rows = []
            for inventory in inventories:
                header, *entries, _ = self.rows(inventory)
                for entry in entries:
                    rows.append({"record": "disposition", "source_id": header["source_id"],
                                 "source_path": entry["path"], "disposition": "keep",
                                 "destination": entry["path"], "reason": "fixture copy",
                                 "expected": audit.signature(entry)})
        output = self.output("ledger")
        digests = {self.rows(p)[0]["source_id"]: hashlib.sha256(p.read_bytes()).hexdigest() for p in inventories}
        with audit.Generation(output, "ledger", "test-run", inventories=digests) as generation:
            for row in rows:
                generation.add(row)
            generation.finish()
        return output

    def verify(self, inventories, ledger, code=0, **kwargs):
        inputs = [value for path in inventories for value in ("--inventory", path)]
        return self.run_audit("verify", "--root", self.final, "--ledger", ledger, *inputs, code=code, **kwargs)

    def copied_fixture(self):
        (self.source / "payload").write_bytes(b"preserve these bytes\n")
        inventory = self.inventory()
        shutil.copytree(self.source, self.final, dirs_exist_ok=True, symlinks=True)
        ledger = self.ledger([inventory])
        return inventory, ledger

    def ledger_rows(self, ledger):
        return self.rows(ledger)[1:-1]

    def test_cli_exit_codes_and_help(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn("inventory", result.stdout)
        result = subprocess.run([sys.executable, str(SCRIPT), "inventory"], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)

    def test_unusual_names_empty_directories_and_literal_symlinks(self):
        names = ["with space", "with\nnewline", "Кириллица", "--option", "back\\slash", os.fsdecode(b"byte-\xff")]
        for name in names:
            (self.source / name).write_bytes(b"abc")
        (self.source / "empty").mkdir()
        (self.source / "outside").symlink_to(self.base / "nonexistent")
        (self.source / "relative").symlink_to("with\nnewline")
        inventory = self.inventory()
        entries = {r["path"]: r for r in self.rows(inventory)[1:-1]}
        for name in names:
            self.assertEqual(entries[name]["blake3"], "6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85")
        self.assertEqual(entries["empty"]["type"], "directory")
        self.assertEqual(entries["relative"]["target"], "with\nnewline")
        self.assertEqual(entries["outside"]["type"], "symlink")
        self.assertNotIn("atime_ns", entries["with space"])
        self.assertNotIn("ctime_ns", entries["with space"])

    def test_xattrs_preserved_and_changed_xattr_rejected(self):
        (self.source / "file").write_bytes(b"data")
        os.setxattr(self.source / "file", "user.audit", b"\0binary\xff")
        inventory = self.inventory()
        shutil.copytree(self.source, self.final, dirs_exist_ok=True)
        ledger = self.ledger([inventory])
        self.verify([inventory], ledger)
        entry = next(r for r in self.rows(inventory) if r.get("path") == "file")
        self.assertEqual(base64.b64decode(entry["xattrs"]["user.audit"]), b"\0binary\xff")
        os.setxattr(self.final / "file", "user.audit", b"changed")
        self.verify([inventory], ledger, code=1)

    def test_special_entries_never_hashed(self):
        os.mkfifo(self.source / "fifo")
        with socket.socket(socket.AF_UNIX) as server:
            server.bind(str(self.source / "socket"))
            with patch.object(audit, "hash_fd", side_effect=AssertionError("special file read")):
                inventory = self.inventory()
        entries = {r["path"]: r for r in self.rows(inventory)[1:-1]}
        self.assertEqual(entries["fifo"]["type"], "fifo")
        self.assertEqual(entries["socket"]["type"], "socket")
        self.verify([inventory], self.ledger([inventory]), code=2)
        rows = self.ledger_rows(self.ledger([inventory]))
        for row in rows:
            row.update(disposition="discard", destination=None, reason="explicit special-entry disposition")
        self.verify([inventory], self.ledger([inventory], rows))

    def test_archive_requires_restore_decision_and_checks_archive_bytes(self):
        os.mkfifo(self.source / "fifo")
        source = self.inventory()
        (self.final / "archive.tar").write_bytes(b"fixture archive representation")
        final = self.inventory(self.final, "archive")
        expected = audit.signature(next(r for r in self.rows(final) if r.get("path") == "archive.tar"))
        rows = self.ledger_rows(self.ledger([source]))
        for row in rows:
            if row["source_path"] == ".":
                row.update(disposition="discard", destination=None, reason="source container directory retired")
            else:
                row.update(disposition="archive", destination="archive.tar", expected=expected,
                           restore="Operator recorded mkfifo reconstruction and source metadata in the archive")
        self.verify([source], self.ledger([source], rows))
        (self.final / "archive.tar").write_bytes(b"corrupted archive")
        self.verify([source], self.ledger([source], rows), code=1)

    def test_completed_generation_never_overwritten(self):
        output = self.inventory()
        original = output.read_bytes()
        with redirect_stderr(io.StringIO()):
            status = audit.main(["inventory", "--root", str(self.source), "--source-id", "A", "--disk-id", "disk-A",
                                 "--run-id", "retry", "--output", str(output)])
        self.assertEqual(status, 2)
        self.assertEqual(output.read_bytes(), original)
        self.assertNotEqual(self.rows(self.inventory())[0]["generation"], self.rows(output)[0]["generation"])

    def test_failed_scan_and_hash_leave_unpublished_partial_then_retry(self):
        (self.source / "file").write_bytes(b"data")
        for failure in (OSError(errno.EIO, "read failure"), subprocess.CalledProcessError(4, "b3sum")):
            with self.subTest(failure=failure):
                with patch.object(audit, "hash_fd", side_effect=failure):
                    self.inventory(code=2)
        partials = list(self.evidence.glob("*.partial"))
        self.assertEqual(len(partials), 2)
        for partial in partials:
            self.assertNotEqual(self.rows(partial)[-1].get("record"), "complete")
        self.inventory()

    def test_enumeration_and_xattr_errors_are_not_empty_successes(self):
        for target in ("scandir", "listxattr"):
            with self.subTest(target=target), patch.object(audit.os, target, side_effect=OSError(errno.EIO, "fixture")):
                self.inventory(code=2)

    def test_source_change_during_hash_is_execution_error(self):
        (self.source / "file").write_bytes(b"abc")
        real_run = subprocess.run

        def mutate(*args, **kwargs):
            result = real_run(*args, **kwargs)
            if "stdin" in kwargs:
                (self.source / "file").write_bytes(b"changed")
            return result

        with patch.object(audit.subprocess, "run", side_effect=mutate):
            self.inventory(code=2)

    def test_atomic_publication_race_does_not_replace_winner(self):
        output = self.output()
        with audit.Generation(output, "ledger", "test") as generation:
            output.write_text("other writer")
            with self.assertRaises(FileExistsError):
                generation.finish()
        self.assertEqual(output.read_text(), "other writer")

    def test_initialization_errors_close_resources(self):
        with patch.object(audit.sqlite3, "connect", side_effect=sqlite3.OperationalError("no space")):
            with self.assertRaises(sqlite3.OperationalError), audit.Index(self.evidence):
                self.fail("must not finish initialization")
        self.assertEqual(list(self.evidence.iterdir()), [])
        generation = audit.Generation(self.output(), "ledger", "test")
        with patch.object(generation, "_write", side_effect=OSError(errno.ENOSPC, "no space")):
            with self.assertRaises(OSError), generation:
                self.fail("must not finish initialization")
        self.assertTrue(generation.stream.closed)
        self.assertTrue(generation.partial.exists())
        self.assertFalse(generation.output.exists())

    def test_output_inside_audited_root_rejected_before_writing(self):
        self.inventory(output=self.source / "bad.jsonl", code=2)
        self.assertEqual(list(self.source.iterdir()), [])
        alias = self.base / "alias"
        alias.symlink_to(self.source, target_is_directory=True)
        self.inventory(output=alias / "bad.jsonl", code=2)
        self.assertEqual(list(self.source.iterdir()), [])
        source = self.inventory()
        copy = self.inventory(self.final, "copy")
        self.run_audit("compare", "--source", source, "--copy", copy, "--mode", "path",
                       output=self.source / "bad.jsonl", code=2)
        self.assertEqual(list(self.source.iterdir()), [])

    def test_truncated_modified_duplicate_and_partial_inputs_fail(self):
        source, ledger = self.copied_fixture()
        for kind in ("truncated", "modified", "duplicate-key", "trailing", "partial"):
            with self.subTest(kind=kind):
                broken = self.output("bad")
                raw = source.read_bytes()
                if kind == "truncated":
                    raw = b"\n".join(raw.splitlines()[:-1]) + b"\n"
                elif kind == "modified":
                    raw = raw.replace(b'"disk-A"', b'"disk-X"')
                elif kind == "duplicate-key":
                    raw = raw.replace(b'"disk_id":"disk-A"', b'"disk_id":"disk-A","disk_id":"disk-A"')
                elif kind == "trailing":
                    raw += b"{}\n"
                else:
                    broken = broken.with_suffix(".partial")
                broken.write_bytes(raw)
                self.verify([broken], ledger, code=2)

    def test_inventory_orphan_and_duplicate_paths_fail(self):
        source, ledger = self.copied_fixture()
        original = self.rows(source)
        for variant in ("orphan", "duplicate"):
            rows = [dict(row) for row in original[1:-1]]
            if variant == "orphan":
                rows[1]["path"] = "missing-parent/file"
            else:
                rows.append(rows[1])
            bad = self.output()
            with audit.Generation(bad, "inventory", "test", source_id="A", disk_id="A", root=str(self.source)) as generation:
                for row in rows:
                    generation.add(row)
                generation.finish()
            self.verify([bad], ledger, code=2)

    def test_path_compare_reports_missing_mismatch_and_extra(self):
        source, _ = self.copied_fixture()
        copy = self.inventory(self.final, "copy")
        self.run_audit("compare", "--source", source, "--copy", copy, "--mode", "path")
        (self.final / "payload").write_bytes(b"different")
        (self.final / "extra").mkdir()
        changed = self.inventory(self.final, "changed")
        report = self.run_audit("compare", "--source", source, "--copy", changed, "--mode", "path", code=1)
        self.assertIn("unexpected_copy_entry", [r.get("status") for r in self.rows(report)])
        (self.final / "payload").unlink()
        missing = self.inventory(self.final, "missing")
        report = self.run_audit("compare", "--source", source, "--copy", missing, "--mode", "path", code=1)
        self.assertIn("missing", [r.get("status") for r in self.rows(report)])

    def test_content_compare_keeps_each_equal_content_source_identity(self):
        for name in ("one", "two"):
            (self.source / name).write_bytes(b"same")
        source = self.inventory()
        (self.final / "elsewhere").write_bytes(b"same")
        shutil.copystat(self.source, self.final)
        copy = self.inventory(self.final, "copy")
        report = self.run_audit("compare", "--source", source, "--copy", copy, "--mode", "content")
        candidates = [r for r in self.rows(report) if r.get("status") == "candidate"]
        self.assertEqual({r["source_path"] for r in candidates}, {"one", "two"})
        self.assertEqual({r["copy_path"] for r in candidates}, {"elsewhere"})

    def test_verify_missing_duplicate_unknown_and_wrong_inventory_ledger(self):
        source, ledger = self.copied_fixture()
        rows = self.ledger_rows(ledger)
        self.verify([source], self.ledger([source], rows[:-1]), code=1)
        self.verify([source], self.ledger([source], rows + [rows[-1]]), code=2)
        unknown = [dict(r) for r in rows]
        unknown[-1]["source_path"] = "unknown"
        self.verify([source], self.ledger([source], unknown), code=2)
        other = self.inventory(source="B")
        self.verify([other], ledger, code=2)

    def test_metadata_changes_require_exact_declared_before_and_expected(self):
        source, ledger = self.copied_fixture()
        (self.final / "payload").chmod(0o600)
        self.verify([source], ledger, code=1)
        rows = self.ledger_rows(ledger)
        row = next(r for r in rows if r["source_path"] == "payload")
        before = row["expected"]["mode"]
        row["expected"]["mode"] = 0o600
        self.verify([source], self.ledger([source], rows), code=2)
        row["transformations"] = {"mode": {"before": before, "expected": 0o600, "reason": "declared repair"}}
        self.verify([source], self.ledger([source], rows))
        row["transformations"]["mode"]["before"] = 0
        self.verify([source], self.ledger([source], rows), code=2)

    def test_collision_merges_and_deduplication(self):
        source, ledger = self.copied_fixture()
        second = self.inventory(source="B")
        rows = self.ledger_rows(ledger) + self.ledger_rows(self.ledger([second]))
        self.verify([source, second], self.ledger([source, second], rows), code=2)
        for row in rows:
            if row["source_path"] == ".":
                row["disposition"] = "merge"
            elif row["source_id"] == "B":
                row["disposition"] = "deduplicate"
        self.verify([source, second], self.ledger([source, second], rows))
        rows[-1]["expected"]["mode"] ^= 0o100
        self.verify([source, second], self.ledger([source, second], rows), code=2)

    def test_differing_content_cannot_be_approved_as_deduplicate(self):
        source, ledger = self.copied_fixture()
        (self.source / "payload").write_bytes(b"different content")
        second = self.inventory(source="B")
        rows = self.ledger_rows(ledger) + self.ledger_rows(self.ledger([second]))
        for row in rows:
            row["disposition"] = "merge" if row["source_path"] == "." else "deduplicate"
        self.verify([source, second], self.ledger([source, second], rows), code=2)

    def test_equal_content_distinct_destinations_are_required(self):
        (self.source / "one").write_bytes(b"same")
        (self.source / "two").write_bytes(b"same")
        source = self.inventory()
        shutil.copytree(self.source, self.final, dirs_exist_ok=True)
        ledger = self.ledger([source])
        self.verify([source], ledger)
        (self.final / "two").unlink()
        self.verify([source], ledger, code=1)

    def test_hardlink_groups_must_survive_or_be_explicitly_separated(self):
        (self.source / "one").write_bytes(b"same")
        os.link(self.source / "one", self.source / "two")
        source = self.inventory()
        shutil.copytree(self.source, self.final, dirs_exist_ok=True)
        ledger = self.ledger([source])
        report = self.verify([source], ledger, code=1)
        self.assertIn("hardlink_mismatch", [r.get("status") for r in self.rows(report)])
        copied = self.inventory(self.final, "copy")
        self.run_audit("compare", "--source", source, "--copy", copied, "--mode", "path", code=1)
        rows = self.ledger_rows(ledger)
        for row in rows:
            if row["source_path"] != ".":
                row.update(hardlinks="separate", hardlink_reason="separate served metadata from backup")
        self.verify([source], self.ledger([source], rows))
        (self.final / "two").unlink()
        os.link(self.final / "one", self.final / "two")
        shutil.copystat(self.source, self.final)
        self.verify([source], ledger)

    def test_lexical_and_intermediate_symlink_escapes_never_verify_source(self):
        source, ledger = self.copied_fixture()
        for destination in ("../source/payload", str(self.source / "payload"), "folder/../payload"):
            rows = self.ledger_rows(ledger)
            rows[-1]["destination"] = destination
            self.verify([source], self.ledger([source], rows), code=2)
        (self.final / "link").symlink_to(self.source, target_is_directory=True)
        rows = self.ledger_rows(ledger)
        rows[-1]["destination"] = "link/payload"
        self.verify([source], self.ledger([source], rows), code=2)

    def test_symlink_target_and_staging_are_checked(self):
        (self.source / "link").symlink_to("missing")
        source = self.inventory()
        shutil.copytree(self.source, self.final, dirs_exist_ok=True, symlinks=True)
        ledger = self.ledger([source])
        self.verify([source], ledger)
        (self.final / "link").unlink()
        (self.final / "link").symlink_to("different")
        self.verify([source], ledger, code=1)
        (self.final / "99_tmp").mkdir()
        (self.final / "99_tmp/empty-unresolved").mkdir()
        report = self.verify([source], ledger, code=1)
        self.assertIn("unresolved_staging", [r.get("status") for r in self.rows(report)])

    def test_verify_io_failure_does_not_publish_completed_report(self):
        source, ledger = self.copied_fixture()
        with patch.object(audit.Tree, "inspect", side_effect=OSError(errno.EIO, "lost mount")):
            self.verify([source], ledger, code=2)

    def test_access_identity_and_writable_mount_are_rejected(self):
        source, ledger = self.copied_fixture()
        self.run_audit("access", "--root", self.final, "--ledger", ledger, code=2)
        with patch.object(audit.os, "getresuid", return_value=(1000,) * 3), \
             patch.object(audit.os, "getresgid", return_value=(1000,) * 3), \
             patch.object(audit.os, "getgroups", return_value=[]):
            self.run_audit("access", "--root", self.final, "--ledger", ledger, code=2)

    def test_served_link_resolution_rejects_escape_and_loop(self):
        (self.final / "dir").mkdir()
        (self.final / "dir/file").write_bytes(b"data")
        (self.final / "inside").symlink_to("dir/file")
        (self.final / "outside").symlink_to("../source")
        (self.final / "absolute").symlink_to(self.source)
        (self.final / "loop").symlink_to("loop")
        with audit.Tree(self.final) as tree:
            self.assertEqual(tree.resolve_link("inside"), "dir/file")
            for name in ("outside", "absolute", "loop"):
                with self.subTest(name=name), self.assertRaises(audit.AuditError):
                    tree.resolve_link(name)

    def test_repeated_directory_access_lists_once_and_detects_change(self):
        with audit.Index(self.evidence) as index, audit.opened(self.final, os.O_RDONLY | os.O_DIRECTORY) as fd:
            real_scandir = os.scandir
            with patch.object(audit.os, "scandir", wraps=real_scandir) as listing:
                for _ in range(20):
                    index.list_directory(fd, ".")
                self.assertEqual(listing.call_count, 1)
            (self.final / "unexpected-change").touch()
            with self.assertRaisesRegex(audit.AuditError, "directory changed"):
                index.list_directory(fd, ".")

    def test_blank_inventory_identity_is_rejected(self):
        self.inventory(source="", code=2)

    def test_three_way_collision_allows_only_one_keep(self):
        source, ledger = self.copied_fixture()
        b, c = self.inventory(source="B"), self.inventory(source="C")
        rows = self.ledger_rows(ledger) + self.ledger_rows(self.ledger([b])) + self.ledger_rows(self.ledger([c]))
        for row in rows:
            if row["source_path"] == ".":
                row["disposition"] = "merge"
            elif row["source_id"] == "A":
                row["disposition"] = "deduplicate"
        self.verify([source, b, c], self.ledger([source, b, c], rows), code=2)

    def test_access_search_permissions_and_symlink_kernel_semantics(self):
        # Run as an ordinary identity even when the VM unit suite runs as root.
        # These checks exercise actual VFS permissions, not os.access mocks.
        self.base.chmod(0o755)
        (self.final / "payload").write_bytes(b"data")
        (self.final / "private").mkdir(mode=0o000)
        (self.final / "empty-no-search").mkdir(mode=0o644)
        targets = {"blocked-parent": "private/../payload", "file-parent": "payload/../payload",
                   "file-dot": "payload/.", "file-slash": "payload/"}
        for name, target in targets.items():
            (self.final / name).symlink_to(target)
        code = """
import errno, importlib.util, os, sys, tempfile
spec = importlib.util.spec_from_file_location('audit', sys.argv[1])
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
with audit.Tree(sys.argv[2]) as tree:
    for name, error in [('blocked-parent', errno.EACCES), ('file-parent', errno.ENOTDIR),
                        ('file-dot', errno.ENOTDIR), ('file-slash', errno.ENOTDIR)]:
        try:
            tree.resolve_link(name)
        except OSError as exc:
            assert exc.errno == error, (name, exc)
        else:
            raise AssertionError('accepted unreadable symlink: ' + name)
    with tempfile.TemporaryDirectory() as temp, audit.Index(temp) as index:
        with tree.parent('empty-no-search') as (parent, name):
            with audit.opened(name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent) as fd:
                try:
                    index.list_directory(fd, 'empty-no-search')
                except PermissionError:
                    pass
                else:
                    raise AssertionError('accepted directory without search permission')
"""
        identity = {"user": 1000, "group": 1000, "extra_groups": []} if os.geteuid() == 0 else {}
        try:
            result = subprocess.run([sys.executable, "-B", "-c", code, str(SCRIPT), str(self.final)],
                                    capture_output=True, text=True, timeout=20, **identity)
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            (self.final / "private").chmod(0o755)
            (self.final / "empty-no-search").chmod(0o755)


if __name__ == "__main__":
    unittest.main()
