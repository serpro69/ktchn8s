#!/usr/bin/python3
"""Read-only admission of the complete storage inventory before any mkfs or mount."""

import json
from pathlib import Path
import re
import subprocess
import sys


def output(*args):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()


def filesystem(fields):
    if "PTTYPE" in fields or "PTUUID" in fields:
        raise ValueError("nested partition table")
    if fields.get("TYPE") == "ext4" and fields.get("USAGE") == "filesystem":
        return "ext4"
    if fields.get("PART_ENTRY_SCHEME") == "gpt" and all(
        key == "DEVNAME" or key.startswith("PART_ENTRY_") for key in fields
    ):
        return "blank"
    raise ValueError("unexpected or missing filesystem signature")


def inspect(data, parity, require_mounted=False):
    mounts = [line.split() for line in output("findmnt", "-rn", "-o", "MAJ:MIN,TARGET,FSTYPE,FSROOT").splitlines()]
    parents = set()
    branches = {}
    for role, drives in (("data", data), ("parity", parity)):
        for number, drive in enumerate(drives, 1):
            name = drive["id"]
            match = re.fullmatch(r"([a-zA-Z0-9_.:+-]+)-part([1-9][0-9]*)", name)
            if not match or match[1] in (".", ".."):
                raise ValueError(f"expected a partition by-id basename: {name}")
            device = Path("/dev/disk/by-id") / name
            target = Path(f"/mnt/{role}{number}")
            kind, parent, devno, size = output("lsblk", "-dnbr", "-o", "TYPE,PKNAME,MAJ:MIN,SIZE", device).split()
            whole = device.with_name(match[1]).resolve(strict=True)
            if kind != "part" or whole != Path("/dev") / parent or int(size) <= 0:
                raise ValueError(f"{device}: partition/parent mismatch")
            if output("lsblk", "-dnro", "TYPE", whole) != "disk" or whole in parents:
                raise ValueError(f"{device}: expected a distinct physical disk for each branch")
            if output("lsblk", "-nr", "-o", "TYPE", device).splitlines() != ["part"]:
                raise ValueError(f"{device}: partition has additional block-device consumers")
            parents.add(whole)
            if target.is_symlink() or target.resolve() != target:
                raise ValueError(f"symlink in mount path {target}")
            uses = [row for row in mounts if row[0] == devno or row[1] == str(target)]
            if uses and uses != [[devno, str(target), "ext4", "/"]]:
                raise ValueError(f"{device}: conflicting mount at {target} or elsewhere: {uses}")
            if not uses and (require_mounted or (target.exists() and any(target.iterdir()))):
                raise ValueError(f"{device}: missing mount or nonempty directory at {target}")
            try:
                signature = output("blkid", "--probe", "--output", "export", device)
                fields = dict(line.split("=", 1) for line in signature.splitlines())
                state = filesystem(fields)
            except ValueError as error:
                raise ValueError(f"{device}: {error}") from error
            if state == "blank" and (uses or drive.get("format_blank") is not True):
                raise ValueError(f"{device}: formatting requires an unmounted GPT partition and format_blank: true")
            partition_id = fields.get("PART_ENTRY_UUID")
            if not partition_id or fields.get("PART_ENTRY_NUMBER") != match[2]:
                raise ValueError(f"{device}: missing or conflicting partition identity")
            branches[str(target)] = dict(partition_id=partition_id, mounted=bool(uses), device=str(device), parent=str(whole), mount=str(target),
                                         state=state, bytes=int(size), role=role)
    for _, path, _, _ in mounts:
        if re.fullmatch(r"/mnt/(data|parity)[0-9]+", path) and path not in branches:
            raise ValueError(f"mounted branch missing from inventory: {path}")
    largest = max(b["bytes"] for b in branches.values() if b["role"] == "data")
    if any(b["bytes"] < largest for b in branches.values() if b["role"] == "parity"):
        raise ValueError("parity partition smaller than a data partition")
    return list(branches.values())


if __name__ == "__main__":
    try:
        data, parity = map(json.loads, sys.argv[1:3])
        print(json.dumps(inspect(data, parity, "--mounted" in sys.argv[3:])))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
