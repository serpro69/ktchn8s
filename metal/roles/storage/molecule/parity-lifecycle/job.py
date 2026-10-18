#!/usr/bin/python3
"""Start one real guest unit invocation and preserve its result and journal."""

import argparse
import json
from pathlib import Path
import subprocess
import time


UNIT = "snapraid-initial-sync.service"
EVIDENCE = Path("/var/log/parity-fixture")


def run(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=120).stdout


def status() -> dict[str, str]:
    return dict(line.split("=", 1) for line in run(
        "systemctl", "show", UNIT,
        "--property=ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,"
        "ExecMainStartTimestampMonotonic,MainPID,InvocationID,TimeoutStartUSec,ExecStart",
    ).splitlines())


def record_evidence(label: str, cursor: str, evidence: dict[str, object]) -> tuple[set[str], list[str]]:
    """Preserve each available record without masking an earlier job failure."""
    errors = []
    journal_ids = set()
    try:
        evidence["final_status"] = status()
    except (OSError, subprocess.SubprocessError) as error:
        errors.append(f"Final status: {error}")
    try:
        run("journalctl", "--sync")
    except (OSError, subprocess.SubprocessError) as error:
        errors.append(f"Journal flush: {error}")
    try:
        journal = run("journalctl", "-u", UNIT, "--after-cursor", cursor, "--no-pager", "-o", "json")
        (EVIDENCE / f"{label}.log").write_text(journal)
        journal_ids = {entry["_SYSTEMD_INVOCATION_ID"] for line in journal.splitlines()
                       if "_SYSTEMD_INVOCATION_ID" in (entry := json.loads(line))}
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        errors.append(f"Journal capture: {error}")
    evidence["journal_invocation_ids"] = sorted(journal_ids)
    evidence["evidence_errors"] = errors
    try:
        (EVIDENCE / f"{label}.json").write_text(json.dumps(evidence, indent=2) + "\n")
    except OSError as error:
        errors.append(f"JSON capture: {error}")
    return journal_ids, errors


def job(label: str, outcome: str) -> None:
    before = status()
    previous = before["ExecMainStartTimestampMonotonic"]
    cursor = run("journalctl", "--show-cursor", "-n", "0").split("-- cursor: ", 1)[1].strip()
    evidence: dict[str, object] = {"label": label, "expected": outcome, "previous_start": previous}
    interrupted = False
    invocation = ""
    try:
        evidence["payloads_before"] = run("sha256sum", "--check", str(EVIDENCE / "payloads.sha256.log"))
        if before["ActiveState"] == "failed":
            run("systemctl", "reset-failed", UNIT)
        run("systemctl", "restart", "--no-block", UNIT)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            state = status()
            started = state["ExecMainStartTimestampMonotonic"] not in ("0", previous)
            invocation = state["InvocationID"] or invocation
            if started and state["SubState"] in ("exited", "failed", "dead"):
                break
            if outcome == "interrupt" and not interrupted and int(state["MainPID"]) > 0:
                pid = state["MainPID"]
                try:
                    io = dict(line.split(": ", 1) for line in Path(f"/proc/{pid}/io").read_text().splitlines())
                    command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
                except FileNotFoundError:
                    continue  # Fail below if it completed before interruption.
                if int(io["write_bytes"]) > 0:
                    if command[:3] != [b"/usr/local/bin/snapraid", b"--force-full", b"sync"]:
                        raise AssertionError(f"Not the real full-sync process: {command!r}")
                    evidence["interrupted_pid"] = pid
                    evidence["interrupted_write_bytes"] = int(io["write_bytes"])
                    run("systemctl", "kill", "--kill-who=main", "--signal=SIGKILL", UNIT)
                    interrupted = True
            time.sleep(0.05)
        else:
            raise TimeoutError(f"Fixture job {label} did not finish within 120 seconds")
        evidence["status"] = state
        if state["TimeoutStartUSec"] != "infinity":
            raise AssertionError(f"Bootstrap timeout is bounded: {state}")
        if outcome == "success":
            expected = ("active", "success", "1", "0")
        elif outcome == "failure":
            expected = ("failed", "exit-code", "1", "42")
        else:
            if not interrupted:
                raise AssertionError("Sync finished before interruption; test did not exercise cancellation")
            expected = ("failed", "signal", "2", "9")
        actual = tuple(state[key] for key in ("ActiveState", "Result", "ExecMainCode", "ExecMainStatus"))
        if actual != expected:
            raise AssertionError(f"Job {label}: expected {expected}, got {actual}")
        evidence["payloads_after"] = run("sha256sum", "--check", str(EVIDENCE / "payloads.sha256.log"))
    finally:
        # Keep evidence even when an assertion or invocation fails.
        evidence["invocation_id"] = invocation
        journal_ids, errors = record_evidence(label, cursor, evidence)
    if errors:
        raise AssertionError(f"Incomplete invocation evidence: {errors}")
    if len(journal_ids) != 1 or (invocation and invocation not in journal_ids):
        raise AssertionError(f"Missing or mixed invocation journal: {journal_ids}")
    if invocation == before["InvocationID"]:
        raise AssertionError("No new invocation ID; a previous run cannot satisfy this job")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label", choices=("initial", "expanded", "interrupted", "retried", "failed", "recovered"))
    parser.add_argument("outcome", choices=("success", "failure", "interrupt"))
    args = parser.parse_args()
    job(args.label, args.outcome)
