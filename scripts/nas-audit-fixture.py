"""Live synthetic audit harness; invoked only through storage-audit-acceptance.yml."""

import argparse
import base64
from contextlib import contextmanager, ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time


audit = None  # Loaded by main, after CLI/path validation; imports have no fixture effects.
SOURCE = FINAL = EVIDENCE = None
PRIVATE = "30_media/30.01_movies/private"
RUN_ID = None
WORKSPACE_PARENT = Path("/var/tmp")
WORKSPACE = None


def workspace_paths(workspace: Path) -> tuple[Path, Path, Path]:
    """Derive only the newly allocated live workspace's scratch paths."""
    if (not workspace.is_absolute() or workspace.parent != WORKSPACE_PARENT or
            not re.fullmatch(r"nas-audit-[a-z0-9_]+", workspace.name) or
            workspace.is_symlink() or not workspace.is_dir() or workspace.resolve() != workspace):
        raise ValueError("workspace must be a real /var/tmp/nas-audit-* directory created for this run")
    info = workspace.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
        raise ValueError("workspace must be owned by the caller and not writable by other identities")
    return workspace / "private/source", workspace / "evidence", Path("/mnt/storage/99_tmp") / workspace.name / "dataset"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


@contextmanager
def directory_handle(path):
    """Open each absolute component without following a symlink, including ancestors."""
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "directory path must be absolute without traversal")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open("/", flags)
    try:
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def identity(fd):
    info = os.fstat(fd)
    return [info.st_dev, info.st_ino]


def backing_root(path=None):
    path = FINAL if path is None else Path(path)
    with directory_handle(path) as merged:
        paths = os.getxattr(merged, "user.mergerfs.allpaths").split(b"\0")
        require(len(paths) == 1, "fixture must have exactly one backing directory")
        backing = Path(os.fsdecode(paths[0]))
    relative = path.relative_to("/mnt/storage/99_tmp")
    require(re.fullmatch(r"/mnt/data[1-9][0-9]*/99_tmp/" + re.escape(str(relative)), str(backing)),
            "fixture backing path is outside configured scratch layout")
    return backing


