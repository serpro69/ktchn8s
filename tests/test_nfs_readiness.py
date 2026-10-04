"""Fast regressions for the probe's byte checks and controller teardown safety.

The real NFS/systemd tests remain in the nfs-lifecycle Molecule scenario.
"""

import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROLE = Path(__file__).resolve().parents[1] / "metal/roles/storage"
SPEC = importlib.util.spec_from_file_location("nfs_vms", ROLE / "molecule/nfs-lifecycle/vms.py")
vms = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vms)


@unittest.skipUnless(os.getuid() == 1000 and os.getgid() == 1000, "probe requires UID/GID 1000")
class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.probe("create", check=True)
        self.probe("promote", check=True)

    def probe(self, action, *, check=False):
        return subprocess.run(
            ["sh", str(ROLE / "files/nfs-readiness.sh"), action, str(self.root)],
            check=check, capture_output=True, text=True, timeout=70,
        )

    def test_exact_payload_and_delete(self):
        self.probe("read", check=True)
        self.probe("delete", check=True)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_extra_newline_is_a_byte_mismatch(self):
        (self.root / "library/promoted").write_bytes(b"nfs-readiness payload\n\n")
        self.assertNotEqual(self.probe("read").returncode, 0)

    def test_read_error_fails(self):
        (self.root / "library/promoted").chmod(0)
        self.assertNotEqual(self.probe("read").returncode, 0)


class VmTeardownTests(unittest.TestCase):
    def test_unrelated_pid_is_never_signalled_or_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)
            server = state / "nfs-server"
            server.mkdir()
            (server / "qemu.pid").write_text(str(os.getpid()))
            disk = server / "root.qcow2"
            disk.touch()
            with patch.object(vms.os, "kill") as kill:
                with self.assertRaisesRegex(RuntimeError, "Refusing to signal"):
                    vms.destroy(state, state / "inventory.json")
                kill.assert_not_called()
            self.assertTrue(disk.exists())

    def test_exiting_process_does_not_interrupt_remaining_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)
            for name in vms.GUESTS:
                directory = state / name
                directory.mkdir()
                (directory / "root.qcow2").touch()
                (directory / "serial.log").write_text("evidence")
            with patch.object(vms, "owned_pid", side_effect=[12345, None, None, None]):
                with patch.object(vms.os, "kill", side_effect=ProcessLookupError):
                    vms.destroy(state, state / "inventory.json")
            self.assertEqual(list(state.glob("*/root.qcow2")), [])
            self.assertEqual(len(list(state.glob("*/serial.log"))), 3)
            self.assertEqual((state / "inventory.json").read_text(), "[]\n")

    def test_live_listener_blocks_creation_even_with_port_reuse(self):
        with socket.socket() as listener, tempfile.TemporaryDirectory() as temp:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            with patch.object(vms, "GUESTS", {"nfs-server": port}), patch.object(vms.os, "access", return_value=True):
                with self.assertRaises(OSError):
                    vms.create(Path(temp), Path(temp) / "inventory.json")


if __name__ == "__main__":
    unittest.main()
