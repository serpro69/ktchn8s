# NAS migration audit helper

`scripts/nas-migration-audit.py` supplies Task 13's acceptance tooling for the
[NAS migration runbook](../feat/wip/nas-storage-layout/implementation.md#migration-runbook).
It reads datasets and writes evidence. The operator still chooses destinations,
copies data, records discards, repairs permissions and approves drive release.
Successful audits do not establish independent recovery copies or parity protection.

## Environment and evidence

Run controller tooling inside `nix develop`. The helper needs Linux, Python 3.11+
and `b3sum`; it uses no third-party Python packages. Inventory and reconciliation
run locally on the host holding the data, with permission to read every entry and
its xattrs/ACLs. NAS Python/b3sum installation and version comparison remain
Task 13.4 while the host is offline. Do not deploy it through the storage role.

Choose a run ID and follow the runbook's
[independent evidence workspace rules](../feat/wip/nas-storage-layout/implementation.md#migration-evidence).
The output directory must already exist, be outside all audited roots, and have
space for reports and a temporary SQLite index. Neither an alias of the dataset
nor a second directory on a disk due for wiping is independent evidence. The
helper checks canonical paths, but cannot establish physical-device independence
or detect every bind-mount alias; the operator must check those properties.

Freeze the original source entries and quiesce destination writers. The helper
detects changes during a file read/directory enumeration; it does not create a
filesystem snapshot or prevent later writes. A destination or ledger change
invalidates earlier acceptance. Reconcile and audit access again before freezing
the final dataset for parity.

Every invocation needs a fresh output name. Reports start in a unique
`<output>.<random>.partial` file, are flushed and fsynced, then published atomically
without replacing an existing generation. An execution failure leaves an
unpublished partial for diagnosis. Never rename a partial to accept it or resume
one: run a complete new scan. SQLite joins are disk-backed and removed on normal
exit; abrupt termination can leave scratch files, which are not evidence.

| Exit | Meaning |
|---|---|
| `0` | Completed and accepted for this command's criteria. |
| `1` | Completed, with differences or access-policy failures; report published. |
| `2` | Execution/input error; no completed output is published. Includes invalid ledgers, failed hashes, I/O errors, changed files and incomplete input generations. |

Neither nonzero status authorizes acceptance. Permission denial during `access`
is exit 1; an I/O failure is exit 2. Check both process exit and report footer.

## Commands

These are future operational examples, not instructions to contact the offline NAS.
Use absolute paths on the host actually running each command, and a fresh output
name on each retry. `--b3sum /path/to/b3sum` selects a verified executable if needed.

```bash
python3 scripts/nas-migration-audit.py inventory \
  --root /mnt/driveA --source-id A --disk-id disk-by-id-recorded-for-A \
  --run-id migration-01 --output /var/log/snapraid/migration/run-01/driveA.jsonl

python3 scripts/nas-migration-audit.py inventory \
  --root /mnt/storage/99_tmp/driveA --source-id nas-copy --disk-id nas-pool \
  --identity mergerfs --run-id migration-01 \
  --output /var/log/snapraid/migration/run-01/nas-copy.jsonl

python3 scripts/nas-migration-audit.py compare --mode path \
  --source /evidence/driveA.jsonl --copy /evidence/nas-copy.jsonl \
  --run-id migration-01 --output /evidence/compare-A.jsonl

python3 scripts/nas-migration-audit.py compare --mode content \
  --source /evidence/driveB.jsonl --copy /evidence/nas-copy.jsonl \
  --run-id migration-01 --output /evidence/discover-B.jsonl

python3 scripts/nas-migration-audit.py verify \
  --inventory /evidence/driveA.jsonl --inventory /evidence/driveB.jsonl \
  --inventory /evidence/driveC.jsonl --ledger /evidence/ledger-01.jsonl \
  --root /mnt/storage --identity mergerfs \
  --run-id migration-01 --output /evidence/verify-01.jsonl
```

`inventory` includes the root as `.` and every descendant, including empty
directories, symlinks and special files. Names round-trip via escaped JSON,
including newlines, Cyrillic and non-UTF-8 Linux filenames. It records numeric
UID/GID/mode, nanosecond mtime and base64 xattrs, including Linux POSIX ACL xattrs.
It ignores atime and does not compare ctime. Symlink targets are literal; no link
is followed and no device/FIFO/socket is read as ordinary file data. Unsupported
xattr access fails the scan rather than silently dropping restoration metadata.

The default `--identity inode` records device/inode hardlink groups on ordinary
local filesystems. Use `--identity mergerfs` on this NAS pool: its `path-hash`
inode numbers differ between hardlink paths. This mode gets backing identities
through mergerfs's documented
[`user.mergerfs.fullpath` attribute](https://trapexit.github.io/mergerfs/2.41.1/runtime_interface/#file-directory-xattrs).
It checks backing metadata and still reads bytes through the confined pool path.
Do not use these identity modes on filesystems with unreliable identities or
through NFS; establish a supported local inventory method first.

Path comparison checks metadata/content, hardlink grouping and unexpected copy
entries. Content comparison emits every source file's equal-content candidates
regardless of path; non-file entries retain path/metadata comparisons. Candidate
matches never authorize deletion or deduplication. Distinct required final paths
must each exist even when their bytes match.

## Ledger schema and publication

All generations use JSONL: one `header`, body records, then one `complete` footer.
The header has `schema: "nas-migration-audit/v1"`, `kind`, `run_id`, and a unique
`generation`. Inventory headers also include `source_id`, `disk_id`, canonical
`root`, identity mode, Python/b3sum versions and helper SHA-256. Ledger headers
have `inventories`, mapping each source ID to the SHA-256 of the entire completed
inventory file. The footer contains body-record `count`, `failures`, `status`
and the SHA-256 of every preceding byte (including newlines). Inputs must be
accepted, complete, internally consistent generations; duplicate JSON keys and
source/path rows fail input validation.

Prepare one `record: "disposition"` row per source entry in an operator-reviewed
`decisions.jsonl` body. Each row has these fields:

| Field | Meaning |
|---|---|
| `source_id`, `source_path` | Exact original identity, including `.` for the source root. |
| `disposition` | `keep`, `merge`, `deduplicate`, `discard`, or `archive`. |
| `destination` | Canonical relative path under the final NAS root, or `null` for discard. Never a path in `99_tmp`. |
| `reason` | Required explanation for the disposition. |
| `expected` | Required for retained entries: `type`, `uid`, `gid`, integer `mode`, `mtime_ns`, `xattrs`, plus `size`/`blake3` for files or `target` for symlinks. Copy these values from the source inventory unless a metadata transformation is declared. |
| `transformations` | Optional mapping of changed metadata fields to `{ "before": ..., "expected": ..., "reason": "..." }`. Allowed fields: UID, GID, mode, mtime and xattrs, using their lowercase schema keys. |
| `hardlinks`, `hardlink_reason` | Default `preserve`. To intentionally separate a hardlink, set `hardlinks: "separate"` and record the reason. |
| `restore` | Required for `archive`: explicit archive restoration procedure for a special entry. `expected` describes the regular archive file whose bytes are verified. |

`merge` applies only to directories. Every source directory sharing a destination
must explicitly say `merge`, with compatible expected metadata. File destinations
can have at most one `keep` row; additional identities must explicitly say
`deduplicate` and have identical expected content and metadata. Two plain `keep`
rows collide. A discard requires a reason and no destination. Special entries
require archive/restore or discard; a regular file cannot be declared an archive
to bypass source-content verification.

Metadata repairs must describe original values and expected final values before
the operator applies them. Content/type/symlink-target changes cannot be approved
as metadata transformations. If preserved and served trees share an inode but
need different permissions, separate their copies and declare that hardlink
transformation. Do not normalize backup metadata as a side effect of media access.

Seal reviewed decisions as a **new** ledger generation using the helper's writer.
This example runs from the repository root; edit the explicit source list and paths.
It does not choose or alter any dispositions:

```python
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("audit", "scripts/nas-migration-audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
inventories = {}
for path in [Path("/evidence/driveA.jsonl"), Path("/evidence/driveB.jsonl"),
             Path("/evidence/driveC.jsonl")]:
    header, digest = audit.read_generation(path, "inventory", lambda header, row: None)
    if header["source_id"] in inventories:
        raise ValueError("duplicate source ID")
    inventories[header["source_id"]] = digest
with audit.Generation("/evidence/ledger-01.jsonl", "ledger", "migration-01",
                      inventories=inventories) as output:
    with open("/evidence/decisions.jsonl") as decisions:
        for line in decisions:
            output.add(json.loads(line))
    output.finish()
```

Sealing only establishes a complete generation, not valid dispositions or acceptance.
`verify` validates the source inventory digests, complete source accounting, source
content, declared metadata, destination collisions and retained hardlinks. It
rehashes every retained file and requires `99_tmp` to have no entries, including
empty leftover directories. Missing destinations/dispositions are reported
differences; conflicting or malformed decisions are input errors. Skeleton and
unrelated final paths are not rejected merely because they are absent from the
ledger. The helper does not evaluate SnapRAID exclusions or independent-copy gates;
the migration runbook requires those separately.

## Served-content access

Mount only `server:/mnt/storage/30_media` read-only on an allowed client. Prepare
an evidence directory writable by UID/GID 1000 outside the mount, with a readable
copy of the **same ledger generation** used by `verify`. Then run:

```bash
setpriv --reuid=1000 --regid=1000 --clear-groups \
  python3 scripts/nas-migration-audit.py access \
  --root /mnt/media-audit --ledger /evidence/ledger-01.jsonl \
  --run-id migration-01 --output /evidence/access-01.jsonl
```

The command refuses another identity, supplementary groups or a writable mount.
It derives served paths from the ledger's `30.01_movies`, `30.02_tv`, and
`30.03_music` subtrees, removes `30_media/`, lists/traverses ancestors and opens
and hashes entire served files. It checks mount read-only flags along the path.
Relative served symlinks must resolve within the media mount; escaping, absolute,
looping or unresolved targets cannot pass. A ledger without served entries is an
input error, not a vacuous access pass.

Require zero failures in both reports and identical `ledger_sha256` values.
Unmount the audit client before any further local repair. After repair, run both
checks again against the updated ledger and unchanged final data. Task 7 uses real
migrated paths; the synthetic VM check only establishes the helper's behavior.

## Repeatable local verification

```bash
nix develop -c python3 -B -m unittest discover -s tests -p test_nas_migration_audit.py -v
nix develop -c bash -c 'cd metal/roles/storage && molecule test -s nfs-lifecycle'
```

The scenario at `metal/roles/storage/molecule/nfs-lifecycle/` (see its `README.md`)
owns disposable guests and tests permission failure before a declared repair,
successful UID-1000 reads afterward, ACL/xattr preservation and mergerfs hardlink
identity. It also runs the unit suite with guest Python/b3sum. Retain helper digest,
tool versions, ledger and both report generations for Task 6's version comparison.
