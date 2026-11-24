#!/usr/bin/python3
"""Keep a new or changed array pending until the operator accepts its scrub."""

import json
from pathlib import Path
import subprocess
import sys


def topology(config):
    directives = []
    for line in config.splitlines():
        fields = line.split()
        if fields and (fields[0] in ("data", "content", "parity") or fields[0].endswith("-parity")):
            directives.append(fields)
    return directives


def already_scheduled(unit):
    result = subprocess.run(["systemctl", "show", unit, "-p", "UnitFileState", "-p", "ActiveState"],
                            check=True, capture_output=True, text=True)
    return {"UnitFileState=enabled", "ActiveState=active"} <= set(result.stdout.splitlines())


def policy(branches, desired, timers, config=Path("/etc/snapraid.conf"), state=Path("/var/lib"), adopt=False):
    if (state / "snapraid-layout.pending").exists() or not config.is_file():
        return "pending"
    current = topology(config.read_text())
    if current != topology(desired) or not all(b["mounted"] and b["state"] == "ext4" for b in branches):
        return "pending"
    accepted = state / "snapraid-layout.accepted"
    identities = [[b["device"], b["partition_id"], b["mount"]] for b in branches]
    if accepted.exists() and json.loads(accepted.read_text())["branches"] != identities:
        return "pending"
    # Adopt pre-existing mounted arrays such as the completed Task 8 installation.
    # Never adopt partial state left by a transition through either public play.
    for fields in current:
        if fields[0] == "data":
            continue
        path = Path(fields[1])
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            return "pending"
    if accepted.exists():
        return "accepted"
    if adopt is True:
        return "adopt"
    # Preserve a legacy operator's running jobs. File existence alone must
    # never turn a paused/partial array into an accepted or scheduled array.
    requested = [unit for enabled, unit in zip(timers, ("snapraid-runner.timer", "snapraid-scrub.timer")) if enabled]
    return "legacy" if requested and all(already_scheduled(unit) for unit in requested) else "pending"


if __name__ == "__main__":
    print(policy(json.loads(sys.argv[1]), sys.argv[2], json.loads(sys.argv[3]), adopt=json.loads(sys.argv[4])))
