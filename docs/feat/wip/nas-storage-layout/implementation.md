# NAS Storage Directory Layout — Implementation Plan

> Design: [design.md](./design.md) · Tasks: [tasks.md](./tasks.md)

Audience: an experienced infra engineer with zero context for this repo. Relevant repo
geography: `metal/roles/storage/` is the Ansible role that provisions the NAS
(`yggdrasil`, `10.10.10.30`); `system/csi-driver-nfs/` is the Helm chart that renders
static NFS PVs; `apps/jellyfin/` is an app-template-based chart running the media stack;
ArgoCD owns everything under `system/`, `platform/`, `apps/` after bootstrap — cluster
changes are applied by committing to git and syncing, never `kubectl apply`. All tooling
runs inside `nix develop`.

## tree-skeleton

Replace the flat `storage_dirs` list with the designed tree.

1. In `metal/roles/storage/vars/main.yml`, replace the `storage_dirs` value
   (`Backups, Documents, Music, Pictures, Temp, Videos`) with the full designed tree as
   relative paths (e.g. `00_meta`, `10_documents`, `10_documents/inbox`,
   `10_documents/10.01_personal`, …, `30_media/rotation/movies`, `30_media/rotation/shows`,
   `30_media/rotation/downloads/complete`, `30_media/rotation/downloads/incomplete` —
   NB: `downloads/` nests INSIDE `rotation/` so linking containers see one mount —
   …, `99_tmp`). Keep it
   one flat list of paths — the consuming task (`tasks/nfs.yml:21`, a `file: state=directory`
   loop over `storage_dirs`) then needs no structural change. Set ownership/mode in that
   task to `1000:1000` / `0775` if not already (must match `nfs_anon_uid/gid` in
   `defaults/main.yml`).
   → verify: inspect a storage-play check/diff, then run twice and require zero changes
   from the directory/legend tasks on the second run. Do not require the whole role's
   recap to be zero: its existing `sensors-detect` task always reports a change.
2. Add `templates/storage-readme.j2` rendering `00_meta/README.md` from the same
   `storage_dirs` variable plus a hand-written legend header (grammar rules, the
   `50_topics` working-set test, machine-vs-human convention, pointer to this repo's
   design doc). Add a task to render it (e.g. at the end of `tasks/nfs.yml` or a new
   `tasks/layout.yml` included from `tasks/main.yml` after the mergerfs include at line 48).
   Also create an empty `00_meta/RETIRED.md` (`copy: force=false`).
   → verify: `ssh root@10.10.10.30 cat /mnt/storage/00_meta/README.md` lists every dir in
   the tree; re-run is idempotent.
3. The old `Videos`, `Backups`, etc. dirs from the previous list: the role must NOT
   delete anything (fail-loud principle — removal is a human decision). Delete them
   manually on the NAS after confirming they are empty.
   → verify: `find /mnt/storage -maxdepth 1` shows only the new tree + lost+found.

Note: do not remove `Temp` blindly — `tasks/k8s_validation.yml` and NFS validation tasks
may reference it; grep the role first and repoint those to `99_tmp` if so.

## snapraid-excludes

In `metal/roles/storage/templates/snapraid.conf.j2`, use **root-anchored** excludes
(leading slash = disk root only) — name-anchored patterns match at ANY depth and would
silently exclude same-named dirs inside `70_backups` dumps:

- add `exclude /30_media/rotation/` — *arr + transmission churn (covers nested
  `downloads/`), re-downloadable by design; keeps `update_threshold`/`delete_threshold`
  meaningful
- add `exclude /10_documents/inbox/` — machine-consumed transient drop dir
- add `exclude /99_tmp/` — migration staging / scratch
- **remove** the existing name-anchored `exclude downloads/` and `exclude appdata/` —
  the former is superseded by rotation, and application state belongs on Ceph rather
  than an arbitrary deep `appdata` directory. Keep `/tmp/` and the listed OS-cruft
  excludes; the migration audit must identify any retained content matching them

