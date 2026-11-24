"""Offline public-command and admission tests; no host or Kubernetes execution.

Make invokes a recording executable. Ansible executes only the entry point's
first assertion, extracted into a disposable play with a synthetic inventory.
The rest of the operator play is deliberately never executed by this suite.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    "storage-validate", "storage-acceptance",
    "storage-audit-acceptance", "storage-client-setup",
)


@unittest.skipUnless(shutil.which("make"), "requires make")
class CommandTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.temp = Path(directory.name)
        self.record = self.temp / "invocation.json"
        recorder = self.temp / "ansible-playbook"
        recorder.write_text(
            f"#!{sys.executable}\n"
            "import json, os, pathlib, sys\n"
            "pathlib.Path(os.environ['PROBE_OUTPUT']).write_text(json.dumps(\n"
            "    {'args': sys.argv[1:], 'kubeconfig': os.environ.get('KUBECONFIG')}))\n"
        )
        recorder.chmod(0o755)
        # Fail if a check target gains provisioning/tool-install prerequisites.
        for name in ("ansible-galaxy", "ssh", "scp", "ssh-keygen"):
            script = self.temp / name
            script.write_text("#!/bin/sh\nexit 93\n")
            script.chmod(0o755)
        (self.temp / "jq").symlink_to("/bin/true")
        self.env = os.environ | {
            "PATH": str(self.temp) + os.pathsep + os.environ.get("PATH", ""),
            "PROBE_OUTPUT": str(self.record),
            "KUBECONFIG": str(self.temp / "selected-cluster.yaml"),
        }
        self.env.pop("MAKEFLAGS", None)

    def invoke(self, target, *arguments):
        return subprocess.run(
            ["make", "--always-make", "--no-print-directory", "-C", str(ROOT / "metal"), target,
             "NO_TERM=true", "ANSIBLE_VERBOSITY=0", *arguments],
            env=self.env, capture_output=True, text=True, timeout=15,
        )

    def test_each_check_routes_only_to_its_public_play_and_preserves_selection(self):
        for target in TARGETS:
            with self.subTest(target=target):
                result = self.invoke(target, "ANSIBLE_TARGETS=nas-test",
                                     "KUBECONFIG=" + self.env["KUBECONFIG"],
                                     "ANSIBLE_ARGS=-e @/tmp/synthetic-vars.yml")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                call = json.loads(self.record.read_text())
                self.assertEqual(call["args"], [
                    "-i", "inventory.sh", "--limit", "nas-test",
                    "-e", "@/tmp/synthetic-vars.yml", target + ".yml",
                ])
                self.assertEqual(call["kubeconfig"], self.env["KUBECONFIG"])
                self.record.unlink()

    def test_default_cluster_selection_ignores_unrelated_exported_config(self):
        for target in TARGETS:
            with self.subTest(target=target):
                result = self.invoke(target, "ANSIBLE_TARGETS=nas-test")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                call = json.loads(self.record.read_text())
                self.assertEqual(call["kubeconfig"], str(ROOT / "metal/kubeconfig.yaml"))
                self.record.unlink()

    def test_check_targets_reject_tag_filters_before_invocation(self):
        for target in TARGETS:
            with self.subTest(target=target):
                result = self.invoke(target, "ANSIBLE_TARGETS=nas-test", "ANSIBLE_TAGS=unrelated")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ANSIBLE_TAGS is unsupported", result.stderr)
                self.assertFalse(self.record.exists())

    def test_check_targets_require_explicit_nas_selection(self):
        for target in TARGETS:
            with self.subTest(target=target):
                result = self.invoke(target, "ANSIBLE_TARGETS=")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("select exactly one NAS", result.stderr)
                self.assertFalse(self.record.exists())


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires Ansible in the existing toolchain")
class AdmissionTests(unittest.TestCase):
    def run_guard(self, source, *, variables=None, limit="nas-one", check=False):
        tasks = yaml.safe_load((ROOT / source).read_text())
        first = tasks[0]
        if "hosts" in first:  # migration-audit admission lives directly in its play
            first = first["tasks"][0]
        self.assertIn("ansible.builtin.assert", first,
                      "Admission must precede operational tasks")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            inventory = temp / "inventory.ini"
            inventory.write_text(
                "[nas]\nnas-one ansible_connection=local\nnas-two ansible_connection=local\n"
                "[k3s]\nnode-one ansible_connection=local\nnode-two ansible_connection=local\n"
            )
            play = temp / "guard.yml"
            play.write_text(yaml.safe_dump([{
                "name": "Offline admission only", "hosts": "nas", "gather_facts": False,
                "vars": {"data_drives": [{"id": "synthetic"}], **(variables or {})},
                "tasks": [first],
            }]))
            config = temp / "ansible.cfg"
            config.write_text("[defaults]\nretry_files_enabled = false\n")
            env = os.environ | {
                "ANSIBLE_CONFIG": str(config), "ANSIBLE_LOCAL_TEMP": str(temp / "ansible-tmp"),
                "ANSIBLE_NOCOLOR": "1",
            }
            args = ["ansible-playbook", "-i", str(inventory), str(play), "--limit", limit]
            if check:
                args.append("--check")
            return subprocess.run(args, cwd=temp, env=env, capture_output=True,
                                  text=True, timeout=20)

    def assert_guard(self, source, succeeds, **kwargs):
        result = self.run_guard(source, **kwargs)
        output = result.stdout + result.stderr
        if succeeds:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn('"evaluated_to": false', output)

    def test_basic_validation_allows_one_node_but_rejects_check_mode_and_multiple_nas(self):
        source = "metal/roles/nfs_validation/tasks/main.yml"
        self.assert_guard(source, True)
        self.assert_guard(source, True, variables={"nfs_readiness_client_nodes": ["node-one", "node-one"]})
        self.assert_guard(source, False, check=True)
        self.assert_guard(source, False, limit="nas")
        self.assert_guard(source, False, variables={"data_drives": []})
        self.assert_guard(source, False, variables={"nfs_readiness_client_nodes": ["node-one"]})

    def test_lifecycle_requires_maintenance_and_two_distinct_inventory_clients(self):
        source = "metal/roles/nfs_validation/tasks/live_acceptance.yml"
        valid = {"nfs_lifecycle_clients": ["node-one", "node-two"], "nfs_lifecycle_maintenance": True}
        self.assert_guard(source, True, variables=valid)
        for override in ({"nfs_lifecycle_maintenance": False},
                         {"nfs_lifecycle_clients": ["node-one"]},
                         {"nfs_lifecycle_clients": ["node-one", "node-one"]},
                         {"nfs_lifecycle_clients": ["nas-one", "node-one"]},
                         {"nfs_lifecycle_clients": ["missing", "node-one"]}):
            with self.subTest(override=override):
                self.assert_guard(source, False, variables=valid | override)
        self.assert_guard(source, False, variables=valid, check=True)
        self.assert_guard(source, False, variables=valid, limit="nas")

    def test_audit_admission_is_independent_of_kubernetes_and_maintenance(self):
        source = "metal/storage-audit-acceptance.yml"
        self.assert_guard(source, True)
        self.assert_guard(source, False, check=True)
        self.assert_guard(source, False, limit="nas")


if __name__ == "__main__":
    unittest.main()
