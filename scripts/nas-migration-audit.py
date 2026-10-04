#!/usr/bin/env python3
"""Read-only Linux migration audits. See docs/guides/nas_migration_audit.md.

Python >=3.11, standard library plus b3sum. Evidence is streamed; SQLite keeps
joins off the Python heap. No command copies, repairs, or removes dataset entries.
"""

import argparse
import base64
from contextlib import ExitStack, contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import uuid


SCHEMA = "nas-migration-audit/v1"
SERVED = ("30_media/30.01_movies", "30_media/30.02_tv", "30_media/30.03_music")
META = ("uid", "gid", "mode", "mtime_ns", "xattrs")
TYPES = {stat.S_IFREG: "file", stat.S_IFDIR: "directory", stat.S_IFLNK: "symlink",
         stat.S_IFIFO: "fifo", stat.S_IFSOCK: "socket", stat.S_IFCHR: "char", stat.S_IFBLK: "block"}
NORMAL = {"file", "directory", "symlink"}
HEX = re.compile(r"[0-9a-f]{64}\Z")


class AuditError(Exception):
    """Invalid input or incomplete execution: never an accepted difference."""


def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def require(condition, message):
    if not condition:
        raise AuditError(message)


def text_value(value, label):
    require(isinstance(value, str) and bool(value) and "\0" not in value, f"invalid {label}")
    return value


def relative(value):
    text_value(value, "relative path")
    require(value == "." or (not value.startswith("/") and
            all(p not in ("", ".", "..") for p in value.split("/"))), f"unsafe path: {value!r}")
    return value


def fingerprint(info):
    # ctime is used only to detect concurrent mutations, never for restoration.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def unchanged(before, after, path):
    require(fingerprint(before) == fingerprint(after), f"entry changed during audit: {path!r}")


