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

Task 11 is a prerequisite to the media rollout. It uses disposable files under
`99_tmp`; clean up its clients before NAS-local migration/sorting begins.

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
4. Document operator promotion in `docs/guides/how_to_for_media_management.md`: use
   one mount of `server:/mnt/storage/30_media` on the NAS or an allowed homelab client,
   operate as UID/GID 1000, pause competing activity for the item, and move between
   paths inside that mount. Do not edit through the NAS-local pool while consumers
   remain mounted. For exceptional local repair, quiesce/unmount those clients first.
   → verify: a client with previously read items can reopen them after promotion and
   rescan; the remaining download hardlink still seeds. With `path-hash`, presented
   inode numbers may differ; use link count and the backing branch's inode identity
   to distinguish a hardlink from a copy.

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

## nfs-media-share

In `system/csi-driver-nfs/values.yaml`, replace the `volumes` entry:

- `name: videos` → `name: media`
- `share: Videos` → `share: 30_media`
- `capacity: 1Ti` → `capacity: 4Ti` (nominal for NFS; must be ≥ any bound PVC request)

This renders PV `pv-nfs-media` (template `templates/pv-nfs.yaml` derives the name).
`spec.nfs`/`volumeHandle` are immutable on an existing PV — but per todo.md the stack has
never run; if `pv-nfs-videos` exists in the cluster in `Available`/`Released` state,
delete it (reclaim policy is `Retain`; nothing on the NAS is touched).
→ verify: `helm template system/csi-driver-nfs | grep -A3 volumeHandle` shows
`…/mnt/storage/30_media`; after ArgoCD sync, `kubectl get pv pv-nfs-media` exists and
`pv-nfs-videos` is gone.

Complete Task 8's parity acceptance and Task 11's export checks before production sync;
Task 5's promotion tests must run after the included-data freeze ends.
Land this and the [jellyfin remount](#jellyfin-remount) in **one commit/sync window**: if
this change syncs alone, the still-deployed jellyfin chart claims the now-deleted
`pv-nfs-videos` and degrades until the remount lands (self-healing, but avoidable).

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
   the same commit).

