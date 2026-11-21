#!/usr/bin/python3
"""Inspect the physical disks, retaining failures alongside successful SMART reads."""

import json
import subprocess
import sys


def report(device, result):
    try:
        data = json.loads(result.stdout)
    except (ValueError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    attributes = {row["id"]: row["raw"]["value"] for row in data.get("ata_smart_attributes", {}).get("table", [])}
    return dict(device=device, tool="smartctl", exit_status=result.returncode,
                overall_health=result.returncode == 0 and data.get("smart_status", {}).get("passed") is True,
                temperature=data.get("temperature", {}).get("current", -1),
                reallocated_sectors=attributes.get(5, 0), pending_sectors=attributes.get(197, 0),
                uncorrectable_errors=attributes.get(187, 0), power_on_hours=attributes.get(9, "N/A"),
                model=data.get("model_name", "Unknown"), serial=data.get("serial_number", "Unknown"))


if __name__ == "__main__":
    entries = []
    for device in sys.argv[1:]:
        result = subprocess.run(["smartctl", "-H", "-A", "--json=c", device], capture_output=True, text=True)
        entries.append(report(device, result))
    print(json.dumps(entries))