Keep a one-line comment per exclude stating *why*. In the same template, use
`loop.index` for additional parity directives and filenames: `parity`, `2-parity`,
`3-parity`. The present `loop.index - 1` repeats the first level via its `1-parity`
alias when adding the second device.
→ verify offline: render one-, two-, and three-device configurations; check the exact
directives/paths and root-anchored excludes, including included backup paths containing
`downloads` or `appdata`. Parse representative configs using SnapRAID 13.0 in a
disposable fixture with accessible data/content directories; assert failure for the
old duplicate-first-level configuration. No sync against real disks is part of Task 2.

The role skips `snapraid.yml` entirely while `parity_drives` is empty. Inspect the live
`/etc/snapraid.conf` and run `snapraid status` only in Task 8 after adding the first
parity device; Task 2 completes with offline validation, not that later live check.

## nfs-export-readiness

Task 11 is synthetic NFS validation, independent of the media applications. Create
`99_tmp/nfs-readiness/{downloads,library}` and expose that one fixture subtree to its
test clients. All creates, links, renames and RO probes stay there; clean up clients
and fixtures before NAS-local migration/sorting begins.

1. In `metal/roles/storage/tasks/mergerfs.yml`, add `noforget` and
   `inodecalc=path-hash` while retaining `category.create=mfs`, remove legacy `use_ino`,
   and keep lazy unmount disabled. Apply in a maintenance window: stop/unmount clients,
   stop NFS, unmount/remount mergerfs normally, restore exports/NFS, and reconnect
   clients. Changing fstab alone does not prove the running options changed.
   → verify: inspect active mergerfs options and NAS process memory, then exercise
   repeated create/link/rename/open/close/reopen from two NFS clients, including after
   an idle interval and a controlled server remount/recovery.
2. Retain `root_squash` and `anonuid/anongid=1000`. The upstream general recommendation
   is broader than this fixed-owner workload; explicitly test it as UID/GID 1000.
   Directories needed by services are created NAS-side with that owner. Test nested
   creation, link, rename, read and deletion; errors block rollout and require a
   design decision, not an automatic switch to `no_root_squash` or privileged clients.
   → verify: successful operations as the real writer identity, plus RO rejection.
3. Extend `tasks/nfs_validation.yml` and `tasks/k8s_validation.yml` to perform the
   lifecycle checks on `99_tmp`, report failures, and clean up fixtures. Correct the
   test pod's existing trailing `&&` before relying on its shell script. Require an
   available kubeconfig and an actually successful pod, not the optional-test skip.
   From the repository root, run `make -C metal storage ANSIBLE_TARGETS=yggdrasil
   ANSIBLE_ARGS='-e validate_nfs=true'` when the cluster and NAS are available.
   → verify: NFS and Kubernetes validation both execute and pass; a deliberately
   unwritable fixture is reported as failed, not skipped.
4. Simulate promotion inside the fixture: link a downloads file into its library,
   rename the library entry and reopen through both clients. Verify unchanged bytes
   through the surviving download name and backing hardlink identity; no torrent
   client or production library is needed. With `path-hash`, presented inode numbers
   may differ, so also use link count and the backing branch's inode identity.
   → verify: reads survive the rename and controlled remount/recovery. Actual seeding,
   library rescans and the operator's production promotion procedure belong to Task 5.

