# Tasks: NAS Storage Directory Layout

> Design: [./design.md](./design.md)
> Implementation: [./implementation.md](./implementation.md)
> Status: pending
> Created: 2026-08-22
> Revised: 2026-10-03 — corroborated review fixes; all implementation/operational tasks remain pending
> Not Doing: SMB shares, documents-service selection (Nextcloud/Copyparty/OpenCloud), Plex/second media service, automated photo promotion, vault reorganization, ZFS migration planning, Gitea code-archive extraction, restic policy values, NFS health monitoring

Tasks 11 and 12 add prerequisites while preserving existing task IDs. Parallel markers
describe independent repository work; serialize NAS role applications, remounts, and
parity jobs. Production media sync waits for Task 8 so local sorting cannot bypass live
NFS clients and promotion tests cannot change the snapshot under verification. Keep
parity-included content frozen from Task 7 through Task 8.

## Task 1: Tree skeleton via storage role
- **Status:** pending
- **Depends on:** —
- **Size:** M
- **Can run in parallel with:** Task 2, Task 3, Task 12
- **Docs:** [implementation.md#tree-skeleton](./implementation.md#tree-skeleton)

### Subtasks
- [ ] 1.1 Replace `storage_dirs` in `metal/roles/storage/vars/main.yml` with the designed tree as a flat path list (top-level dirs, `NN.MM` subdirs, `30_media/rotation/{movies,shows}`, `30_media/rotation/downloads/{complete,incomplete}` — downloads nests INSIDE rotation, `10_documents/inbox`)
- [ ] 1.2 Ensure the `storage_dirs` loop in `tasks/nfs.yml` sets owner/group `1000:1000`, mode `0775`
- [ ] 1.3 Add `templates/storage-readme.j2` (legend: grammar rules, working-set test, machine-vs-human convention) rendered to `00_meta/README.md` from the same variable; create `00_meta/RETIRED.md` with `force: false`
- [ ] 1.4 Grep the role for references to old dirs (`Temp`, `Videos` in validation tasks) and repoint to `99_tmp`
- [ ] 1.5 Run the role against the NAS twice: second run reports zero changes for the layout/legend tasks (the pre-existing `sensors-detect` task always changes); manually remove only confirmed-empty legacy dirs and verify the new tree

## Task 2: SnapRAID excludes and parity configuration
- **Status:** pending
- **Depends on:** —
- **Size:** S
- **Can run in parallel with:** Task 1, Task 3, Task 6, Task 7, Task 9, Task 11
- **Docs:** [implementation.md#snapraid-excludes](./implementation.md#snapraid-excludes)

### Subtasks
- [ ] 2.1 Add root-anchored `/30_media/rotation/`, `/10_documents/inbox/`, `/99_tmp/` excludes with rationale to `metal/roles/storage/templates/snapraid.conf.j2`; remove generic `downloads/` and `appdata/` excludes
- [ ] 2.2 Correct additional parity directives/filenames to use `loop.index`: `parity`, `2-parity`, `3-parity`, with no repeated first level
- [ ] 2.3 Render and parse one-, two-, and three-parity configs offline in disposable SnapRAID 13.0 fixtures; assert exact paths, included backup `downloads`/`appdata` paths, and rejection of duplicate first parity; the live config check belongs to Task 8 because the role skips it with no parity drives

## Task 3: b3sum in the dev shell
- **Status:** pending
- **Depends on:** —
- **Size:** S
- **Can run in parallel with:** Task 1, Task 2, Task 9, Task 11, Task 12
- **Docs:** [implementation.md#devshell-b3sum](./implementation.md#devshell-b3sum)

### Subtasks
- [ ] 3.1 Add `b3sum` to `devShells.default` packages in `flake.nix`
- [ ] 3.2 Verify `nix develop -c b3sum --version`

## Task 4: NFS media PV (csi-driver-nfs)
- **Status:** pending
- **Depends on:** Task 8, Task 11
- **Size:** S
- **Can run in parallel with:** Task 9
- **Docs:** [implementation.md#nfs-media-share](./implementation.md#nfs-media-share)
- **Note:** land Tasks 4 and 5 in ONE commit/sync window — Task 4 alone leaves the deployed chart claiming the deleted `pv-nfs-videos` (transient degradation)

### Subtasks
- [ ] 4.1 In `system/csi-driver-nfs/values.yaml` replace the `videos` volume entry with `media` / share `30_media` / capacity 4Ti
- [ ] 4.2 Delete stale `pv-nfs-videos` from the cluster if present (Retain policy — NAS data untouched)
- [ ] 4.3 Verify: `helm template` renders `pv-nfs-media` with volumeHandle `…/mnt/storage/30_media`; after ArgoCD sync `kubectl get pv pv-nfs-media` exists

## Task 5: Jellyfin stack remount end-to-end
- **Status:** pending
- **Depends on:** Task 4
- **Size:** M
- **Can run in parallel with:** Task 9
- **Docs:** [implementation.md#jellyfin-remount](./implementation.md#jellyfin-remount)

### Subtasks
- [ ] 5.1 Rename `apps/jellyfin/templates/pvc-videos.yaml` → `pvc-media.yaml` binding `pvc-nfs-media` → `pv-nfs-media`
- [ ] 5.2 Rework `persistence` in `apps/jellyfin/values.yaml`: single NFS claim; **ONE volumeMount per linking container** (radarr `/data`→subPath `rotation`; sonarr `/data`→subPath `rotation`; transmission `/data/downloads`→subPath `rotation/downloads`; Jellyfin all-`readOnly` incl. `/media/music`→`30.03_music`); strip media subPaths from the Ceph `data` PVC (configs only)
- [ ] 5.3 Add `PUID: "1000"`/`PGID: "1000"` env to all lscr.io containers (transmission, radarr, sonarr, prowlarr); no `runAsUser` on them
- [ ] 5.4 Update transmission download-dir config to `/data/downloads/complete` + `/data/downloads/incomplete`; *arr root folders `/data/movies`, `/data/shows`
- [ ] 5.5 Update `docs/guides/how_to_for_media_management.md` (root folders, Jellyfin library paths, operator promotion through one NFS share mount)
- [ ] 5.6 Render before sync: one media mount per linking container, RO flags and PUID/PGID. After sync inspect actual service credentials, run UID/write/link probes through `s6-setuidgid abc` in each writer, and perform a real application import while seeding continues; require EROFS in Jellyfin
- [ ] 5.7 Run `make -C metal storage ANSIBLE_TARGETS=yggdrasil ANSIBLE_ARGS='-e validate_nfs=true'` with a working kubeconfig and require the NFS tests to execute; repeat Task 11's reopen/promotion checks on final mounts. Keep `./tests/metal.sh` identified separately as a network smoke test

## Task 6: Migration — copy & cross-drive verification (manual ops)
- **Status:** pending
- **Depends on:** Task 1, Task 3, Task 11
- **Size:** M
- **Can run in parallel with:** Task 2, Task 9, Task 12
- **Docs:** [implementation.md#migration-runbook](./implementation.md#migration-runbook)

### Subtasks
- [ ] 6.1 Freeze and inventory A/B/C before copying: disk IDs, all entry types/metadata, hashes of regular files (including A), symlink text; install/record `b3sum` on the NAS. Abort on any failed or partial enumeration/hash
- [ ] 6.2 rsync A → `99_tmp/driveA/` (`-aHAX`, no `--delete`), hash locally on the NAS and reconcile all copied entries against A; keep manifests/evidence under `00_meta/migration/` and on an independent surviving device
- [ ] 6.3 Compare hash-sets, copy and checksum unique B/C content into `99_tmp/drive{B,C}_delta/`; record every source/path identity, including equal-content files with distinct required destinations, in the runbook's JSONL ledger

## Task 7: Migration — sort into numbered homes (manual ops)
- **Status:** pending
- **Depends on:** Task 6
- **Size:** M
- **Can run in parallel with:** Task 2, Task 9, Task 12
- **Docs:** [implementation.md#migration-runbook](./implementation.md#migration-runbook)

### Subtasks
- [ ] 7.1 Validate the audit procedure on fixtures (colliding versions, required duplicate paths, nested moves, unusual filenames, symlinks, hash failures); save the exact helper/commands with migration evidence
- [ ] 7.2 Move content per the mapping, stopping before any collision; record per-entry final paths and keep/deduplicate/discard decisions. Preserve differing versions at distinct leaf paths unless explicitly discarded
- [ ] 7.3 Delete approved cruft with source identity and reason recorded; exhaustively re-hash final regular files and reconcile symlinks/directory metadata and every source disposition. No sample-only acceptance
- [ ] 7.4 Require no unresolved staging entries, zero unexplained differences, and evidence backed up independently; check retained content against parity excludes and freeze included paths through Task 8

## Task 8: Parity enablement & drive release (manual ops)
- **Status:** pending
- **Depends on:** Task 2, Task 7, Task 12
- **Size:** M
- **Can run in parallel with:** Task 9
- **Docs:** [implementation.md#parity-enablement](./implementation.md#parity-enablement)

### Subtasks
- [ ] 8.1 Check candidate identity/byte size and recoverability of every retained B entry; reserve independent space and copy/read-verify B-only deltas to a surviving device before B's wipe. Insufficient capacity or a failed check blocks release
- [ ] 8.2 Stop/disable maintenance and await running jobs; wipe B only after the gate, add first parity, apply the role and inspect live config/excludes. Explicitly start the Task 12 unit and record this invocation's successful exit/logs; require unchanged included data
- [ ] 8.3 Run `snapraid scrub -p full`; require successful exit, zero errors and full coverage before C's wipe. Preserve sources/safety copies on failure; never accept the routine 10% scrub unit
- [ ] 8.4 Repeat C's per-file recovery/size checks, add `2-parity`, run the full-sync unit again without deleting prior parity/content, then full-scrub both levels and record completion
- [ ] 8.5 Release A last only after the two-level sync/scrub and a recovery check covering safety copies and excluded retained items; record its role. Leave a cold spare unformatted; parity/data expansion requires a further sync/full scrub before claiming protection
- [ ] 8.6 Re-enable maintenance only after acceptance; preserve independent migration evidence and record interruption/retry results and any capacity limits encountered

## Task 9: Legend & docs
- **Status:** pending
- **Depends on:** Task 1
- **Size:** S
- **Can run in parallel with:** Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8, Task 11, Task 12
- **Docs:** [implementation.md#legend-docs](./implementation.md#legend-docs)

### Subtasks
- [ ] 9.1 Write the vault legend note (manual, in Obsidian vault) mirroring `00_meta/README.md`
- [ ] 9.2 Point `docs/info/todo.md` storage section at `docs/feat/wip/nas-storage-layout/` (supersedes "Future shares (Pictures, Documents, Music, Backups)" naming)
- [ ] 9.3 Run `python3 -m mkdocs build --strict --site-dir /tmp/ktchn8s-docs-check` and check revised local links; document any unrelated baseline warnings rather than weakening the check

## Task 11: NFS export lifecycle acceptance
- **Status:** pending
- **Depends on:** Task 1
- **Size:** M
- **Can run in parallel with:** Task 2, Task 3, Task 9, Task 12
- **Docs:** [implementation.md#nfs-export-readiness](./implementation.md#nfs-export-readiness)
- **Slicing:** Risk-First — settle export behavior before data migration and production consumers

### Subtasks
- [ ] 11.1 Update `metal/roles/storage/tasks/mergerfs.yml` with `noforget`, `inodecalc=path-hash`, normal unmount behavior, and removal of `use_ino`; apply with clients quiesced and inspect active options
- [ ] 11.2 Extend NFS/Kubernetes validation tasks using `99_tmp` fixtures: UID-1000 nested creation/link/rename/delete, two-client reopen after idle and remount/recovery, RO rejection, NAS memory observation; correct the test pod's trailing `&&` and require tests actually execute
- [ ] 11.3 Retain `root_squash`; prove required fixed-owner operations and record results. Permission or stale-handle failures block production rollout and require a design revision, not silent privilege relaxation
- [ ] 11.4 Document/test operator promotion through one scoped NFS mount; prove reopened content and backing hardlinks, then tear down all validation clients before Task 6's local migration

## Task 12: Explicit parity bootstrap and expansion jobs
- **Status:** pending
- **Depends on:** Task 2
- **Size:** M
- **Can run in parallel with:** Task 1, Task 3, Task 6, Task 7, Task 9, Task 11
- **Docs:** [implementation.md#parity-job-readiness](./implementation.md#parity-job-readiness)

### Subtasks
- [ ] 12.1 Update `tasks/snapraid.yml`, `tasks/snapraid_initial_sync.yml` and `handlers/main.yml`: always deploy the bootstrap unit, remove the first-parity-file completion guard and automatic config-change start, require explicit operator start after safety gates
- [ ] 12.2 Update `templates/snapraid-initial-sync.service.j2` to invoke `snapraid --force-full sync` directly with journal output and no fixed 12-hour timeout; maintenance timers/handlers must respect stopped/disabled state during bootstrap
- [ ] 12.3 In disposable multi-filesystem fixtures prove initial creation, adding second parity, interruption/retry and nonzero-exit propagation; applying config must not start jobs, and role reruns must not reactivate disabled maintenance

## Task 10: Final verification
- **Status:** pending
- **Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8, Task 9, Task 11, Task 12
- **Size:** S
- **Can run in parallel with:** —

### Subtasks
- [ ] 10.1 Run `/kk:test` — layout-task idempotency, offline parity configs and job lifecycle, complete migration/release evidence, explicit NFS/app identity/import/reopen/RO proofs, separate network smoke test, strict docs build
- [ ] 10.2 Run `/kk:document` — finalize docs, move feature out of wip when done
- [ ] 10.3 Run `/kk:review-code` — review the ansible/helm/nix changes
- [ ] 10.4 Run `/kk:review-spec` — verify implementation matches design/implementation docs

## Dependency Graph

```
Task 1 ─→ Task 11 ─→ Task 6 ─→ Task 7 ─→ Task 8 ─→ Task 4 ─→ Task 5
   │                   ↑                  ↑
   └─→ Task 9          │                  │
Task 3 ────────────────┘                  │
Task 2 ─→ Task 12 ────────────────────────┘

All Tasks 1–9, 11, 12 ─→ Task 10
(Task 6 also depends directly on Task 1; Task 4 on Task 11;
 Task 8 on Task 2. Tasks 6–8 are manual/operational.)
```