→ verify (render before sync; runtime checks after sync, in order):
  a. `helm template apps/jellyfin` — every media mount resolves to the single
     `pvc-nfs-media` claim; Jellyfin's mounts carry `readOnly: true`; radarr/sonarr have
     exactly one media volumeMount each; PUID/PGID env present on all lscr containers.
  b. UID proof: inspect the actual Radarr/Sonarr/Transmission process credentials
     (for example, the process's `/proc/<pid>/status`), requiring UID/GID 1000.
     In each writer container, use `s6-setuidgid abc id` and perform a disposable write
     through that same helper. Bare `kubectl exec ... id` tests the exec process,
     usually root, which can write through root-squash even with a wrong app UID.
  c. Hardlink proof: in radarr, run the entire quoted probe as `abc`:
     `s6-setuidgid abc sh -c 'touch /data/downloads/complete/.linktest && ln /data/downloads/complete/.linktest /data/movies/.linktest && stat -c %h /data/movies/.linktest'`
     prints `2`; clean up
     both names. Repeat for sonarr's `/data/shows`. Then import a small legal test
     download using the application itself and prove it linked while seeding continues.
  d. RO proof: in the jellyfin container, `touch /media/movies/x` fails with EROFS.
  e. Run the storage-play command in [nfs-export-readiness](#nfs-export-readiness)
     and confirm its NFS tests execute. `./tests/metal.sh` is a separate cluster/network
     smoke test; it provides no NFS coverage. Repeat the reopen/promotion checks with
     the final mounts and confirm RO enforcement survives pod recreation.

## migration-runbook

Manual/operational, before production NFS consumers start. Create
`/mnt/storage/00_meta/migration/`; keep a second copy of its evidence on a surviving
independent device, outside the source dataset being inventoried. Freeze source writes
and stop on any enumeration, read, hash, copy, or reconciliation failure.

1. **Inventory A/B/C before copying.** Record source disk-by-id and mount, tool versions,
   regular-file hashes, symlink text, directory entries/metadata, and other file types.
   Generate `driveA.b3`, `driveB.b3`, and `driveC.b3` at their attached machines; a failed
   or partial scan is not a valid manifest. Use NUL-safe enumeration and the checksum
   tool's escaped filename format/checker; do not parse filenames by whitespace or
   silently omit non-regular entries. Never follow source symlinks during inventory.
   Install `b3sum` once on the NAS (`apt install b3sum` on Debian, or a verified upstream
   binary) and record the version. This remains a migration tool outside the role.
   → verify: all scans complete with zero errors and entry counts reconcile; special
   files need an explicit archive/restore or discard decision before release.
2. **Copy A and reconcile.** Use `rsync -aHAX --info=progress2 /mnt/driveA/
   /mnt/storage/99_tmp/driveA/`, checking success; never use `--delete`. Generate
   `nas-copy.b3` locally on the NAS, outside the hashed staging tree. Compare all A
   regular-file hashes and inventory entries against the copy.
   → verify: no missing/mismatched entries, including symlinks and empty directories.
3. **Discover B/C deltas.** Compare validated hash-sets to find content missing from
   the NAS; copy it into `99_tmp/driveB_delta/` and `driveC_delta/`, preserving relative
   paths, and hash every new copy. Keep source identities even for equal content:
   a file needed at a second final path must be copied/linked there or explicitly
   deduplicated by the operator. Equality of hashes alone is not a discard decision.
   → verify: every B/C entry has staged content or a recorded proposed disposition.
4. **Sort with collision checks.** Maintain an escaped, machine-readable ledger (JSONL)
   with source disk ID, relative source path, entry type, source hash/link text,
   final path, disposition (`keep`, `deduplicate`, `discard`), and decision reason.
   Record moves as they occur; directory-level logs may aid reconstruction but cannot
   replace each entry's final mapping. Before each move, check the destination. If
   differing content collides, stop and choose distinct unnumbered leaf paths or an
   explicit discard; never overwrite. Equal-content deduplication records the retained
   destination for every source entry. Log cruft deletion deliberately.
   → verify on a small fixture first: different contents with the same destination,
   equal contents at required distinct paths, nested moves, spaces/newlines in names,
   dangling symlinks, and a failed hash must not silently lose an entry.
5. **Reconcile everything after sorting.** Re-read every retained regular file at its
   final path and compare its source hash; verify symlink targets and directory
   metadata, including any explicit transformations. Reject missing entries, unlogged
   discards, destination collisions, unresolved paths and checksum failures. Remove
   empty staging directories only after their entries are reconciled.
   → verify: `99_tmp` has no unresolved entries of any type, all source entries have
   checked dispositions, and the complete final audit has zero unexplained differences.
   Sampling is optional additional inspection, never the release gate. Store the exact
   audit commands/helper used and its output with the manifests for reproducibility.
6. **Freeze the accepted dataset.** Stop promotions and all writers to included paths
   until Task 8's final full scrub. Cross-check retained destinations against the
   rendered SnapRAID excludes; an excluded retained item requires its own independent
   backup or relocation into an included path before its source can be released.
   During parity work, write new job logs/evidence outside the pool (NAS journal and
   the independent evidence device), so updating `00_meta` cannot change the snapshot
   under verification. Archive those logs into `00_meta/migration/` after release;
   their independent copy protects them until the next normal parity sync.
   → verify: the ledger and final checksums describe the dataset used for parity.

## parity-enablement

One drive at a time; **drive A last**. Tasks 2, 7, and 12 must be complete. Stop/disable
maintenance timers and wait for running jobs before each configuration transition.
Preserve the frozen included dataset and the independently stored audit evidence.

0. **Parity-size gate (before ANY wipe):** snapraid requires each parity device to be at
   least as large as the largest data branch. All drives are same-model 18TB Seagates
   (owner-confirmed 2026-08-22), so this holds — still, compare `lsblk -b` byte sizes of
   the candidate parity drive vs every `/mnt/data*` device and record the numbers in
   `00_meta/migration/`. Abort the wipe if the candidate is smaller.
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