References: [mergerfs 2.41.1 NFS](https://trapexit.github.io/mergerfs/2.41.1/remote_filesystems/)
and [inode calculation](https://trapexit.github.io/mergerfs/2.41.1/config/inodecalc/).

## parity-job-readiness

Task 12 prepares bootstrap/expansion before source disks are released. Update
`metal/roles/storage/tasks/snapraid.yml`, `tasks/snapraid_initial_sync.yml`,
`handlers/main.yml`, and `templates/snapraid-initial-sync.service.j2`:

1. Deploy the bootstrap unit on every configuration run, including when first parity
   exists. Remove the first-file-exists completion assumption and automatic start
   on config changes; the operator starts this job after the runbook's safety gates.
   → verify: first setup, an interrupted job, and adding second parity all leave a
   runnable unit; applying configuration alone does not run parity computation.
2. Make the unit invoke `/usr/local/bin/snapraid --force-full sync` directly, retaining
   output in the journal. This explicit full computation supports initial creation
   and adding another parity level while retaining existing parity/content files.
   Remove the `tee` pipeline and the fixed 12-hour cutoff (`TimeoutStartSec=infinity`);
   the operator monitors progress and may stop a stuck job. Keep routine incremental
   syncs in the maintenance runner.
   → verify in a disposable multi-filesystem fixture: one parity then two parity
   initialize, a nonzero SnapRAID exit produces a failed unit, an interrupted run
   cannot satisfy completion, and retry completes without deleting old parity.
3. During bootstrap/expansion, stop and disable the runner and scrub timers and wait
   for existing jobs to finish. Ensure the role/handlers respect disabled maintenance
   settings instead of restarting a timer unconditionally. Do not rely on `Conflicts=`
   alone: a timer could start another unit and terminate the active bootstrap job.
   → verify: a role rerun leaves maintenance stopped until the operator re-enables it.

Task 8 records the unit invocation, completion result/exit status and logs, then runs
an explicit full scrub. These changes do not make existence of a parity file or a
previous successful invocation sufficient evidence for a newly added parity level.

## devshell-b3sum

Add `b3sum` to the `packages` list in the `devShells.default` `mkShell` block of
`flake.nix` (~line 31).
→ verify: `nix develop -c b3sum --version`.

## migration-audit-tooling

Task 13 creates `scripts/nas-migration-audit.py` and
`tests/test_nas_migration_audit.py` before Task 6. Use Python's standard library and
the Task 3 `b3sum` executable. Before Task 13's NAS fixture, verify Python 3 and install
`b3sum` once there (`apt install b3sum` on Debian, or a verified upstream binary);
record both versions with the fixture results. The helper reads datasets and writes
evidence only. Copying, moving, permission changes, discards and disk operations remain
explicit operator actions.

| Subcommand | Inputs and result |
|---|---|
| `inventory` | Root, source/disk ID and output path → versioned JSONL inventory of all entry types; BLAKE3 for regular files, literal symlink targets, numeric UID/GID/mode, mtime and ACL/xattr evidence. Do not compare non-restorable ctime or read-sensitive atime. Record source hardlink groups where the filesystem exposes reliable identities. |
| `compare` | Source and copy inventories; select path comparison for A's copy or content comparison for B/C discovery → missing/mismatched entries and candidate equal-content matches, preserving every source identity. It never decides that a duplicate may be discarded. |
| `verify` | A/B/C inventories, disposition ledger and final NAS root → complete source-to-destination/content/expected-metadata reconciliation. |
| `access` | Disposition ledger and a read-only mount of `30_media` → directory-list/traversal and actual file-open/read results for every declared served path, executed as UID/GID 1000 with no extra groups. Derive paths from the ledger's three served subtrees and remove the `30_media/` prefix for this mount; reject paths escaping it and unresolved link targets. |

The inventory and ledger use escaped JSON strings that round-trip filesystem names,
including spaces, newlines and Cyrillic. Never follow symlinks during inventory or
read a special device as ordinary file data. Unsupported entries require an explicit
archive/restore or discard decision. Ledger rows identify source ID/path, disposition,
final destination and reason; metadata transformations include before/expected values.
Explicit directory merges and equal-content deduplication are allowed; conflicting
file content or incompatible expected metadata at one destination fails verification.
Reject paths escaping their declared roots; regular-file verification must not follow
an intermediate symlink outside the final NAS root and mistake source data for a copy.

Exit 0 means the command completed successfully with its acceptance criteria met;
exit 1 means a completed comparison/audit found differences or access failures;
exit 2 means an execution/input error, including inventory/verification I/O errors,
failed hashes, source changes during hashing or incomplete inputs. An `access`
permission denial is a reported policy failure (exit 1), not an incomplete scan.
Neither nonzero exit authorizes acceptance. Write outputs outside audited roots
through `.partial` files and publish a completed generation atomically, with
schema/run ID, counts and completion status. Never overwrite a completed generation.
Retries create a fresh generation; partial inventories cannot be resumed or accepted.
Verification/access reports record the same ledger digest; any ledger or destination
change invalidates previous acceptance and requires the relevant checks again.
Stream inventories/reports and hash locally to avoid reading NAS data over the network.

→ verify: `python3 -m unittest discover -s tests -p 'test_nas_migration_audit.py'`
covers the command exit/output contract, partial scans/retries, failed hashes, unusual
names, symlinks/root escapes, special files, missing/duplicate ledger rows, merges/collisions,
equal-content distinct destinations and approved metadata transformations. The access
fixture must fail on a foreign-owned 0700 tree, then pass after the declared fix;
run that identity-sensitive check on the NAS/Task 11 test environment if necessary.
Task 13 depends on Tasks 3 and 11, uses their tool/fixture environment, and cleans up
its clients afterward. It completes only when its checks pass, before Task 6 starts.

## nfs-media-share

In `system/csi-driver-nfs/values.yaml`, replace the `volumes` entry:

- `name: videos` → `name: media`
- `share: Videos` → `share: 30_media`
- `capacity: 1Ti` → `capacity: 4Ti` (nominal for NFS; must be ≥ any bound PVC request)

This renders PV `pv-nfs-media` (template `templates/pv-nfs.yaml` derives the name).
The share/volume handle cannot be changed in place on the old PV. Task 4 prepares the
replacement chart on a non-deployed work branch and completes with offline rendering;
it performs no cluster deletion or sync.
→ verify: `helm template system/csi-driver-nfs | grep -A3 volumeHandle` shows
`…/mnt/storage/30_media`, with the intended capacity and Retain policy.

Task 5 consumes the prepared chart and owns one release containing both the PV and
application changes, after Task 8 and the export checks. Keep Task 4 off the deployed
Git revision until that release. Task 5 owns stale-resource cleanup and live acceptance.

## jellyfin-remount

In `apps/jellyfin/values.yaml` (+ `templates/pvc-videos.yaml`):

1. Rename the static-binding PVC: `templates/pvc-videos.yaml` → `pvc-media.yaml`;
   `metadata.name: pvc-nfs-media`, `volumeName: pv-nfs-media`, `storage` request ≤ PV
   capacity. Keep `storageClassName: ""`.
2. In `persistence`: drop the `anothervideos` block. Rename/redefine it as `media` using
   `existingClaim: pvc-nfs-media` with `advancedMounts`. **Critical rule: a container
   that hardlinks (radarr, sonarr) gets exactly ONE mount from this PVC** — separate
   subPath mounts of the same PVC are distinct bind mounts and `link(2)` fails with
   `EXDEV` across them (kernel compares vfsmounts, not `st_dev`):
   - `main.main` (Jellyfin, read-only-everything, never links — multiple mounts fine):
     `/media/movies` → subPath `30.01_movies` (**readOnly**), `/media/shows` → subPath
     `30.02_tv` (**readOnly**), `/media/music` → subPath `30.03_music` (**readOnly**),
     `/media/rotation` → subPath `rotation` (**readOnly**).
   - `main.transmission`: `/data/downloads` → subPath `rotation/downloads` (rw) — sole
     mount; it never links, and the narrower subPath keeps least privilege while the
     container-side path string matches the *arrs'.
   - `main.radarr`: `/data` → subPath `rotation` (rw) — sole mount; root folder
     `/data/movies`, downloads visible at `/data/downloads`.
   - `main.sonarr`: `/data` → subPath `rotation` (rw) — sole mount; root folder
     `/data/shows`.
3. Add `PUID: "1000"` and `PGID: "1000"` env to every lscr.io container (transmission,
   radarr, sonarr, prowlarr): `root_squash` remaps only uid 0, fsGroup is inert on NFS,
   and linuxserver images otherwise drop to uid 911 → EACCES on `1000:1000/0775` dirs.
   Do NOT set `runAsUser` on these containers — it disables linuxserver's PUID handling.
4. In the `data` PVC `advancedMounts`, remove the media subPaths (`movies`, `shows`,
   `transmission/downloads`, `transmission/downloads/complete`) from all containers —
   `data` keeps config mounts only. Update transmission's config so the download dir is
   `/data/downloads/complete` with incomplete dir `/data/downloads/incomplete`;
   radarr/sonarr download-client paths see identical strings — no remote path mappings.
5. Container-path consistency check: the *arr "Root Folder" settings (runtime config, set
   via each app's UI/API on first setup — see
   `docs/guides/how_to_for_media_management.md`) must point at `/data/movies` and
   `/data/shows`. The guide's Jellyfin library paths change to `/media/movies`,
   `/media/shows` (preserved) + `/media/rotation/{movies,shows}` (update the guide in
   the same release). Document operator promotion in that guide: UID/GID 1000, one NFS
   mount of `server:/mnt/storage/30_media` on an allowed homelab client, and competing
   activity for that item paused. Local repair requires quiescing/unmounting clients.
6. After Task 8, release both charts together through GitOps. Inspect the old PV/PVC
   first; unexpected use or data stops cleanup. Retire the old claim with its consumer
   mounts, then delete the old PV only when Available/Released. Retain keeps NAS data.
   → verify: the new claim binds to `pv-nfs-media`, old unused resources are gone, and
   the replacement pod starts. Record the rendered rollout strategy inherited from
   app-template and its behavior with the retained config PVC.

Verify in this order, rendering before sync and running runtime checks afterward:

1. `helm template apps/jellyfin` — every media mount resolves to the single
   `pvc-nfs-media` claim; Jellyfin's mounts carry `readOnly: true`; radarr/sonarr have
   exactly one media volumeMount each; PUID/PGID env present on all lscr containers.
2. UID proof: inspect the actual Radarr/Sonarr/Transmission process credentials
   (for example, the process's `/proc/<pid>/status`), requiring UID/GID 1000.
   In each writer container, use `s6-setuidgid abc id` and perform a disposable write
   through that same helper. Bare `kubectl exec ... id` tests the exec process,
   usually root, which can write through root-squash even with a wrong app UID.
3. Hardlink proof: in radarr, run the entire quoted probe as `abc`:
   `s6-setuidgid abc sh -c 'touch /data/downloads/complete/.linktest && ln /data/downloads/complete/.linktest /data/movies/.linktest && stat -c %h /data/movies/.linktest'`
   prints `2`; clean up both names. Repeat for sonarr's `/data/shows`. Then import a
   small legal test download using the application itself and prove it linked while
   seeding continues.
4. RO proof: in the jellyfin container, `touch /media/movies/x` fails with EROFS.
5. Run the storage-play command in [nfs-export-readiness](#nfs-export-readiness)
   and confirm its NFS tests execute. `./tests/metal.sh` is a separate cluster/network
   smoke test; it provides no NFS coverage. On final mounts, test promotion/rescan
   and continued seeding using disposable media, then actual playback of migrated
   content from every configured preserved library. Confirm RO enforcement survives
   pod recreation. These application checks are Task 5 acceptance, not Task 11 gates.

## migrated-content-access

Task 7 applies this policy after sorting and before final acceptance/freeze. The
skeleton's ownership does not repair permissions inside copied trees.

| Tier | Required access and metadata policy |
|---|---|
| `30_media/30.01_movies`, `30.02_tv`, `30.03_music` | UID/GID 1000 must list/traverse directories and read every served regular file. The operator needs directory write access for curation. Keep source metadata when compatible; otherwise record the required per-path ownership/mode/ACL transformation before applying it. Service mounts remain RO. |
| `30_media/rotation` | Writers run as 1000:1000; Task 11 proves synthetic writes and Task 5 proves actual imports. It is not a destination for retained migrated content. |
| Backups and other currently unserved tiers | Preserve source restoration metadata and record any deliberate transformation. No blanket recursive ownership/ACL normalization. A future consumer must declare its identity and pass its own access audit before rollout. |

Inventory metadata before repair and put before/expected values in the ledger. If a
served path shares an inode with an archive requiring unchanged metadata, separate
the served copy first and record that transformation; changing shared inode metadata
would also change the archive. Do not silently widen access to documents or backups.

After local changes finish, mount only `30_media` read-only through NFS on an allowed
client and run the helper's `access` probe as 1000:1000. It must inspect actual migrated
paths, not freshly created placeholders. Unmount the audit client afterward; if a
repair is needed, perform it with clients quiesced and rerun the affected checks.
Complete the full final reconciliation against the ledger's expected metadata before
freezing the dataset. Task 5 later verifies the real service identity and playback.

## migration-evidence

Select and record a run ID plus a controller evidence directory on a physical disk
outside the NAS pool and drives A/B/C, with sufficient capacity for inventories/logs.
It is the authoritative workspace and must survive every planned wipe. Keep original
source entries unchanged; a separately named and tracked safety-copy area may receive
new files, including on a surviving source drive, without modifying those originals.

NAS-local audits may spool reports under `/var/log/snapraid/migration/<run-id>/`;
copy each completed generation and current job evidence to the controller workspace
before a wipe. The NAS journal alone is not the independent copy. Preserve dataset
IDs and distinct original/safety-copy inventories so release checks cover both.

`00_meta/migration/` is the NAS archive of evidence. Populate it before Task 7's freeze;
all Task 8 size records, safety-copy receipts, logs, retry results and disposition
updates go only to the controller workspace/NAS spool during the freeze. After release,
archive the completed evidence to `00_meta` and retain its independent copy until the
next normal sync protects those new archive files.

## migration-runbook

Manual/operational, after Task 13's tooling passes and before production consumers
start. Set up the [evidence workspace](#migration-evidence), freeze original source
entries, and stop on any enumeration, read, hash, copy, or reconciliation failure.

1. **Inventory A/B/C before copying.** Use the helper's `inventory` command on each
   attached source, recording disk ID, root and tool versions in the run evidence.
   Publish `driveA.jsonl`, `driveB.jsonl`, `driveC.jsonl` only after complete successful
   scans; each records hashes, entry types and metadata per the tooling contract.
   Check the NAS tool versions against the Task 13 fixture record; setup happened
   before those tests. This remains migration tooling outside the storage role.
   → verify: all scans complete with zero errors and entry counts reconcile; special
   files need an explicit archive/restore or discard decision before release.
2. **Copy A and reconcile.** Run on the NAS with permission to preserve source metadata:
   use `rsync -aHAX --info=progress2 /mnt/driveA/
   /mnt/storage/99_tmp/driveA/`, checking success; never use `--delete`. Inventory that
   copy locally on the NAS into `nas-copy.jsonl` outside the staging tree. Run the
   helper's path comparison against A's inventory.
   → verify: no missing/mismatched entries, including symlinks and empty directories.
3. **Discover B/C deltas.** Use the helper's content comparison to find content missing
   from the NAS; copy it into `99_tmp/driveB_delta/` and `driveC_delta/`, preserving relative
   paths, and hash every new copy. Keep source identities even for equal content:
   a file needed at a second final path must be copied/linked there or explicitly
   deduplicated by the operator. Equality of hashes alone is not a discard decision.
   → verify: every B/C entry has staged content or a recorded proposed disposition.
4. **Sort with collision checks.** Maintain the tooling contract's JSONL ledger,
   recording each source entry's destination/disposition and expected metadata.
   Record moves as they occur; directory-level logs may aid reconstruction but cannot
   replace each entry's final mapping. Before each move, check the destination. If
   differing content collides, stop and choose distinct unnumbered leaf paths or an
   explicit discard; never overwrite. Equal-content deduplication records the retained
   destination for every source entry. Log cruft deletion deliberately.
   Apply the [migrated access policy](#migrated-content-access), record repairs, and
   run its temporary RO access probe. Task 13 already tests the collision/error cases.
   → verify: all media access failures are resolved, transformations are explicit,
   and the audit mount is removed before further local changes or the freeze.
5. **Reconcile everything after sorting.** Run the helper's `verify` command against
   all three source inventories, the ledger and the final tree. It re-hashes all kept
   files and checks expected metadata/links and complete accounting. Remove
   empty staging directories only after their entries are reconciled.
   → verify: `99_tmp` has no unresolved entries of any type, all source entries have
   checked dispositions, and the complete final audit has zero unexplained differences.
   Sampling is optional additional inspection, never the release gate. Store the
   helper revision, invocations, final access results and completed reports as evidence.
6. **Freeze the accepted dataset.** Stop promotions and all writers to included paths
   until Task 8's final full scrub. Cross-check retained destinations against the
   final exclusions rendered in Task 2 (an explicit Task 7 prerequisite). An excluded
   retained item requires its own independent backup or relocation into an included
   path before its source can be released.
   Apply the [evidence-location rule](#migration-evidence) throughout Task 8; the NAS
   archive stays unchanged until release is complete.
   → verify: the ledger and final checksums describe the dataset used for parity.

## parity-enablement

One drive at a time; **drive A last**. Tasks 2, 7, and 12 must be complete. Stop/disable
maintenance timers and wait for running jobs before each configuration transition.
Preserve the frozen included dataset. Every record below goes to the controller
evidence workspace defined in [migration-evidence](#migration-evidence), using the
NAS spool/journal only as a working copy; never update `00_meta` during this sequence.

0. **Parity-size gate (before ANY wipe):** snapraid requires each parity device to be at
   least as large as the largest data branch. All drives are same-model 18TB Seagates
   (owner-confirmed 2026-08-22), so this holds — still, compare `lsblk -b` byte sizes of
   the candidate parity drive vs every `/mnt/data*` device and record the numbers in
   the controller evidence workspace. Abort the wipe if the candidate is smaller.
1. **Per-file redundancy gate before B:** use the ledger to identify retained content
   on B without a verified copy on A/C or another independent surviving device, apart
   from the NAS. Reserve sufficient free space there, copy those deltas into a separate
   safety-copy directory, and read/hash them back. Record disk IDs, paths, hashes and
   free space. No spare capacity or any failed verification means **do not wipe B**.
   → verify: every retained B entry can be recovered if its NAS data disk fails during
   first parity construction; another path/branch on the same physical disk does not count.
2. Wipe drive B (`make -C metal wipe` targets k8s nodes — for the NAS use manual
   `wipefs`/`blkdiscard` per the drive's disk-by-id), add its id under `parity_drives` in
   the sops inventory (`metal/inventory/metal.yml`), run the storage role
   (`make -C metal storage ANSIBLE_TARGETS=yggdrasil`). The role formats/mounts
   `/mnt/parity1`, renders the corrected config and deploys the Task 12 unit; it does
   not start it. Inspect `/etc/snapraid.conf`, excludes, and `snapraid status` here.
   Start `snapraid-initial-sync` explicitly. Record this invocation's journal and
   `systemctl show` result/exit status; wait for successful completion, not file creation.
   → verify: success for the current dataset/configuration, no active competing job,
   and `snapraid diff` reports no included changes before proceeding.
3. **First full scrub:** run `snapraid scrub -p full` and require successful exit, zero
   errors, and complete block coverage in the output/status. The default scrub unit's
   10%/ten-day policy and an age-filtered percentage pass are not substitutes.
   → verify: first parity can protect the retained snapshot before releasing C.
4. **Release C and expand:** repeat identity/size and per-file recovery checks. Coverage
   may now come from the unchanged verified first-parity snapshot; any excluded or
   newly changed retained content still needs an independent copy. Wipe C only after
   that gate, add it as `2-parity`, apply the role, then explicitly run the full-sync
   unit again. Keep first parity/content files intact; do not delete them to trigger a
   first-file guard. Full-scrub again with `snapraid scrub -p full`.
   → verify: both configured levels are initialized, this invocation succeeded, no
   included changes occurred, and all blocks passed the second full scrub.
5. **Release A last:** repeat the per-file recovery check, including safety copies
   placed on A and any retained excluded entries. Only the successful two-level sync
   and full scrub authorize release. Record whether A becomes parity, data, or a cold
   spare. Keep a spare unformatted until needed; adding parity repeats expansion/full
   scrub, and adding a data branch requires another sync/full scrub before protection
   of that changed layout is claimed. Preserve an independent copy of migration evidence.
6. Re-enable maintenance only after recording successful completion. Update
   `snapraid_maintenance` thresholds in role defaults only if the first weeks show
   false-positive aborts — do not pre-tune.

On interruption or any failure: stop later wipes, retain all source/safety copies and
existing parity/content files, diagnose, then restart the explicit job and repeat the
full scrub. Never infer completion from a partial parity file or an earlier unit run.
On unexpected data changes, redo affected checks and sync before accepting the scrub.

## legend-docs

1. Vault legend note (outside this repo, in the Obsidian vault's `000_Infra/001_Legend/`):
   a `cosmarchy_of_the_nas.md`-style note mirroring `00_meta/README.md` — tree, grammar
   rules, working-set test, "machines feed, humans promote". Manual step; the repo-side
   task is only to keep `00_meta/README.md` authoritative.
2. `docs/info/todo.md`: under "Storage Node / NFS Optimizations", add a line pointing to
   `docs/feat/wip/nas-storage-layout/` as the layout source of truth (the "Future shares
   (Pictures, Documents, Music, Backups)" naming in the NFS-review follow-up is
   superseded by this design's names).
3. `docs/guides/how_to_for_media_management.md`: updated as part of
   [jellyfin-remount](#jellyfin-remount) step 5 and the operator-promotion procedure.
→ verify: `python3 -m mkdocs build --strict --site-dir /tmp/ktchn8s-docs-check` completes
without warnings. `make docs` serves a preview and is not a terminating build check.
If unrelated baseline warnings exist, record them and prove no new warnings; do not
silently weaken strict mode. Also check local links in the revised Markdown directly.

## Deferred / follow-ups (explicit)

- **restic policy values** per tier — design names the tiers; concrete
  frequencies/retention are future work (`scripts/backup.py` / backup docs).
- **NFS health monitoring** — pre-existing todo.md item; becomes more urgent once media
  serving depends on the NAS. Not part of this feature.
- **Environment repair:** the existing `.venv/bin/pip` launcher references a differently
  cased `ktchn8S` path. Recreate the virtualenv before dependency-installing checks;
  existing `python3 -m mkdocs` works for this documentation pass. This pre-existing
  environment issue is outside the storage changes.
- **Immich & documents-service deployment** — their mount requirements are binding
  (design.md § Service integration); the deployments are separate features.