def copy_records(root_fd, entries):
    """Copy this six-entry synthetic tree into an empty, pinned native directory."""
    allowed = {".", "30_media", "30_media/30.01_movies", PRIVATE,
               PRIVATE + "/payload", PRIVATE + "/linked-payload"}
    require({entry["path"] for entry in entries} == allowed and len(entries) == len(allowed),
            "unexpected fixture source entries")
    with os.scandir(root_fd) as children:
        require(next(children, None) is None, "refuse a nonempty backing fixture")
    with ExitStack() as resources:
        descriptors = {".": root_fd}
        directories = sorted((e for e in entries if e["type"] == "directory" and e["path"] != "."),
                             key=lambda e: e["path"].count("/"))
        for entry in directories:
            relative = Path(entry["path"])
            parent = descriptors[str(relative.parent)]
            os.mkdir(relative.name, mode=0o700, dir_fd=parent)
            fd = os.open(relative.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            resources.callback(os.close, fd)
            descriptors[entry["path"]] = fd
        first = None
        for entry in (e for e in entries if e["type"] == "file"):
            relative = Path(entry["path"])
            parent = descriptors[str(relative.parent)]
            if first is None:
                fd = os.open(relative.name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                resources.callback(os.close, fd)
                with os.fdopen(os.dup(fd), "wb") as output:
                    output.write((SOURCE / relative).read_bytes())
                first = (parent, relative.name)
            else:
                os.link(first[1], relative.name, src_dir_fd=first[0], dst_dir_fd=parent, follow_symlinks=False)
                fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
                resources.callback(os.close, fd)
            descriptors[entry["path"]] = fd
        require(len(descriptors) == len(allowed), "incomplete fixture copy")
        claim = {entry["path"]: {"identity": identity(descriptors[entry["path"]]), "type": entry["type"]}
                 for entry in entries}
        # Parents stay root-owned/inaccessible until their children are completely populated.
        for entry in sorted(entries, key=lambda e: -1 if e["path"] == "." else e["path"].count("/"), reverse=True):
            fd = descriptors[entry["path"]]
            os.fchown(fd, entry["uid"], entry["gid"])
            os.fchmod(fd, entry["mode"])
            for name, value in entry["xattrs"].items():
                os.setxattr(fd, name, base64.b64decode(value))
            os.utime(fd, ns=(entry["mtime_ns"], entry["mtime_ns"]))
        return claim


def copy_fixture(entries):
    guard = FINAL.parent
    backing = backing_root(guard)
    with directory_handle(backing) as guard_fd, ExitStack() as resources:
        info = os.fstat(guard_fd)
        require(info.st_uid == 0 and not stat.S_IMODE(info.st_mode) & 0o022,
                "new fixture must still be root-owned and not writable by the reader")
        with os.scandir(guard_fd) as children:
            require(next(children, None) is None, "refuse a nonempty backing guard")
        # The root-owned guard is never chowned: UID1000 cannot substitute dataset
        # between this mkdir and open, even if it renames the outer guard itself.
        os.mkdir("dataset", mode=0o700, dir_fd=guard_fd)
        root_fd = os.open("dataset", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=guard_fd)
        resources.callback(os.close, root_fd)
        objects = copy_records(root_fd, entries)
        require(backing_root(guard) == backing, "fixture namespace changed during copy")
        with directory_handle(backing) as current:
            require(identity(current) == identity(guard_fd), "backing guard was replaced during copy")
        claim = {"backing_root": str(backing / "dataset"),
                 "guard_root": str(backing), "guard_identity": identity(guard_fd), "objects": objects}
        with (EVIDENCE / "fixture-claim.jsonl").open("x") as output:
            output.write(json.dumps(claim) + "\n")


def repair_claimed(root_fd, objects):
    """Pin and validate every native object before changing any metadata."""
    require(identity(root_fd) == objects["."]["identity"], "fixture root identity changed")
    with ExitStack() as resources:
        descriptors = {".": root_fd}
        for relative in sorted((p for p in objects if p != "."), key=lambda p: p.count("/")):
            path = Path(relative)
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
            if objects[relative]["type"] == "directory":
                flags |= os.O_DIRECTORY
            fd = os.open(path.name, flags, dir_fd=descriptors[str(path.parent)])
            resources.callback(os.close, fd)
            require(identity(fd) == objects[relative]["identity"], "fixture object identity changed: " + relative)
            descriptors[relative] = fd
        for relative in (PRIVATE + "/payload", PRIVATE + "/linked-payload"):
            info = os.fstat(descriptors[relative])
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 2, "unexpected backing hardlinks")
        private_fd = descriptors[PRIVATE]
        for name in ("system.posix_acl_access", "system.posix_acl_default"):
            if name in os.listxattr(private_fd):
                os.removexattr(private_fd, name)
        for relative in (PRIVATE, PRIVATE + "/payload", PRIVATE + "/linked-payload"):
            os.fchown(descriptors[relative], 1000, 1000)
            os.fchmod(descriptors[relative], 0o775 if relative == PRIVATE else 0o644)


def cleanup_claimed(root_fd, objects):
    """Remove only the sealed, identity-checked synthetic objects; never recurse."""
    require(identity(root_fd) == objects["."]["identity"], "fixture root identity changed")
    with ExitStack() as resources:
        descriptors = {".": root_fd}
        for relative in sorted((p for p in objects if p != "."), key=lambda p: p.count("/")):
            path = Path(relative)
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if objects[relative]["type"] == "directory":
                flags |= os.O_DIRECTORY
            fd = os.open(path.name, flags, dir_fd=descriptors[str(path.parent)])
            resources.callback(os.close, fd)
            require(identity(fd) == objects[relative]["identity"], "cleanup object identity changed: " + relative)
            descriptors[relative] = fd
        # Seal only the original objects. No unprivileged directory writer can race deletion afterward.
        for relative, fd in descriptors.items():
            os.fchown(fd, os.geteuid(), os.getegid())
            os.fchmod(fd, 0o700 if objects[relative]["type"] == "directory" else 0o600)
        for relative, fd in descriptors.items():
            if objects[relative]["type"] == "directory":
                expected = {Path(p).name for p in objects if p != "." and str(Path(p).parent) == relative}
                with os.scandir(fd) as children:
                    require({entry.name for entry in children} == expected, "unexpected cleanup entries: " + relative)
        # A writer may have held a directory handle during descriptor collection.
        # Revalidate every namespace edge only after sealing all original parents.
        for relative in (p for p in objects if p != "."):
            path = Path(relative)
            info = os.stat(path.name, dir_fd=descriptors[str(path.parent)], follow_symlinks=False)
            require([info.st_dev, info.st_ino] == objects[relative]["identity"], "cleanup entry identity changed: " + relative)
        for relative in (PRIVATE + "/payload", PRIVATE + "/linked-payload"):
            require(os.fstat(descriptors[relative]).st_nlink == 2, "unexpected cleanup hardlinks")
        for relative in (PRIVATE + "/payload", PRIVATE + "/linked-payload"):
            path = Path(relative)
            info = os.stat(path.name, dir_fd=descriptors[str(path.parent)], follow_symlinks=False)
            require([info.st_dev, info.st_ino] == objects[relative]["identity"], "cleanup entry replaced")
            os.unlink(path.name, dir_fd=descriptors[str(path.parent)])
        require(os.fstat(descriptors[PRIVATE + "/payload"]).st_nlink == 0, "fixture has an unexpected surviving link")
        for relative in sorted((p for p in objects if p != "." and objects[p]["type"] == "directory"),
                               key=lambda p: p.count("/"), reverse=True):
            path = Path(relative)
            os.rmdir(path.name, dir_fd=descriptors[str(path.parent)])
            require(os.fstat(descriptors[relative]).st_nlink == 0, "owned directory was not removed")


def cleanup():
    require(WORKSPACE is not None, "live cleanup requires a workspace")
    claim_file = EVIDENCE / "fixture-claim.jsonl"
    guard_path = FINAL.parent
    backing = backing_root(guard_path)
    with directory_handle(backing) as guard_fd:
        if claim_file.exists():
            claim = rows(claim_file)[0]
            require(str(backing) == claim["guard_root"] and identity(guard_fd) == claim["guard_identity"], "guard identity changed")
            with directory_handle(backing / "dataset") as root_fd:
                cleanup_claimed(root_fd, claim["objects"])
                os.rmdir("dataset", dir_fd=guard_fd)
                require(os.fstat(root_fd).st_nlink == 0, "owned dataset directory was not removed")
        with os.scandir(guard_fd) as children:
            require(next(children, None) is None, "unclaimed or unexpected fixture content; preserve for assessment")
        with directory_handle(backing.parent) as parent_fd:
            info = os.stat(backing.name, dir_fd=parent_fd, follow_symlinks=False)
            require([info.st_dev, info.st_ino] == identity(guard_fd), "guard was replaced before removal")
            # The scratch parent intentionally belongs to UID1000. Remove its
            # empty guard with that identity, without granting root deletion rights.
            subprocess.run(["setpriv", "--reuid=1000", "--regid=1000", "--clear-groups",
                            "rmdir", "--", str(guard_path)], check=True)
            require(os.fstat(guard_fd).st_nlink == 0, "owned guard directory was not removed")


def seal_reader():
    require(WORKSPACE is not None, "reader protection requires a live workspace")
    path = WORKSPACE / "reader"
    if not path.exists() and not path.is_symlink():
        return
    with directory_handle(path) as fd:
        os.fchown(fd, os.geteuid(), os.getegid())
        os.fchmod(fd, 0o700)
        with os.scandir(fd) as children:
            for entry in children:
                info = entry.stat(follow_symlinks=False)
                require(stat.S_ISREG(info.st_mode) and info.st_uid == 1000 and info.st_nlink == 1,
                        "unexpected reader artifact; preserve workspace for assessment")


def capture(phase):
    seal_reader()
    source = WORKSPACE / "reader" / ("reader-" + phase + ".jsonl")
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 1000 and info.st_nlink == 1 and info.st_size < 1048576,
                "unexpected reader report")
        content = stream.read()
        require((os.fstat(stream.fileno()).st_size, os.fstat(stream.fileno()).st_mtime_ns) == (info.st_size, info.st_mtime_ns),
                "reader report changed during capture")
    output_fd = os.open(EVIDENCE / ("access-" + phase + ".jsonl"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(output_fd, "wb") as output:
        output.write(content)
    if phase == "before":
        with directory_handle(WORKSPACE / "reader") as directory:
            os.fchown(directory, 1000, 1000)
            os.fchmod(directory, 0o755)


def rows(path):
    with open(path) as stream:
        return [json.loads(line) for line in stream]


def run(*args, expected=0):
    result = audit.main([*map(str, args), "--run-id", RUN_ID])
    if result != expected:
        raise RuntimeError(f"audit returned {result}, expected {expected}: {args}")


def seed():
    require(stat.S_IMODE(WORKSPACE.stat().st_mode) == 0o700,
            "live workspace must remain private during root seeding")
    require(FINAL.parent.is_dir() and not FINAL.parent.is_symlink(), "live fixture guard must be a real directory")
    with os.scandir(FINAL.parent) as entries:
        require(next(entries, None) is None, "refuse a nonempty live fixture")
    SOURCE.parent.mkdir(mode=0o700)
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
    run("inventory", "--root", SOURCE, "--source-id", "fixture",
        "--disk-id", "workspace-source",
        "--output", inventory)
    copy_fixture(rows(inventory)[1:-1])
    digest = hashlib.sha256(inventory.read_bytes()).hexdigest()
    with audit.Generation(EVIDENCE / "ledger.jsonl", "ledger", RUN_ID,
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
    claim = rows(EVIDENCE / "fixture-claim.jsonl")[0]
    require(str(backing_root()) == claim["backing_root"], "fixture backing path changed")
    with directory_handle(claim["backing_root"]) as root_fd:
        repair_claimed(root_fd, claim["objects"])
    # The accepted mergerfs configuration caches attributes/entries for one second.
    time.sleep(2)
    run("verify", "--root", FINAL, "--identity", "mergerfs", "--inventory", EVIDENCE / "source.jsonl",
        "--ledger", EVIDENCE / "ledger.jsonl", "--output", EVIDENCE / "verify-after.jsonl")


def check():
    before, after = rows(EVIDENCE / "access-before.jsonl"), rows(EVIDENCE / "access-after.jsonl")
    verified = rows(EVIDENCE / "verify-after.jsonl")
    require(before[-1]["status"] == "differences" and before[-1]["failures"] >= 1, "missing denied-access result")
    require(any(r.get("status") == "denied_or_unresolved" and r.get("errno") == 13 for r in before), "missing EACCES evidence")
    require(after[-1]["status"] == verified[-1]["status"] == "accepted", "repair/access was not accepted")
    require(before[0]["ledger_sha256"] == after[0]["ledger_sha256"] == verified[0]["ledger_sha256"], "ledger generation changed")
    require(before[0]["uid"] == after[0]["uid"] == 1000, "wrong reader UID")
    require(before[0]["gid"] == after[0]["gid"] == 1000, "wrong reader GID")
    require(before[0]["groups"] == after[0]["groups"] == [], "reader has supplementary groups")
    require(before[0]["tools"] == after[0]["tools"] == verified[0]["tools"], "audit tool/helper versions changed")
    reads = [r for r in after if r.get("type") == "file"]
    require(len(reads) == 2 and all(r["status"] == "read" for r in reads), "both fixture files must be read")
    print(json.dumps({"fixture": "passed", "tools": verified[0]["tools"],
                      "ledger_sha256": verified[0]["ledger_sha256"], "file_reads": len(reads)}))


def main(argv=None):
    global audit, SOURCE, EVIDENCE, FINAL, RUN_ID, WORKSPACE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["seed", "repair", "check", "cleanup", "seal-reader", "capture-before", "capture-after"])
    parser.add_argument("--workspace", type=Path, required=True,
                        help="owned /var/tmp/nas-audit-* workspace; scratch guard must already exist")
    args = parser.parse_args(argv)
    SOURCE, EVIDENCE, FINAL = workspace_paths(args.workspace)
    WORKSPACE = args.workspace
    RUN_ID = args.workspace.name
    helper = WORKSPACE / "scripts/nas-migration-audit.py"
    spec = importlib.util.spec_from_file_location("nas_audit", helper)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    if args.phase == "seed":
        seed()
    elif args.phase.startswith("capture-"):
        capture(args.phase.removeprefix("capture-"))
    elif args.phase in ("cleanup", "seal-reader"):
        {"cleanup": cleanup, "seal-reader": seal_reader}[args.phase]()
    else:
        {"repair": repair, "check": check}[args.phase]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
