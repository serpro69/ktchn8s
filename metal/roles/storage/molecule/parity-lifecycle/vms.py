#!/usr/bin/env python3
"""Own one disposable parity QEMU guest; never read production inventory or disks.

Requires Linux/x86_64, KVM and the flake's QEMU/OpenSSH/xorriso. Guest SSH
uses QEMU user networking and binds only to loopback.
"""

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time


GUESTS = {"parity-server": 23101}
DISKS = ("data1", "data2", "parity1", "parity2")


def run(*args: str) -> None:
    subprocess.run(args, check=True, timeout=120)


def owned_pid(directory: Path) -> int | None:
    """Refuse to signal a reused PID or a VM outside this scenario directory."""
    pidfile = directory / "qemu.pid"
    if not pidfile.exists():
        return None
    pid = int(pidfile.read_text().strip())
    try:
        command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    except FileNotFoundError:
        return None
    if not command[0]:  # Exited daemon awaiting reaping.
        return None
    if os.fsencode(str(pidfile)) not in command or b"qemu-system-x86_64" not in command[0]:
        raise RuntimeError(f"Refusing to signal PID {pid}: not this fixture's QEMU")
    return pid


def destroy(state: Path, inventory: Path) -> None:
    for name in GUESTS:
        directory = state / name
        pid = owned_pid(directory)
        if pid is not None:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass  # It exited between the ownership check and the signal.
            deadline = time.monotonic() + 30
            while owned_pid(directory) is not None:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"QEMU {name} did not stop; disks retained")
                time.sleep(0.2)
        # Keep serial logs as failure evidence. Never remove arbitrary paths.
        for filename in ("root.qcow2", *(f"{disk}.qcow2" for disk in DISKS), "seed.iso", "qemu.pid"):
            (directory / filename).unlink(missing_ok=True)
    inventory.write_text("[]\n")


def create(state: Path, inventory: Path) -> None:
    if not os.access("/dev/kvm", os.R_OK | os.W_OK):
        raise RuntimeError("KVM is required; VM capability checks cannot be skipped")
    for port in GUESTS.values():
        with socket.socket() as probe:
            # A destroyed guest may leave TCP TIME_WAIT entries. Live listeners
            # still fail this bind; do not use SO_REUSEPORT.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))
    key = state / "id_ed25519"
    if not key.exists():
        run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key))
    public_key = key.with_suffix(".pub").read_text().strip()
    instances = []
    try:
        for index, (name, port) in enumerate(GUESTS.items(), start=1):
            directory = state / name
            directory.mkdir(mode=0o700, exist_ok=True)
            if (directory / "root.qcow2").exists():
                raise RuntimeError("Existing scratch disk: run molecule destroy first")
            (directory / "user-data").write_text(
                "#cloud-config\n"
                "disable_root: false\nssh_pwauth: false\n"
                "users:\n  - name: root\n    lock_passwd: true\n"
                f"    ssh_authorized_keys:\n      - {public_key}\n"
            )
            (directory / "meta-data").write_text(f"instance-id: {name}\nlocal-hostname: {name}\n")
            run("qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b",
                str(state / "base.qcow2"), str(directory / "root.qcow2"), "8G")
            run("xorriso", "-as", "mkisofs", "-quiet", "-output", str(directory / "seed.iso"),
                "-volid", "cidata", "-joliet", "-rock", str(directory / "user-data"),
                str(directory / "meta-data"))
            forward = f"user,id=net,hostfwd=tcp:127.0.0.1:{port}-:22"
            command = [
                "qemu-system-x86_64", "-enable-kvm", "-cpu", "host", "-smp", "2", "-m", "1024",
                "-display", "none", "-monitor", "none", "-daemonize",
                "-pidfile", str(directory / "qemu.pid"),
                "-serial", f"file:{directory}/serial.log",
                "-drive", f"file={directory}/root.qcow2,if=virtio,format=qcow2",
                "-drive", f"file={directory}/seed.iso,media=cdrom,readonly=on",
                "-netdev", forward, "-device", f"virtio-net-pci,netdev=net,mac=52:54:00:12:34:{index:02x}",
            ]
            for disk in DISKS:
                run("qemu-img", "create", "-f", "qcow2", str(directory / f"{disk}.qcow2"), "2G")
                command += ["-drive", f"file={directory}/{disk}.qcow2,if=virtio,format=qcow2"]
            run(*command)
            instances.append({"instance": name, "address": "127.0.0.1", "port": str(port),
                              "user": "root", "identity_file": str(key)})
        inventory.write_text(json.dumps(instances, indent=2) + "\n")
    except Exception:
        destroy(state, inventory)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "destroy"))
    parser.add_argument("state", type=Path)
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    state = args.state.resolve()
    if "," in str(state):
        raise ValueError("QEMU fixture path must not contain commas")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    {"create": create, "destroy": destroy}[args.action](state, args.inventory)


if __name__ == "__main__":
    main()
