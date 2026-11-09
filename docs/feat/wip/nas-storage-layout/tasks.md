# Tasks: NAS Storage Directory Layout

> Design: [./design.md](./design.md)
> Implementation: [./implementation.md](./implementation.md)
> Status: in-progress
> Created: 2026-08-22
> Revised: 2026-11-09 — Tasks 1–4, 9 and 11–13 complete; migration, media rollout and final verification remain pending
> Not Doing: SMB shares, documents-service selection (Nextcloud/Copyparty/OpenCloud), Plex/second media service, automated photo promotion, vault reorganization, ZFS migration planning, Gitea code-archive extraction, restic policy values, NFS health monitoring

Tasks 11–13 add prerequisites while preserving existing task IDs. Parallel markers
describe independent repository work; serialize NAS role applications, remounts, and
parity jobs. Production media sync waits for Task 8 so local sorting cannot bypass live
NFS clients and promotion tests cannot change the snapshot under verification. Keep
parity-included content frozen from Task 7 through Task 8.

Execution outline: prepare the layout and tools (1–3), prove synthetic NFS behavior
(11), finish audit tooling (13), migrate/reconcile (6–7), initialize/verify parity
(8, after 12), then jointly release media (5, using the offline PV work from 4).
Task 4 can finish offline on a work branch; Task 5 owns all live acceptance and sync.