def versions(b3sum):
    result = subprocess.run([b3sum, "--version"], capture_output=True, text=True,
                            check=True, timeout=30)
    return {"python": platform.python_version(), "b3sum": result.stdout.strip(),
            "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def hash_fd(fd, b3sum):
    # Passing an already-open regular file as stdin avoids filename escaping and
    # symlink races in b3sum's pathname handling. Its stdin implementation streams.
    before = os.fstat(fd)
    require(stat.S_ISREG(before.st_mode), "refusing to hash a non-regular file")
    result = subprocess.run([b3sum, "--no-names"], stdin=fd, capture_output=True,
                            check=True)
    digest = result.stdout.decode("ascii").strip()
    require(HEX.fullmatch(digest), "invalid b3sum output")
    unchanged(before, os.fstat(fd), "hashed file")
    return digest


class Generation:
    """Publish complete, fsynced JSONL using an atomic no-replace hardlink.

    Failed runs retain their uniquely named .partial file for diagnosis. A retry
    must use a new output name if the requested generation already exists.
    """

    def __init__(self, output, kind, run_id, **details):
        self.output = Path(output)
        self.header = {"record": "header", "schema": SCHEMA, "kind": kind,
                       "run_id": text_value(run_id, "run ID"), "generation": str(uuid.uuid4()),
                       **details}
        self.count = 0
        self.digest = hashlib.sha256()

    def __enter__(self):
        require(not os.path.lexists(self.output), f"generation already exists: {self.output}")
        require(not self.output.name.endswith(".partial"), "output name must not end in .partial")
        fd, name = tempfile.mkstemp(prefix=self.output.name + ".", suffix=".partial",
                                    dir=self.output.parent)
        self.partial = Path(name)
        with ExitStack() as initializing:
            self.stream = initializing.enter_context(os.fdopen(fd, "wb"))
            self._write(self.header)
            initializing.pop_all()
        return self

    def _write(self, row):
        data = (encoded(row) + "\n").encode("ascii")
        self.stream.write(data)
        self.digest.update(data)

    def add(self, row):
        require(row.get("record") not in ("header", "complete"), "reserved record type")
        self._write(row)
        self.count += 1

    def finish(self, failures=0):
        footer = {"record": "complete", "count": self.count, "failures": failures,
                  "status": "accepted" if failures == 0 else "differences",
                  "sha256": self.digest.hexdigest()}
        self.stream.write((encoded(footer) + "\n").encode("ascii"))
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()
        os.link(self.partial, self.output)  # atomic and fails if another writer won
        self.partial.unlink()
        with opened(self.output.parent, os.O_RDONLY | os.O_DIRECTORY) as directory:
            os.fsync(directory)

    def __exit__(self, *_):
        self.stream.close()


@contextmanager
def opened(path, flags, *, dir_fd=None):
    fd = os.open(path, flags | os.O_CLOEXEC, dir_fd=dir_fd)
    try:
        yield fd
    finally:
        os.close(fd)


def output_outside(output, roots, inputs=()):
    output = Path(output)
    require(output.parent.is_dir(), "output parent must already exist")
    resolved = output.parent.resolve() / output.name
    for root in roots:
        root = Path(root).resolve()
        require(not resolved.is_relative_to(root), f"evidence must be outside audited root: {root}")
    for path in inputs:
        require(resolved != Path(path).resolve(), "output must not replace an input")


class Tree:
    """Descriptor-relative traversal; ordinary audits never follow any symlink."""

    def __init__(self, root, b3sum="b3sum", identity="inode"):
        self.root = Path(root).absolute()
        self.b3sum = b3sum
        self.identity = identity

    def __enter__(self):
        # Opening the canonical root is explicit; every descendant is no-follow.
        self.fd = os.open(self.root.resolve(strict=True), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        return self

    def __exit__(self, *_):
        os.close(self.fd)

    @contextmanager
    def parent(self, path):
        parts = relative(path).split("/")
        fd = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                dir_fd=fd)
                os.close(fd)
                fd = child
            yield fd, parts[-1]
        finally:
            os.close(fd)

    def inode(self, fd):
        info = os.fstat(fd)
        if self.identity == "mergerfs":
            # Mergerfs path-hash deliberately gives hardlinks different presented
            # inode numbers. Query its documented backing path only for identity;
            # all content/metadata reads still go through the confined pool fd.
            backing = os.fsdecode(os.getxattr(fd, "user.mergerfs.fullpath"))
            require(backing.startswith("/"), "mergerfs returned a non-absolute backing path")
            actual = os.stat(backing, follow_symlinks=False)
            require(stat.S_ISREG(actual.st_mode), "mergerfs backing entry is not regular")
            require((actual.st_size, actual.st_mtime_ns, actual.st_nlink) ==
                    (info.st_size, info.st_mtime_ns, info.st_nlink), "mergerfs backing metadata mismatch")
            info = actual
        return f"{info.st_dev}:{info.st_ino}"

    def entry(self, parent, name, path):
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        kind = TYPES.get(stat.S_IFMT(before.st_mode))
        require(kind is not None, f"unknown entry type: {path!r}")
        row = {"record": "entry", "path": path, "type": kind, "uid": before.st_uid,
               "gid": before.st_gid, "mode": stat.S_IMODE(before.st_mode),
               "mtime_ns": before.st_mtime_ns}
        # procfs anchors lgetxattr to the already-open parent, including symlinks.
        anchored = f"/proc/self/fd/{parent}/{name}"
        row["xattrs"] = {key: base64.b64encode(os.getxattr(anchored, key, follow_symlinks=False)).decode("ascii")
                         for key in os.listxattr(anchored, follow_symlinks=False)}
        if kind in ("file", "directory"):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if kind == "directory":
                flags |= os.O_DIRECTORY
            with opened(name, flags, dir_fd=parent) as fd:
                unchanged(before, os.fstat(fd), path)
                if kind == "file":
                    row.update(size=before.st_size, blake3=hash_fd(fd, self.b3sum),
                               identity=self.inode(fd), nlink=before.st_nlink)
                    row["hardlink_group"] = row["identity"] if before.st_nlink > 1 else None
        elif kind == "symlink":
            row["target"] = os.readlink(name, dir_fd=parent)
        else:
            row["rdev"] = before.st_rdev
        unchanged(before, os.stat(name, dir_fd=parent, follow_symlinks=False), path)
        return row

    def inspect(self, path):
        with self.parent(path) as (parent, name):
            return self.entry(parent, name, path)

    def walk(self):
        yield self.entry(self.fd, ".", ".")
        yield from self._walk(self.fd, "")

    def _walk(self, fd, prefix):
        before = os.fstat(fd)
        with os.scandir(fd) as entries:
            for item in entries:
                path = prefix + item.name
                row = self.entry(fd, item.name, path)
                yield row
                if row["type"] == "directory":
                    with opened(item.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd) as child:
                        unchanged(item.stat(follow_symlinks=False), os.fstat(child), path)
                        yield from self._walk(child, path + "/")
        unchanged(before, os.fstat(fd), prefix or ".")

    def resolve_link(self, path):
        """Resolve served links inside this root, rejecting absolute/broken loops."""
        pending = relative(path).split("/")
        resolved = []
        links = 0
        while pending:
            part = pending.pop(0)
            if part in ("", "."):
                continue
            if part == "..":
                require(resolved, "served symlink escapes media root")
                resolved.pop()
                continue
            candidate = "/".join([*resolved, part])
            with self.parent(candidate) as (parent, name):
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    links += 1
                    require(links <= 40, "served symlink loop")
                    target = os.readlink(name, dir_fd=parent)
                    require(not target.startswith("/"), "absolute served symlink is not portable within mount")
                    pending = target.split("/") + pending
                else:
                    if pending:
                        # The kernel must traverse this component even if the
                        # next token is '.', '..', or a trailing slash. Lexical
                        # simplification would falsely accept unreadable links.
                        with opened(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent) as fd:
                            os.stat(".", dir_fd=fd, follow_symlinks=False)
                    resolved.append(part)
        return "/".join(resolved) or "."

    def read_access(self, path, index):
        path = self.resolve_link(path)
        parts = path.split("/")
        # List every ancestor as well as opening/traversing it. No chmod/chown.
        for end in range(len(parts)):
            parent_path = "/".join(parts[:end]) or "."
            with self.parent(parent_path) as (parent, name):
                with opened(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent) as fd:
                    require(os.fstatvfs(fd).f_flag & os.ST_RDONLY, "access encountered a writable mount")
                    index.list_directory(fd, parent_path)
        with self.parent(path) as (parent, name):
            with opened(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent) as fd:
                require(os.fstatvfs(fd).f_flag & os.ST_RDONLY, "access encountered a writable mount")
                info = os.fstat(fd)
                if stat.S_ISDIR(info.st_mode):
                    index.list_directory(fd, path)
                    return {"resolved": path, "type": "directory"}
                require(stat.S_ISREG(info.st_mode), "served target is not a file or directory")
                return {"resolved": path, "type": "file", "blake3": hash_fd(fd, self.b3sum), "size": info.st_size}


def signature(row):
    fields = list(META) + ["type"]
    fields += {"file": ["size", "blake3"], "symlink": ["target"],
               "directory": []}.get(row["type"], ["rdev"])
    return {key: row[key] for key in fields}


def validate_signature(row):
    require(isinstance(row, dict) and row.get("type") in TYPES.values(), "invalid entry type")
    for key in META[:-1]:
        require(type(row.get(key)) is int, f"invalid metadata field {key}")
    require(row["uid"] >= 0 and row["gid"] >= 0 and 0 <= row["mode"] <= 0o7777, "invalid owner/mode")
    require(isinstance(row.get("xattrs"), dict), "missing xattr/ACL evidence")
    for name, value in row["xattrs"].items():
        text_value(name, "xattr name")
        require(isinstance(value, str), "invalid xattr encoding")
        try:
            base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise AuditError("invalid base64 xattr") from exc
    if row["type"] == "file":
        require(type(row.get("size")) is int and row["size"] >= 0, "invalid file size")
        require(isinstance(row.get("blake3"), str) and HEX.fullmatch(row["blake3"]), "invalid BLAKE3 digest")
    elif row["type"] == "symlink":
        text_value(row.get("target"), "symlink target")
    elif row["type"] != "directory":
        require(type(row.get("rdev")) is int and row["rdev"] >= 0, "invalid special entry")


def json_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_generation(path, kind, consume):
    require(not str(path).endswith(".partial"), "partial generations cannot be accepted")
    digest, full_digest = hashlib.sha256(), hashlib.sha256()
    count, header, footer = 0, None, None
    with open(path, "rb") as stream:
        before = os.fstat(stream.fileno())
        for raw in stream:
            require(raw.endswith(b"\n"), "truncated JSONL line")
            require(footer is None, "trailing records after completion")
            row = json.loads(raw, object_pairs_hook=json_object)
            require(isinstance(row, dict), "JSONL record must be an object")
            full_digest.update(raw)
            if header is None:
                require(row.get("record") == "header" and row.get("schema") == SCHEMA and
                        row.get("kind") == kind, "wrong generation schema/kind")
                text_value(row.get("run_id"), "run ID")
                text_value(row.get("generation"), "generation ID")
                header = row
            elif row.get("record") == "complete":
                require(type(row.get("count")) is int and row["count"] == count and
                        row.get("sha256") == digest.hexdigest(), "incomplete or altered generation")
                require(row.get("status") == "accepted" and row.get("failures") == 0,
                        "input generation was not accepted")
                footer = row
                continue
            else:
                consume(header, row)
                count += 1
            digest.update(raw)
        unchanged(before, os.fstat(stream.fileno()), str(path))
    require(header is not None and footer is not None, "incomplete generation")
    return header, full_digest.hexdigest()


def inventory_root(path):
    # Check locations before creating even the temporary SQLite index. The full
    # parser subsequently validates this same header and its completion digest.
    with open(path, "rb") as stream:
        header = json.loads(stream.readline(), object_pairs_hook=json_object)
    require(isinstance(header, dict) and header.get("schema") == SCHEMA and
            header.get("kind") == "inventory", "invalid inventory header")
    return text_value(header.get("root"), "inventory root")


class Index:
    """Disposable disk-backed joins; filenames are JSON-escaped for byte fidelity."""

    def __init__(self, directory):
        self.directory = directory

    def __enter__(self):
        fd, self.path = tempfile.mkstemp(prefix="nas-audit-", suffix=".sqlite.partial", dir=self.directory)
        os.close(fd)
        with ExitStack() as initializing:
            initializing.callback(os.unlink, self.path)
            self.db = sqlite3.connect(self.path)
            initializing.callback(self.db.close)
            self.db.executescript("""
                CREATE TABLE entries (owner TEXT, path TEXT, data TEXT, content TEXT, links TEXT,
                                      PRIMARY KEY(owner,path));
                CREATE INDEX by_content ON entries(owner,content);
                CREATE TABLE ledger (owner TEXT, path TEXT, destination TEXT, data TEXT,
                                     PRIMARY KEY(owner,path));
                CREATE TABLE destinations (path TEXT PRIMARY KEY, expected TEXT, disposition TEXT, actual TEXT);
                CREATE TABLE links (owner TEXT, group_id TEXT, identity TEXT, PRIMARY KEY(owner,group_id));
                CREATE TABLE directories (path TEXT PRIMARY KEY, fingerprint TEXT);
            """)
            initializing.pop_all()
        return self

    def __exit__(self, *_):
        try:
            self.db.close()
        finally:
            os.unlink(self.path)

    def list_directory(self, fd, path):
        # Listing every ancestor for every file makes a flat library quadratic.
        # Cache successful listings on disk, but recheck metadata on every visit.
        before = os.fstat(fd)
        # scandir needs read permission; resolving '.' additionally proves search
        # permission, including for an empty final directory with no descendants.
        os.stat(".", dir_fd=fd, follow_symlinks=False)
        previous = self.db.execute("SELECT fingerprint FROM directories WHERE path=?", (encoded(path),)).fetchone()
        current = encoded(fingerprint(before))
        if previous:
            require(previous[0] == current, f"directory changed during access: {path!r}")
            return
        with os.scandir(fd) as entries:
            for _ in entries:
                pass
        unchanged(before, os.fstat(fd), path)
        self.db.execute("INSERT INTO directories VALUES (?,?)", (encoded(path), current))

    def inventory(self, path, owner=None):
        def consume(header, row):
            source = text_value(header.get("source_id"), "source ID")
            text_value(header.get("disk_id"), "disk ID")
            text_value(header.get("root"), "inventory root")
            require(row.get("record") == "entry", "unexpected inventory record")
            relative(row.get("path"))
            validate_signature(row)
            group = row.get("hardlink_group")
            if row["type"] == "file":
                text_value(row.get("identity"), "file identity")
                require(type(row.get("nlink")) is int and row["nlink"] >= 1, "invalid link count")
                require(group == (row["identity"] if row["nlink"] > 1 else None), "invalid hardlink group")
            content = encoded([row.get("blake3"), row.get("size")]) if row["type"] == "file" else None
            self.db.execute("INSERT INTO entries VALUES (?,?,?,?,?)",
                            (encoded(owner or source), encoded(row["path"]), encoded(row), content, group))
        header, digest = read_generation(path, "inventory", consume)
        source = owner or header.get("source_id")
        root = self.db.execute("SELECT data FROM entries WHERE owner=? AND path=?",
                               (encoded(source), encoded("."))).fetchone()
        require(root is not None and json.loads(root[0])["type"] == "directory", "inventory lacks root directory")
        # Every non-root entry needs an inventoried directory parent. A complete
        # footer alone must not turn an orphaned entry list into a complete scan.
        for (data,) in self.db.execute("SELECT data FROM entries WHERE owner=?", (encoded(source),)):
            row = json.loads(data)
            if row["path"] == ".":
                continue
            parent = row["path"].rsplit("/", 1)[0] if "/" in row["path"] else "."
            match = self.db.execute("SELECT data FROM entries WHERE owner=? AND path=?",
                                    (encoded(source), encoded(parent))).fetchone()
            require(match and json.loads(match[0])["type"] == "directory", "inventory entry lacks directory parent")
        return header, digest

    def ledger(self, path):
        def consume(_, row):
            require(row.get("record") == "disposition", "unexpected ledger record")
            source = text_value(row.get("source_id"), "source ID")
            relative(row.get("source_path"))
            text_value(row.get("reason"), "disposition reason")
            action = row.get("disposition")
            require(action in ("keep", "deduplicate", "merge", "discard", "archive"), "unknown disposition")
            destination = row.get("destination")
            if action == "discard":
                require(destination is None, "discard must have null destination")
            else:
                relative(destination)
                require(destination != "99_tmp" and not destination.startswith("99_tmp/"),
                        "retained destination is in staging")
                validate_signature(row.get("expected"))
                if action == "merge":
                    require(row["expected"]["type"] == "directory", "only directories may merge")
                if action == "deduplicate":
                    require(row["expected"]["type"] == "file", "only equal regular files may deduplicate")
                if action == "archive":
                    require(row["expected"]["type"] == "file", "archive must be a regular file")
                    text_value(row.get("restore"), "archive restore procedure")
            if row.get("hardlinks", "preserve") != "preserve":
                require(row["hardlinks"] == "separate", "unknown hardlink policy")
                text_value(row.get("hardlink_reason"), "hardlink transformation reason")
            self.db.execute("INSERT INTO ledger VALUES (?,?,?,?)",
                            (encoded(source), encoded(row["source_path"]),
                             encoded(destination) if destination is not None else None, encoded(row)))
        return read_generation(path, "ledger", consume)


def inventory(args):
    text_value(args.source_id, "source ID")
    text_value(args.disk_id, "disk ID")
    output_outside(args.output, [args.root])
    with Tree(args.root, args.b3sum, args.identity) as tree, Generation(
            args.output, "inventory", args.run_id, root=str(tree.root.resolve()),
            source_id=args.source_id, disk_id=args.disk_id, identity=args.identity,
            tools=versions(args.b3sum)) as out:
        for row in tree.walk():
            out.add(row)
        out.finish()
    return 0


def compare(args):
    output_outside(args.output, [inventory_root(args.source), inventory_root(args.copy)],
                   [args.source, args.copy])
    with Index(Path(args.output).parent) as index:
        left, left_digest = index.inventory(args.source, "source")
        right, right_digest = index.inventory(args.copy, "copy")
        output_outside(args.output, [left["root"], right["root"]])
        failures = 0
        with Generation(args.output, "compare", args.run_id, mode=args.mode,
                        inputs={"source": left_digest, "copy": right_digest}) as out:
            for path, data, content in index.db.execute("SELECT path,data,content FROM entries WHERE owner=?", (encoded("source"),)):
                source = json.loads(data)
                result = {"record": "comparison", "source_id": left["source_id"], "source_path": source["path"]}
                if args.mode == "content" and source["type"] == "file":
                    matches = index.db.execute("SELECT path FROM entries WHERE owner=? AND content=?", (encoded("copy"), content))
                    found = False
                    for (candidate,) in matches:
                        out.add({**result, "status": "candidate", "copy_path": json.loads(candidate)})
                        found = True
                    if not found:
                        out.add({**result, "status": "missing_content"})
                        failures += 1
                    continue
                match = index.db.execute("SELECT data FROM entries WHERE owner=? AND path=?", (encoded("copy"), path)).fetchone()
                status = "missing" if match is None else "match"
                if match is not None:
                    other = json.loads(match[0])
                    if signature(source) != signature(other):
                        status = "mismatch"
                    if args.mode == "path" and source.get("hardlink_group"):
                        old = index.db.execute("SELECT identity FROM links WHERE owner=? AND group_id=?",
                                               (encoded("source"), source["hardlink_group"])).fetchone()
                        if old and old[0] != other.get("identity"):
                            status = "hardlink_mismatch"
                        elif not old:
                            index.db.execute("INSERT INTO links VALUES (?,?,?)",
                                             (encoded("source"), source["hardlink_group"], other.get("identity")))
                failures += status != "match"
                out.add({**result, "status": status})
            if args.mode == "path":
                for (path,) in index.db.execute("SELECT path FROM entries WHERE owner=? EXCEPT SELECT path FROM entries WHERE owner=?",
                                               (encoded("copy"), encoded("source"))):
                    out.add({"record": "comparison", "status": "unexpected_copy_entry", "copy_path": json.loads(path)})
                    failures += 1
            out.finish(failures)
        return int(failures > 0)


def expected_from_source(source, row):
    expected = row["expected"]
    if row["disposition"] == "archive":
        require(source["type"] not in NORMAL, "archive disposition is for special entries only")
        return
    require(source["type"] in NORMAL, "special entries need archive/restore or discard")
    original = signature(source)
    require({k: v for k, v in original.items() if k not in META} ==
            {k: v for k, v in signature(expected).items() if k not in META},
            "ledger changes source content/type/target")
    changes = row.get("transformations", {})
    require(isinstance(changes, dict) and set(changes) <= set(META), "invalid metadata transformations")
    for key in META:
        if original[key] != expected[key] or key in changes:
            change = changes.get(key)
            require(isinstance(change, dict) and change.get("before") == original[key] and
                    change.get("expected") == expected[key], f"undeclared or incorrect {key} transformation")
            text_value(change.get("reason"), "transformation reason")


def register_destination(index, row, actual=None):
    path = encoded(row["destination"])
    previous = index.db.execute("SELECT expected,disposition,actual FROM destinations WHERE path=?", (path,)).fetchone()
    expected = encoded(signature(row["expected"]))
    if previous:
        require(previous[0] == expected, "conflicting content or expected metadata at destination")
        action, old_action = row["disposition"], previous[1]
        require((action == old_action == "merge") or
                (action in ("keep", "deduplicate") and old_action in ("keep", "deduplicate") and
                 (action == "deduplicate" or old_action == "deduplicate")), "destination collision needs explicit merge/deduplication")
        if action == "keep":
            index.db.execute("UPDATE destinations SET disposition='keep' WHERE path=?", (path,))
        return json.loads(previous[2]) if previous[2] is not None else None
    index.db.execute("INSERT INTO destinations VALUES (?,?,?,?)", (path, expected, row["disposition"], encoded(actual) if actual is not None else None))
    return actual


def verify(args):
    output_outside(args.output, [args.root, *map(inventory_root, args.inventory)],
                   [args.ledger, *args.inventory])
    with Index(Path(args.output).parent) as index:
        inputs, source_ids = {}, set()
        for path in args.inventory:
            header, digest = index.inventory(path)
            source = header["source_id"]
            require(source not in source_ids, "duplicate source inventory ID")
            source_ids.add(source)
            inputs[source] = digest
        ledger, ledger_digest = index.ledger(args.ledger)
        require(ledger["inventories"] == inputs, "ledger inventory digests do not match supplied sources")
        failures = 0
        with Tree(args.root, args.b3sum, args.identity) as tree, Generation(
                args.output, "verify", args.run_id, ledger_sha256=ledger_digest,
                inventories=inputs, root=str(tree.root.resolve()), tools=versions(args.b3sum)) as out:
            missing = index.db.execute("SELECT owner,path FROM entries EXCEPT SELECT owner,path FROM ledger")
            for owner, path in missing:
                failures += 1
                out.add({"record": "verification", "status": "missing_disposition", "source_id": json.loads(owner), "source_path": json.loads(path)})
            for owner, path, data in index.db.execute("SELECT owner,path,data FROM ledger"):
                row = json.loads(data)
                match = index.db.execute("SELECT data FROM entries WHERE owner=? AND path=?", (owner, path)).fetchone()
                require(match is not None, "ledger references unknown source entry")
                source = json.loads(match[0])
                result = {"record": "verification", "source_id": row["source_id"], "source_path": row["source_path"], "destination": row.get("destination")}
                if row["disposition"] == "discard":
                    out.add({**result, "status": "discard", "reason": row["reason"]})
                    continue
                expected_from_source(source, row)
                try:
                    actual = tree.inspect(row["destination"])
                except FileNotFoundError:
                    failures += 1
                    register_destination(index, row)
                    out.add({**result, "status": "missing_destination"})
                    continue
                register_destination(index, row, actual)
                status = "match" if signature(actual) == signature(row["expected"]) else "mismatch"
                group = source.get("hardlink_group")
                if group and row.get("hardlinks", "preserve") == "preserve":
                    identity = actual.get("identity")
                    old = index.db.execute("SELECT identity FROM links WHERE owner=? AND group_id=?", (owner, group)).fetchone()
                    if old and old[0] != identity:
                        status = "hardlink_mismatch"
                    elif not old:
                        index.db.execute("INSERT INTO links VALUES (?,?,?)", (owner, group, identity))
                failures += status != "match"
                out.add({**result, "status": status, "actual": signature(actual)})
            try:
                with tree.parent("99_tmp") as (parent, name):
                    with opened(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent) as fd:
                        with os.scandir(fd) as entries:
                            for item in entries:
                                failures += 1
                                out.add({"record": "verification", "status": "unresolved_staging", "path": "99_tmp/" + item.name})
            except FileNotFoundError:
                pass
            out.finish(failures)
        return int(failures > 0)


def access(args):
    require(os.getresuid() == (1000, 1000, 1000) and os.getresgid() == (1000, 1000, 1000) and
            not os.getgroups(), "access requires UID/GID 1000 with no supplementary groups")
    output_outside(args.output, [args.root], [args.ledger])
    with Index(Path(args.output).parent) as index:
        _, ledger_digest = index.ledger(args.ledger)
        failures, selected = 0, 0
        with Tree(args.root, args.b3sum) as tree, Generation(
                args.output, "access", args.run_id, ledger_sha256=ledger_digest,
                root=str(tree.root.resolve()), uid=1000, gid=1000, groups=[], tools=versions(args.b3sum)) as out:
            require(os.fstatvfs(tree.fd).f_flag & os.ST_RDONLY, "access requires a read-only mount")
            for (data,) in index.db.execute("SELECT data FROM ledger WHERE destination IS NOT NULL"):
                row = json.loads(data)
                destination = row["destination"]
                if not any(destination == prefix or destination.startswith(prefix + "/") for prefix in SERVED):
                    continue
                register_destination(index, row)
                selected += 1
                result = {"record": "access", "source_id": row["source_id"], "source_path": row["source_path"], "destination": destination}
                try:
                    actual = tree.read_access(destination.removeprefix("30_media/"), index)
                    expected = row["expected"]
                    matches = expected["type"] == "symlink" or (actual["type"] == expected["type"] and
                              (actual["type"] != "file" or (actual["blake3"], actual["size"]) == (expected["blake3"], expected["size"])))
                    failures += not matches
                    out.add({**result, "status": "read" if matches else "mismatch", **actual})
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EPERM, errno.ENOENT, errno.ENOTDIR, errno.ELOOP):
                        raise
                    failures += 1
                    out.add({**result, "status": "denied_or_unresolved", "errno": exc.errno})
            require(selected > 0, "ledger declares no served entries")
            out.finish(failures)
        return int(failures > 0)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("inventory", "compare", "verify", "access"):
        command = commands.add_parser(name)
        command.add_argument("--output", required=True, type=Path)
        command.add_argument("--run-id", required=True)
        if name != "compare":
            command.add_argument("--root", required=True, type=Path)
            command.add_argument("--b3sum", default="b3sum")
        if name in ("inventory", "verify"):
            command.add_argument("--identity", choices=("inode", "mergerfs"), default="inode",
                                 help="use mergerfs for a pool with path-hash inodes; inode for ordinary local filesystems")
        if name == "inventory":
            command.add_argument("--source-id", required=True)
            command.add_argument("--disk-id", required=True)
        elif name == "compare":
            command.add_argument("--source", required=True, type=Path)
            command.add_argument("--copy", required=True, type=Path)
            command.add_argument("--mode", choices=("path", "content"), required=True)
        else:
            command.add_argument("--ledger", required=True, type=Path)
            if name == "verify":
                command.add_argument("--inventory", required=True, action="append", type=Path)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return {"inventory": inventory, "compare": compare, "verify": verify, "access": access}[args.command](args)
    except (AuditError, OSError, ValueError, KeyError, TypeError, sqlite3.Error,
            subprocess.SubprocessError) as exc:
        print(f"audit incomplete: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
