"""Seed/repair/assert only the disposable VM migration-audit fixture."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


SPEC = importlib.util.spec_from_file_location("nas_audit", "/tmp/nas-audit/scripts/nas-migration-audit.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
SOURCE = Path("/var/tmp/migration-audit-source")
FINAL = Path("/mnt/storage/99_tmp/migration-audit")
EVIDENCE = Path("/var/tmp/migration-audit-evidence")
PRIVATE = "30_media/30.01_movies/private"


def rows(path):
    with open(path) as stream:
        return [json.loads(line) for line in stream]


def run(*args, expected=0):
    result = audit.main([*map(str, args), "--run-id", "molecule-access"])
    if result != expected:
        raise RuntimeError(f"audit returned {result}, expected {expected}: {args}")


def seed():
    SOURCE.mkdir()
    EVIDENCE.mkdir(mode=0o755)
    private = SOURCE / PRIVATE
    private.mkdir(parents=True)
    (private / "payload").write_bytes(b"migration access fixture\n")
    os.link(private / "payload", private / "linked-payload")
    for directory, _, files in os.walk(SOURCE):
        os.chown(directory, 1000, 1000)
        os.chmod(directory, 0o775)
        for name in files:
            os.chown(Path(directory) / name, 1234, 1234)
            os.chmod(Path(directory) / name, 0o600)
    os.chown(private, 1234, 1234)
    os.chmod(private, 0o700)
    subprocess.run(["setfacl", "-m", "u:1000:---", str(private)], check=True)
    os.setxattr(private / "payload", "user.fixture", b"preserve this xattr")
    inventory = EVIDENCE / "source.jsonl"
    run("inventory", "--root", SOURCE, "--source-id", "fixture", "--disk-id", "vm-root",
        "--output", inventory)
    FINAL.mkdir()
    subprocess.run(["cp", "-a", str(SOURCE) + "/.", str(FINAL)], check=True)
    digest = hashlib.sha256(inventory.read_bytes()).hexdigest()
    with audit.Generation(EVIDENCE / "ledger.jsonl", "ledger", "molecule-access",
                          inventories={"fixture": digest}) as out:
        for entry in rows(inventory)[1:-1]:
            expected = audit.signature(entry)
            changes = {}
            if entry["path"] == PRIVATE or entry["path"].startswith(PRIVATE + "/"):
                expected.update(uid=1000, gid=1000, mode=0o775 if entry["type"] == "directory" else 0o644)
                expected["xattrs"] = {k: v for k, v in expected["xattrs"].items() if not k.startswith("system.posix_acl_")}
                for key in audit.META:
                    if entry[key] != expected[key]:
                        changes[key] = {"before": entry[key], "expected": expected[key],
                                        "reason": "declared UID-1000 served-media repair"}
            out.add({"record": "disposition", "source_id": "fixture", "source_path": entry["path"],
                     "disposition": "keep", "destination": entry["path"], "expected": expected,
                     "transformations": changes, "reason": "retain fixture with explicit access repair"})
        out.finish()
    run("verify", "--root", FINAL, "--identity", "mergerfs", "--inventory", inventory,
        "--ledger", EVIDENCE / "ledger.jsonl", "--output", EVIDENCE / "verify-before.jsonl", expected=1)


def repair():
    private = FINAL / PRIVATE
    subprocess.run(["setfacl", "-b", str(private)], check=True)
    for path in (private, private / "payload", private / "linked-payload"):
        os.chown(path, 1000, 1000)
        os.chmod(path, 0o775 if path.is_dir() else 0o644)
    run("verify", "--root", FINAL, "--identity", "mergerfs", "--inventory", EVIDENCE / "source.jsonl",
        "--ledger", EVIDENCE / "ledger.jsonl", "--output", EVIDENCE / "verify-after.jsonl")


def check():
    before, after = rows(EVIDENCE / "access-before.jsonl"), rows(EVIDENCE / "access-after.jsonl")
    verified = rows(EVIDENCE / "verify-after.jsonl")
    assert before[-1]["status"] == "differences" and before[-1]["failures"] >= 1
    assert any(r.get("status") == "denied_or_unresolved" and r.get("errno") == 13 for r in before)
    assert after[-1]["status"] == verified[-1]["status"] == "accepted"
    assert before[0]["ledger_sha256"] == after[0]["ledger_sha256"] == verified[0]["ledger_sha256"]
    assert before[0]["uid"] == after[0]["uid"] == 1000
    assert before[0]["gid"] == after[0]["gid"] == 1000
    assert before[0]["groups"] == after[0]["groups"] == []
    reads = [r for r in after if r.get("type") == "file"]
    assert len(reads) == 2 and all(r["status"] == "read" for r in reads)
    print(json.dumps({"fixture": "passed", "tools": verified[0]["tools"],
                      "ledger_sha256": verified[0]["ledger_sha256"], "file_reads": len(reads)}))


if __name__ == "__main__":
    {"seed": seed, "repair": repair, "check": check}[sys.argv[1]]()