Molecule covers the isolated role lifecycle checks in Tasks 11–12, with Task 13
reusing the NFS fixture for its identity-sensitive access test. Task 3 supplies the
tooling. Follow [the scenario contract](./implementation.md#molecule-testing);
passing a disposable scenario does not complete any deferred live acceptance.

The [acceptance summary](./reviews/guided-execution-2026-11-08.md) records the completed live gates and verification limits. Raw execution records and audit reports remain private under the ignored `.nas-audit-evidence/` directory.

## Task 1: Tree skeleton via storage role
- **Status:** done
- **Repository work:** done; live acceptance completed 2026-11-09
- **Depends on:** —
- **Size:** M
- **Can run in parallel with:** Task 2, Task 3, Task 12
- **Docs:** [implementation.md#tree-skeleton](./implementation.md#tree-skeleton)

### Subtasks
- [x] 1.1 Replace `storage_dirs` in `metal/roles/storage/vars/main.yml` with the designed tree as a flat path list (top-level dirs, `NN.MM` subdirs, `30_media/rotation/{movies,shows}`, `30_media/rotation/downloads/{complete,incomplete}` — downloads nests INSIDE rotation, `10_documents/inbox`)
- [x] 1.2 Ensure the `storage_dirs` loop in `tasks/nfs.yml` sets owner/group `1000:1000`, mode `0775`
- [x] 1.3 Add `templates/storage-readme.j2` (legend: grammar rules, working-set test, machine-vs-human convention) rendered to `00_meta/README.md` from the same variable; create `00_meta/RETIRED.md` with `force: false`
- [x] 1.4 Grep the role for references to old dirs (`Temp`, `Videos` in validation tasks) and repoint to `99_tmp`
- [x] 1.5 Run the role against the NAS twice: second run reports zero changes for the layout/legend tasks (the pre-existing `sensors-detect` task always changes); manually remove only confirmed-empty legacy dirs and verify the new tree

### Execution context

**Accepted 2026-11-09:** The operator completed the constrained preview, coordinated
normal mount transition and two storage-role applications. All 40 layout entries,
the legend and retirement file were unchanged on the second application; only
the existing sensors task changed. Confirmed-empty legacy entries were removed
and absence was checked on the pool and every branch. Routine role execution
still does not delete legacy data.

Earlier local layout/legend checks and the disposable NFS scenario covered
ownership, modes, idempotence and preservation of existing data and retirement
entries. They were separate from the now-completed live gate. See the
[Task 1 acceptance evidence](./reviews/guided-execution-2026-11-08.md#task-1-live-acceptance-complete-2026-11-09).

## Task 2: SnapRAID excludes and parity configuration
- **Status:** done
- **Depends on:** —
- **Size:** S
- **Can run in parallel with:** Task 1, Task 3, Task 4, Task 6, Task 9, Task 11, Task 13
- **Docs:** [implementation.md#snapraid-excludes](./implementation.md#snapraid-excludes)

### Subtasks
- [x] 2.1 Add root-anchored `/30_media/rotation/`, `/10_documents/inbox/`, `/99_tmp/` excludes with rationale to `metal/roles/storage/templates/snapraid.conf.j2`; remove generic `downloads/` and `appdata/` excludes
- [x] 2.2 Correct additional parity directives/filenames to use `loop.index`: `parity`, `2-parity`, `3-parity`, with no repeated first level
- [x] 2.3 Render and parse one-, two-, and three-parity configs offline in disposable SnapRAID 13.0 fixtures; assert exact paths, included backup `downloads`/`appdata` paths, and rejection of duplicate first parity; the live config check belongs to Task 8 because the role skips it with no parity drives

**Verified 2026-10-04:** The three config tests passed against SnapRAID 13.0:
root-only exclusions, preservation of same-named backup paths, correct additional
parity levels and rejection of duplicate first parity. No live parity computation
was performed. The role skips parity configuration while no parity drives are
assigned; live configuration, sync and full-scrub evidence remain Task 8. See
[the fixture commands and limits](./implementation.md#snapraid-excludes).

## Task 3: Storage test tooling in the dev shell
- **Status:** done
- **Depends on:** —
- **Size:** S
- **Can run in parallel with:** Task 1, Task 2, Task 4, Task 9
- **Docs:** [implementation.md#devshell-b3sum](./implementation.md#devshell-b3sum)

### Subtasks
- [x] 3.1 Add `b3sum` to `devShells.default` packages in `flake.nix`
- [x] 3.2 Verify `nix develop -c b3sum --version`
- [x] 3.3 Add a Molecule package compatible with the locked Ansible/Python environment to `devShells.default` in `flake.nix`; use the pinned Nix package set rather than a global pip install
- [x] 3.4 Verify `nix develop -c molecule --version` and scenario CLI availability; record the resolved versions. VM backend setup and actual scenario passes belong to Tasks 11–12

**Verified 2026-10-04:** The locked x86_64-linux toolchain provides b3sum 1.8.2,
Molecule 25.11.1, Ansible Core 2.19.4, Python 3.13.11 and molecule-plugins 23.5.3.
Version/help checks and flake evaluation passed; other platforms were not checked.
CLI availability alone did not establish VM capabilities or live acceptance.
The existing virtualenv-launcher issue remains an
[environment follow-up](./implementation.md#deferred-follow-ups-explicit).

## Task 4: Prepare the NFS media PV offline
- **Status:** done
- **Depends on:** Task 1
- **Size:** S
- **Can run in parallel with:** Task 2, Task 3, Task 6, Task 7, Task 8, Task 9, Task 11, Task 12, Task 13
- **Docs:** [implementation.md#nfs-media-share](./implementation.md#nfs-media-share)
- **Slicing:** Contract-First — prepare the binding contract; Task 5 owns deployment
- **Note:** Complete through offline rendering on a non-deployed work branch. Release together with Task 5 after parity acceptance; no deletion or sync belongs to Task 4

### Subtasks
- [x] 4.1 In `system/csi-driver-nfs/values.yaml` replace the `videos` volume entry with `media` / share `30_media` / capacity 4Ti
- [x] 4.2 Verify offline: `helm template` renders `pv-nfs-media` with volumeHandle `…/mnt/storage/30_media`, capacity 4Ti and Retain policy; leave cluster resources unchanged

**Verified 2026-10-04:** Helm 3.19.1 lint/render checks passed with the cached
csi-driver-nfs 4.13.0 dependency. Only the PV name, capacity, CSI handle and share
changed; Retain, ReadWriteMany, static class-less binding and mount options were
preserved. Kubernetes schema validation was unavailable because kubeconform was
absent. This was offline preparation on the feature branch: Task 5 still owns
joint release, binding, old-resource cleanup and application acceptance after
Task 8. See [the rendering contract](./implementation.md#nfs-media-share).

## Task 5: Jellyfin stack remount end-to-end
- **Status:** pending
- **Depends on:** Task 4, Task 8
- **Size:** M
- **Can run in parallel with:** Task 9
- **Docs:** [implementation.md#jellyfin-remount](./implementation.md#jellyfin-remount)

### Subtasks
- [ ] 5.1 Rename `apps/jellyfin/templates/pvc-videos.yaml` → `pvc-media.yaml` binding `pvc-nfs-media` → `pv-nfs-media`
- [ ] 5.2 Rework `persistence` in `apps/jellyfin/values.yaml`: single NFS claim; **ONE volumeMount per linking container** (radarr `/data`→subPath `rotation`; sonarr `/data`→subPath `rotation`; transmission `/data/downloads`→subPath `rotation/downloads`; Jellyfin all-`readOnly` incl. `/media/music`→`30.03_music`); strip media subPaths from the Ceph `data` PVC (configs only)
- [ ] 5.3 Add `PUID: "1000"`/`PGID: "1000"` env to all lscr.io containers (transmission, radarr, sonarr, prowlarr); no `runAsUser` on them
- [ ] 5.4 Update transmission download-dir config to `/data/downloads/complete` + `/data/downloads/incomplete`; *arr root folders `/data/movies`, `/data/shows`
- [ ] 5.5 Update the media-management guide with paths and the operator promotion procedure; render both charts and record the inherited rollout strategy
- [ ] 5.6 After Task 8, release both charts together, retire old consumer mounts/claim, and delete the unused old PV only after its state is safe; verify new binding and replacement-pod startup per the implementation plan
- [ ] 5.7 Complete all live acceptance in `implementation.md#jellyfin-remount`: real app credentials/import/hardlinks/seeding, promotion/rescan, actual migrated-library playback, RO after recreation, and explicitly executed NFS tests. Network smoke testing remains separate



## Task 6: Migration — copy & cross-drive verification (manual ops)
- **Status:** pending
- **Depends on:** Task 1, Task 3, Task 11, Task 13
- **Size:** M
- **Can run in parallel with:** Task 2, Task 4, Task 9, Task 12
- **Docs:** [implementation.md#migration-runbook](./implementation.md#migration-runbook)

### Subtasks
- [ ] 6.1 Establish `implementation.md#migration-evidence` workspace; freeze original source entries and use Task 13's tested helper to publish complete A/B/C JSONL inventories, recording NAS Python/b3sum versions
- [ ] 6.2 Copy A locally to `99_tmp/driveA/` with metadata preservation, inventory/hash the copy on the NAS, and use path comparison to reconcile all entries; publish evidence to the independent workspace
- [ ] 6.3 Use content comparison to discover B/C deltas, copy/read-verify them, and record all source/path identities and proposed dispositions in the ledger; stop on execution/incomplete-input errors

### Execution context

No real source has been mounted, inventoried or copied in this guided work.
Tasks 1, 3, 11 and 13 now satisfy the tooling/storage prerequisites, but the owner
stopped before migration. On resumption, the owner must reconcile the A/B/C labels,
logical source relationships and independent recovery copies with the actual
sources before mounting or copying anything. Preserve original data and RAID/LVM
structures. The assistant prepares reviewed batches; the owner executes them.

## Task 7: Migration — sort into numbered homes (manual ops)
- **Status:** pending
- **Depends on:** Task 2, Task 6
- **Size:** M
- **Can run in parallel with:** Task 4, Task 9, Task 12
- **Docs:** [implementation.md#migration-runbook](./implementation.md#migration-runbook)

### Subtasks
- [ ] 7.1 Curate/move content per the mapping with collision stops and explicit keep/deduplicate/discard records; tooling fixtures must already have passed Task 13
- [ ] 7.2 Apply `implementation.md#migrated-content-access`: record necessary permission/ACL transformations, preserve archive metadata, and prove actual migrated-media reads as UID/GID 1000 through a temporary RO NFS mount; remove that client afterward
- [ ] 7.3 Run the helper's complete final reconciliation; require metadata/content/disposition checks and access acceptance against the same ledger generation, with no unresolved staging entries
- [ ] 7.4 Check retained content against Task 2's finalized exclusions, archive the accepted evidence before the freeze, and follow `implementation.md#migration-evidence` through Task 8



## Task 8: Parity enablement & drive release (manual ops)
- **Status:** pending
- **Depends on:** Task 2, Task 7, Task 12
- **Size:** M
- **Can run in parallel with:** Task 4, Task 9
- **Docs:** [implementation.md#parity-enablement](./implementation.md#parity-enablement)

### Subtasks
- [ ] 8.1 Check candidate identity/byte size and recoverability of every retained B entry; reserve independent space and copy/read-verify B-only deltas to a surviving device before B's wipe. Insufficient capacity or a failed check blocks release
- [ ] 8.2 Stop/disable maintenance and await running jobs; wipe B only after the gate, add first parity, apply the role and inspect live config/excludes. Explicitly start the Task 12 unit and record this invocation's successful exit/logs; require unchanged included data
- [ ] 8.3 Run `snapraid scrub -p full`; require successful exit, zero errors and full coverage before C's wipe. Preserve sources/safety copies on failure; never accept the routine 10% scrub unit
- [ ] 8.4 Repeat C's per-file recovery/size checks, add `2-parity`, run the full-sync unit again without deleting prior parity/content, then full-scrub both levels and record completion
- [ ] 8.5 Release A last only after the two-level sync/scrub and a recovery check covering safety copies and excluded retained items; record its role. Leave a cold spare unformatted; parity/data expansion requires a further sync/full scrub before claiming protection
- [ ] 8.6 Write all size/safety-copy/job/retry/disposition records to the controller evidence workspace during the freeze; after release archive them to `00_meta`, keep the independent copy, and re-enable maintenance



## Task 9: Legend & docs
- **Status:** done
- **Depends on:** Task 1
- **Size:** S
- **Can run in parallel with:** Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8, Task 11, Task 12, Task 13
- **Docs:** [implementation.md#legend-docs](./implementation.md#legend-docs)

### Subtasks
- [x] 9.1 Write the vault legend note (manual, in Obsidian vault) mirroring `00_meta/README.md`
- [x] 9.2 Point `docs/info/todo.md` storage section at `docs/feat/wip/nas-storage-layout/` (supersedes "Future shares (Pictures, Documents, Music, Backups)" naming)
- [x] 9.3 Run `python3 -m mkdocs build --strict --site-dir /tmp/ktchn8s-docs-check` and check revised local links; document any unrelated baseline warnings rather than weakening the check

**Accepted 2026-11-08:** The vault legend was matched to the generated 40-directory
tree and policy sections, repository references were updated, and archived-review
links were repaired. Strict MkDocs, 71 local links/anchors, rendered-legend equality
and vault metadata checks passed. Earlier documentation warnings are resolved.
The NAS-generated legend remains authoritative; media rollout documentation still
belongs to Task 5. No NAS deployment was inferred from these documentation checks.

## Task 11: NFS export lifecycle acceptance
- **Status:** done
- **Repository work:** done; live lifecycle, Kubernetes and teardown acceptance completed 2026-11-09
- **Depends on:** Task 1, Task 3
- **Size:** M
- **Can run in parallel with:** Task 2, Task 4, Task 9, Task 12
- **Docs:** [implementation.md#nfs-export-readiness](./implementation.md#nfs-export-readiness)
- **Slicing:** Risk-First — settle export behavior before data migration and production consumers
- **Offline scope:** Task 1.1–1.4 plus Task 3 suffice for scenario work; Task 1.5 is required before live NAS acceptance. Keep offline and live results separate

### Subtasks
- [x] 11.1 Update `metal/roles/storage/tasks/mergerfs.yml` with `noforget`, `inodecalc=path-hash`, normal unmount behavior, and removal of `use_ino`; prove active options in the Molecule guest
- [x] 11.2 Extend NFS/Kubernetes validation using `99_tmp` fixtures and a shared UID-1000 probe; require actual successful pod completion and kubeconfig availability. Prove two-client idle/reopen, remount/recovery, RO rejection and memory reporting in Molecule; render the Kubernetes probes offline
- [x] 11.3 Retain `root_squash`; prove the fixed-owner operations in the disposable guests and record results. Permission or stale-handle failures still block production rollout and require a design revision, not silent privilege relaxation
- [x] 11.4 Simulate rename/promotion only inside `99_tmp/nfs-readiness`, proving reopened bytes and backing links without media applications; tear down VM clients/fixtures. Real seeding, production promotion and library rescans belong to Task 5
- [x] 11.5 Create `metal/roles/storage/molecule/nfs-lifecycle/` with pinned disposable VM provisioning, isolated inventory, real-role convergence/idempotence, lifecycle and layout-preservation assertions; run the full scenario, intentional-failure cleanup and fresh recreation
- [x] 11.6 When the NAS returns, perform Task 1.5 and the mount changes in one maintenance window, quiescing/unmounting clients before the first full-role application; use the normal NFS/mergerfs shutdown/remount procedure in the implementation plan. Prove live active options, fixed-owner operations, two-client idle/reopen and controlled remount/recovery, RO rejection, backing links and NAS memory. Run the required live Kubernetes probes and verify clients/fixtures are removed. Live acceptance completed2026-11-09; VM results alone did not satisfy it

### Execution context

**Accepted 2026-11-09:** The operator completed the live two-client lifecycle,
including fixed-owner denied/allowed operations, 65-second idle/reopen, RO rejection,
backing hardlink identity, normal NFS/mergerfs recovery, post-recovery reads and
memory observations. Both Kubernetes probes succeeded, and namespace, client
mounts, workspaces and pool/all-branch fixture cleanup were verified.

The earlier three-VM scenario passed configuration idempotence, layout/data
preservation, lifecycle checks, intentional-failure cleanup and fresh recreation.
The full live gate was satisfied by operator output, not by those VM results.
The focused live entry point and its limits are documented in
[the implementation plan](./implementation.md#guided-live-acceptance-entry-point);
see the [acceptance summary](./reviews/guided-execution-2026-11-08.md#task-11-live-nfs-acceptance).
No lifecycle or cleanup repeat is needed for this completed run.

## Task 12: Explicit parity bootstrap and expansion jobs
- **Status:** done
- **Depends on:** Task 2, Task 3
- **Size:** M
- **Can run in parallel with:** Task 1, Task 4, Task 6, Task 7, Task 9, Task 11, Task 13
- **Docs:** [implementation.md#parity-job-readiness](./implementation.md#parity-job-readiness)

### Subtasks
- [x] 12.1 Update `tasks/snapraid.yml`, `tasks/snapraid_initial_sync.yml` and `handlers/main.yml`: always deploy the bootstrap unit, remove the first-parity-file completion guard and automatic config-change start, require explicit operator start after safety gates
- [x] 12.2 Update `templates/snapraid-initial-sync.service.j2` to invoke `snapraid --force-full sync` directly with journal output and no fixed 12-hour timeout; maintenance timers/handlers must respect stopped/disabled state during bootstrap
- [x] 12.3 Create `metal/roles/storage/molecule/parity-lifecycle/` using a disposable systemd VM and distinct data/parity filesystems; exercise actual role tasks/handlers and prove initial creation, adding second parity, interruption/retry and nonzero-exit propagation. Applying config must not start jobs, and role reruns must not reactivate disabled maintenance
- [x] 12.4 Run `molecule test -s parity-lifecycle` from the role directory inside `nix develop`; require configuration idempotence, successful and failed unit evidence, recovery after injected failure, and cleanup/recreation. Keep this scenario independent of Task 11; real NAS sync/scrub remains Task 8

**Verified 2026-10-04:** The independent QEMU/KVM scenario passed with SnapRAID
13.0, systemd 252.39 and four distinct scratch filesystems. Configuration was
idempotent and preserved existing parity/content bytes without starting jobs.
First sync, expansion, two full scrubs, real-process interruption/retry and
injected exit-42 failure/recovery passed with distinct invocation evidence and
unchanged payload hashes. Failure cleanup and fresh recreation also passed.

The unit retains completion evidence with RemainAfterExit; each explicit attempt
uses restart and must produce a new invocation ID. Disabled maintenance stays
stopped, and credential-bearing runner configuration is mode 0600. These are
disposable-environment results: real NAS sync, scrub and drive release remain
Task 8. See [the job contract](./implementation.md#parity-job-readiness) and the
scenario README under `metal/roles/storage/molecule/parity-lifecycle/`.

## Task 13: Migration inventory and audit tooling
- **Status:** done
- **Repository work:** done; NAS differing-version unit/access and teardown acceptance completed2026-11-09
- **Depends on:** Task 3, Task 11
- **Size:** M
- **Can run in parallel with:** Task 2, Task 4, Task 9, Task 12
- **Docs:** [implementation.md#migration-audit-tooling](./implementation.md#migration-audit-tooling)
- **Slicing:** Risk-First — validate the acceptance mechanism before handling real sources

### Subtasks
- [x] 13.1 Create `scripts/nas-migration-audit.py` with the documented inventory/compare/verify/access contract, read-only dataset handling, versioned JSONL, explicit exit codes and atomic completed generations
- [x] 13.2 Add `tests/test_nas_migration_audit.py` covering the specified data/metadata/error/retry cases; run standard-library unittest discovery from the dev shell
- [x] 13.3 Extend Task 11's `molecule/nfs-lifecycle` verifier with the restrictive-permission audit fixture; require UID/GID 1000 reads over a read-only NFS mount to fail before the declared repair and pass afterward, then clean up clients. Record helper/tool revisions for Task 6; keep unit tests in 13.2 and actual migrated-content acceptance in Task 7
- [x] 13.4 When the NAS is available, prepare Python 3/b3sum outside the storage role and compare their versions with the fixture record; rerun unit/access checks for differing versions before Task 6. Completed2026-11-09 on NAS Python3.13.5/b3sum1.8.1

### Execution context

**Accepted 2026-11-09:** All 31 audit unit tests passed without skips on the NAS's
Python 3.13.5/b3sum 1.8.1 stack. Actual UID/GID 1000 reads with no supplementary
groups over RO NFS produced the expected permission failures before repair,
then read both files successfully afterward. Reconciliation, ledger digest,
tool versions and helper hash matched. Evidence transfer, normal unmount,
pool/all-branch fixture absence and workspace removal passed.

The retained records were also inspected locally: all eight required files and
six completed JSONL generation digests were valid. Raw reports remain private
and Git-ignored. The core helper and completed Molecule fixture are unchanged;
live-only ownership/cleanup protections are in the separate harness. See
[the workflow](./implementation.md#guided-live-audit-acceptance) and
[acceptance evidence](./reviews/guided-execution-2026-11-08.md#task-13-audit-tooling-acceptance).

Earlier unit/scenario checks passed on Python 3.12.10/b3sum 1.8.2 and guest
Python 3.11.2/b3sum 1.2.0, including denied-read, declared-repair and failure-cleanup
cases. The different NAS stack required its own successful checks above. Actual
source inventories, migrated-library access and drive release remain Tasks 6–8;
none has started. Task 6 must record its own tool/helper revisions and evidence.

## Task 10: Final verification
- **Status:** pending
- **Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8, Task 9, Task 11, Task 12, Task 13
- **Size:** S
- **Can run in parallel with:** —

### Subtasks
- [ ] 10.1 Run `/kk:test` — both Molecule scenarios (including Task 13's access fixture), layout idempotency, direct parity config/audit-helper tests, `bash tests/test_inventory.sh`, complete migration/access/release evidence, live NFS and real application acceptance, separate network smoke test, strict docs build. Scenario passes do not replace live gates
- [ ] 10.2 Run `/kk:document` — finalize docs, move feature out of wip when done
- [ ] 10.3 Run `/kk:review-code` — review the ansible/helm/nix changes
- [ ] 10.4 Run `/kk:review-spec` — verify implementation matches design/implementation docs

Final feature verification remains pending until the migration, parity and
application acceptance tasks are complete. The completed incremental reviews and
synthetic/live storage checks do not replace this final gate.

## Dependency Graph

```
Task 1  ─→ Tasks 4 (offline), 6, 9, 11
Task 2  ─→ Tasks 7, 8, 12
Task 3  ─→ Tasks 6, 11, 12, 13
Task 4  ─→ Task 5
Task 6  ─→ Task 7
Task 7  ─→ Task 8
Task 8  ─→ Task 5
Task 11 ─→ Tasks 6, 13
Task 12 ─→ Task 8
Task 13 ─→ Task 6

All Tasks 1–9, 11–13 ─→ Task 10
```
