"""Offline regressions for NAS provisioning. All devices and mounts are synthetic."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml
from jinja2 import Environment, StrictUndefined


ROLE = Path(__file__).resolve().parents[1] / "metal/roles/storage"


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROLE / "files" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


disks = helper("storage-disks")
smart = helper("smart-report")
backups = helper("content-backup")
parity = helper("parity-policy")


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.data = {"id": "virtio-synthetic-part1", "format_blank": True}
        self.mounts = "0:1 / overlay /"
        self.signature = "PART_ENTRY_SCHEME=gpt\nPART_ENTRY_UUID=fixture-uuid\nPART_ENTRY_NUMBER=1"
        self.parent = "vdb"
        self.probe_error = 0
        original_resolve = Path.resolve

        def resolve(path, *args, **kwargs):
            if path.parent == Path("/dev/disk/by-id"):
                return Path("/dev/vdb")
            return original_resolve(path, *args, **kwargs)

        mock_path = patch.object(Path, "resolve", resolve)
        mock_path.start()
        self.addCleanup(mock_path.stop)
        commands = patch.object(disks, "output", side_effect=self.output)
        commands.start()
        self.addCleanup(commands.stop)

    def output(self, *args):
        if args[0] == "findmnt":
            return self.mounts
        if args[0] == "blkid":
            if self.probe_error:
                raise subprocess.CalledProcessError(self.probe_error, args)
            return self.signature
        if args[0] == "lsblk" and "TYPE,PKNAME,MAJ:MIN,SIZE" in args:
            return f"part {self.parent} 8:17 1024"
        if args[:3] == ("lsblk", "-dnro", "TYPE"):
            return "disk"
        if args[:4] == ("lsblk", "-nr", "-o", "TYPE"):
            return "part"
        self.fail(str(args))

    def test_blank_then_repeat_requires_real_ext4_mount(self):
        self.assertEqual(disks.inspect([self.data], [])[0]["state"], "blank")
        self.signature += "\nTYPE=ext4\nUSAGE=filesystem"
        self.mounts += "\n8:17 /mnt/data1 ext4 /"
        result, = disks.inspect([{"id": self.data["id"]}], [], require_mounted=True)
        self.assertEqual((result["state"], result["parent"], result["mounted"]), ("ext4", "/dev/vdb", True))

    def test_blank_without_boolean_authorization_is_rejected(self):
        for value in [None, False, "true", 1]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "format_blank"):
                disks.inspect([dict(self.data, format_blank=value)], [])

    def test_probe_failures_are_never_blank(self):
        for self.probe_error in [2, 4, 8]:
            with self.subTest(rc=self.probe_error), self.assertRaises(subprocess.CalledProcessError):
                disks.inspect([self.data], [])

    def test_unexpected_and_empty_signatures_are_rejected(self):
        for self.signature in ["", "TYPE=xfs", "PTTYPE=dos\nTYPE=ext4", "TYPE=swap", "TYPE=LVM2_member"]:
            with self.subTest(sig=self.signature), self.assertRaises(ValueError):
                disks.inspect([self.data], [])

    def test_reject_other_mount_and_wrong_backing(self):
        for self.mounts in ["8:19 /mnt/data1 ext4 /", "8:17 /mnt/other ext4 /",
                            "8:17 /mnt/data1 ext4 /subdir", "8:19 /mnt/parity2 ext4 /"]:
            with self.subTest(mount=self.mounts), self.assertRaises(ValueError):
                disks.inspect([self.data], [])

    def test_duplicate_data_and_parity_aliases_and_parent_mismatch(self):
        for data, parity_drives in [([self.data, self.data], []), ([self.data], [dict(self.data, id="wwn-alias-part1")])]:
            with self.assertRaisesRegex(ValueError, "distinct physical disk"):
                disks.inspect(data, parity_drives)
        self.parent = "vdc"
        with self.assertRaisesRegex(ValueError, "parent mismatch"):
            disks.inspect([self.data], [])


class ParityPolicyTests(unittest.TestCase):
    def test_pending_survives_partial_initialization_and_changed_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "snapraid.conf"
            content = root / "snapraid.content"
            level = root / "snapraid.parity"
            desired = f"parity {level}\ncontent {content}\ndata d1 /mnt/data1\n"
            branch = dict(device="/dev/test", state="ext4", partition_id="one", mounted=True, mount="/mnt/data1")
            def decision():
                return parity.policy([branch], desired, [False, False], config, root)
            self.assertEqual(decision(), "pending")
            config.write_text(desired)
            self.assertEqual(decision(), "pending")
            level.write_bytes(b"parity")
            content.write_bytes(b"content")
            # Existing parity/content, including partial files, never authorizes timer activation.
            self.assertEqual(decision(), "pending")
            self.assertEqual(parity.policy([branch], desired, [False, False], config, root, adopt=True), "adopt")
            for running, expected in [(False, "pending"), (True, "legacy")]:
                with patch.object(parity, "already_scheduled", return_value=running):
                    self.assertEqual(parity.policy([branch], desired, [True, True], config, root), expected)
            (root / "snapraid-layout.pending").write_text('{"branches":[]}')
            self.assertEqual(decision(), "pending")
            self.assertEqual(parity.policy([branch], desired, [False, False], config, root, adopt=True), "pending")
            (root / "snapraid-layout.pending").rename(root / "snapraid-layout.accepted")
            self.assertEqual(decision(), "pending")
            (root / "snapraid-layout.accepted").write_text(json.dumps({"branches": [["/dev/test", "one", "/mnt/data1"]]}))
            self.assertEqual(decision(), "accepted")
            self.assertEqual(parity.policy([branch], desired + "2-parity /mnt/parity2/file\n", [False, False], config, root), "pending")


class HealthTests(unittest.TestCase):
    def test_mixed_healthy_failing_and_unreadable_reports_keep_identity(self):
        def observe(device, rc, stdout):
            return smart.report(device, subprocess.CompletedProcess([], rc, stdout=stdout))
        result = [observe("/dev/a", 0, '{"smart_status":{"passed":true}}'),
                  observe("/dev/b", 8, '{"smart_status":{"passed":false},"temperature":{"current":65}}'),
                  observe("/dev/c", 2, "Device unavailable")]
        self.assertEqual([r["device"] for r in result if not r["overall_health"]], ["/dev/b", "/dev/c"])
        self.assertEqual(result[1]["temperature"], 65)
        self.assertEqual(result[2]["exit_status"], 2)


class BackupTests(unittest.TestCase):
    def test_distinct_copies_retention_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = [root / branch / "snapraid.content" for branch in ("data1", "var")]
            for n, source in enumerate(files):
                source.parent.mkdir()
                source.write_text(f"content copy {n}")
            config = root / "snapraid.conf"
            config.write_text("".join(f"content {source}\n" for source in files))
            directory = root / "backups"
            directory.mkdir()
            old, second, last = [backups.backup(config, directory, 2) for _ in range(3)]
            self.assertFalse(old.exists())
            self.assertTrue(second.is_dir())
            for source in files:
                self.assertEqual((last / source.relative_to("/")).read_bytes(), source.read_bytes())
            files[1].unlink()
            with self.assertRaisesRegex(ValueError, "invalid content source"):
                backups.backup(config, directory, 2)
            self.assertEqual(set(directory.iterdir()), {second, last})


class InstallerTests(unittest.TestCase):
    def test_release_asset_names_match_pinned_checksums(self):
        variables = yaml.safe_load((ROLE / "vars/main.yml").read_text())
        env = Environment(undefined=StrictUndefined)
        deb = env.from_string(variables["mergerfs_pkg_deb"])
        rpm = env.from_string(variables["mergerfs_pkg_rpm"])
        for release in ["bookworm", "trixie"]:
            name = deb.render(**variables, ansible_distribution="Debian", ansible_distribution_release=release)
            self.assertRegex(variables["mergerfs_checksums"][name], "^sha256:[a-f0-9]{64}$")
        for release in [40, 41, 42, 43]:
            for arch in ["x86_64", "aarch64"]:
                name = rpm.render(**variables, ansible_distribution_major_version=release, ansible_architecture=arch)
                self.assertRegex(variables["mergerfs_checksums"][name], "^sha256:[a-f0-9]{64}$")


class ProvisionVmTests(unittest.TestCase):
    def test_create_refuses_existing_overlay_without_removing_it(self):
        spec = importlib.util.spec_from_file_location("storage_vms", ROLE / "molecule/parity-lifecycle/vms.py")
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        with tempfile.TemporaryDirectory() as tmp, patch.object(driver.os, "access", return_value=True):
            state = Path(tmp)
            disk = state / next(iter(driver.GUESTS)) / "root.qcow2"
            disk.parent.mkdir()
            disk.write_bytes(b"retained guest state")
            with self.assertRaisesRegex(RuntimeError, "Existing scratch disk"):
                driver.create(state, state / "instance.json")
            self.assertEqual(disk.read_bytes(), b"retained guest state")


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires the repository Ansible toolchain")
class DiskProbeTransportTests(unittest.TestCase):
    def test_accepts_separate_diagnostics_but_rejects_incomplete_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            role = root / "roles/storage"
            (role / "tasks").mkdir(parents=True)
            (role / "files").mkdir()
            shutil.copyfile(ROLE / "tasks/probe_disks.yml", role / "tasks/main.yml")
            # Exercise the real Ansible task without access to a block device.
            (role / "files/storage-disks.py").write_text(
                "import json, sys\n"
                "data, parity = map(json.loads, sys.argv[1:])\n"
                "print('disk diagnostic', file=sys.stderr)\n"
                "print(json.dumps([{'device': d['id']} for d in data + parity]))\n"
            )
            play = root / "probe.yml"
            play.write_text(yaml.safe_dump([{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": {"data_drives": [{"id": "disk-a"}], "parity_drives": [],
                         "data_devices": ["disk-a"], "parity_devices": []},
                "roles": ["storage"],
                "tasks": [{"ansible.builtin.assert": {"that": [
                    "storage_disk_probe.stderr == 'disk diagnostic'",
                    "(storage_disk_probe.stdout | from_json)[0].device == 'disk-a'",
                ]}}],
            }]))
            cmd = ["ansible-playbook", "-i", "localhost,", str(play)]
            env = dict(os.environ, ANSIBLE_ROLES_PATH=str(root / "roles"), ANSIBLE_NOCOLOR="1",
                       ANSIBLE_LOCAL_TEMP=str(root / "local"), ANSIBLE_REMOTE_TEMP=str(root / "remote"))
            passed = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            failed = subprocess.run(cmd + ["-e", '{"data_devices":["disk-a","disk-b"]}'],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("Read partition identities", failed.stdout)
            self.assertIn("disk diagnostic", failed.stdout + failed.stderr)


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires the repository Ansible toolchain")
class FirewallCheckModeTests(unittest.TestCase):
    def test_ssh_allow_obeys_effective_check_mode(self):
        policy = yaml.safe_load((ROLE / "tasks/ufw_policy.yml").read_text())
        tasks = [task for task in policy if task.get("register") in {"storage_ssh_preview", "storage_ssh_apply"}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ufw = root / "ufw"
            ufw.write_text("#!/bin/sh\n"
                           "if test \"$1\" = --dry-run; then shift; else touch \"$APPLIED\"; fi\n"
                           'test "$*" = "prepend allow from 10.0.2.2/32 to any port 22 proto tcp comment NAS SSH" || exit 1\n'
                           "echo 'Rules updated'\n")
            ufw.chmod(0o700)
            for cli_check, block_check in [(False, True), (True, False)]:
                with self.subTest(cli_check=cli_check, block_check=block_check):
                    applied = root / f"applied-{cli_check}"
                    play = root / "firewall.yml"
                    play.write_text(yaml.safe_dump([{
                        "hosts": "localhost", "connection": "local", "gather_facts": False,
                        "environment": {"PATH": f"{root}:{os.environ['PATH']}", "APPLIED": str(applied)},
                        "vars": {"storage_ssh_connection": {"stdout": "10.0.2.2 40000 10.0.2.15 22"},
                                 "firewall_allowed_networks": ["10.0.2.2/32"]},
                        "tasks": [{"block": tasks, "check_mode": block_check}],
                    }]))
                    args = ["ansible-playbook", "-i", "localhost,", str(play)]
                    if cli_check:
                        args.append("--check")
                    result = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=30,
                                            env=dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root / "local"),
                                                     ANSIBLE_REMOTE_TEMP=str(root / "remote")))
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(applied.exists(), not block_check)


if __name__ == "__main__":
    unittest.main()
