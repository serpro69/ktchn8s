"""Regression checks for failure evidence; real service behavior lives in Molecule."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


HELPER = Path(__file__).resolve().parents[1] / "metal/roles/storage/molecule/parity-lifecycle/job.py"
SPEC = importlib.util.spec_from_file_location("parity_fixture_job", HELPER)
job = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(job)


class EvidenceTests(unittest.TestCase):
    def test_flush_failure_keeps_status_and_available_journal(self):
        def run(*args):
            if args == ("journalctl", "--sync"):
                raise subprocess.CalledProcessError(1, args)
            return '{"_SYSTEMD_INVOCATION_ID": "test-id"}\n'

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(job, "EVIDENCE", root), patch.object(job, "run", side_effect=run), \
                    patch.object(job, "status", return_value={"Result": "exit-code", "ExecMainStatus": "42"}):
                ids, errors = job.record_evidence("failed", "cursor", {})
            saved = json.loads((root / "failed.json").read_text())
            self.assertEqual(ids, {"test-id"})
            self.assertEqual(saved["final_status"]["ExecMainStatus"], "42")
            self.assertIn("Journal flush:", errors[0])
            self.assertEqual(len(errors), 1)
            self.assertIn("test-id", (root / "failed.log").read_text())

    def test_journal_read_failure_still_publishes_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(job, "EVIDENCE", root), patch.object(job, "status", return_value={"Result": "signal"}), \
                    patch.object(job, "run", side_effect=["", subprocess.TimeoutExpired("journalctl", 120)]):
                ids, errors = job.record_evidence("interrupted", "cursor", {})
            saved = json.loads((root / "interrupted.json").read_text())
            self.assertEqual(ids, set())
            self.assertEqual(saved["final_status"]["Result"], "signal")
            self.assertIn("Journal capture:", errors[0])
            self.assertEqual(saved["evidence_errors"], errors)

    def test_unwritable_evidence_is_reported_without_raising(self):
        with tempfile.TemporaryDirectory() as directory:
            not_a_directory = Path(directory) / "occupied"
            not_a_directory.write_text("existing file\n")
            with patch.object(job, "EVIDENCE", not_a_directory), patch.object(job, "status", return_value={}), \
                    patch.object(job, "run", return_value=""):
                ids, errors = job.record_evidence("failed", "cursor", {})
            self.assertEqual(ids, set())
            self.assertEqual(len(errors), 2)
            self.assertIn("Journal capture:", errors[0])
            self.assertIn("JSON capture:", errors[1])
            self.assertEqual(not_a_directory.read_text(), "existing file\n")

    def test_original_job_error_survives_evidence_failure(self):
        original = subprocess.CalledProcessError(1, ["sha256sum", "--check"])

        def run(*args):
            if args[0] == "sha256sum":
                raise original
            if "--show-cursor" in args:
                return "-- cursor: test-cursor\n"
            raise subprocess.TimeoutExpired(args, 120)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(job, "EVIDENCE", root), patch.object(job, "run", side_effect=run), \
                    patch.object(job, "status", side_effect=[
                        {"ExecMainStartTimestampMonotonic": "0", "ActiveState": "inactive"},
                        OSError("status unavailable"),
                    ]):
                with self.assertRaises(subprocess.CalledProcessError) as caught:
                    job.job("initial", "success")
            self.assertIs(caught.exception, original)
            saved = json.loads((root / "initial.json").read_text())
            self.assertEqual(len(saved["evidence_errors"]), 3)


if __name__ == "__main__":
    unittest.main()
