# Tasks: NAS Storage Directory Layout

> Design: [./design.md](./design.md)
> Implementation: [./implementation.md](./implementation.md)
> Status: in-progress
> Created: 2026-08-22
> Revised: 2026-10-04 — Tasks 2–4 and 12 complete; Tasks 1, 11 and 13 repository work verified; both Molecule scenarios pass; NAS apply/preparation/acceptance deferred while offline
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

## Task 1: Tree skeleton via storage role
- **Status:** in-progress
- **Repository work:** done; live acceptance in 1.5 remains deferred
- **Depends on:** —
- **Size:** M
- **Can run in parallel with:** Task 2, Task 3, Task 12
- **Docs:** [implementation.md#tree-skeleton](./implementation.md#tree-skeleton)

### Subtasks
- [x] 1.1 Replace `storage_dirs` in `metal/roles/storage/vars/main.yml` with the designed tree as a flat path list (top-level dirs, `NN.MM` subdirs, `30_media/rotation/{movies,shows}`, `30_media/rotation/downloads/{complete,incomplete}` — downloads nests INSIDE rotation, `10_documents/inbox`)
- [x] 1.2 Ensure the `storage_dirs` loop in `tasks/nfs.yml` sets owner/group `1000:1000`, mode `0775`
- [x] 1.3 Add `templates/storage-readme.j2` (legend: grammar rules, working-set test, machine-vs-human convention) rendered to `00_meta/README.md` from the same variable; create `00_meta/RETIRED.md` with `force: false`
- [x] 1.4 Grep the role for references to old dirs (`Temp`, `Videos` in validation tasks) and repoint to `99_tmp`
- [ ] 1.5 Run the role against the NAS twice: second run reports zero changes for the layout/legend tasks (the pre-existing `sensors-detect` task always changes); manually remove only confirmed-empty legacy dirs and verify the new tree

**Deferred operation (2026-10-04):** Subtask 1.5 is deferred at the owner's request
because the NAS is offline. Do not run Ansible against the NAS for this task now.
When the host is available, inspect the storage-play check/diff, apply twice, record
layout/legend idempotence, and remove legacy directories only after confirming they
are empty. Local validation does not satisfy this live acceptance gate.

**Local verification (2026-10-04):** YAML lint, offline Ansible lint and a
localhost-only syntax check passed. A disposable localhost fixture ran the three
actual layout/legend tasks against a temporary root: all 40 directories had
`1000:1000` ownership and `0775` mode; the second application made zero changes.
Existing retirement entries, legacy data and restrictive descendant permissions
survived. Strict template rendering matched the full path list and included an
extra path supplied only through the variable. No NAS commands were executed.
Isolated code review found no correctness issues. Its optional `basename` filter
suggestion was left unchanged because the standard Jinja expression works in both
rendering checks. If that style change is adopted later, rerun the Ansible template
check.

**Molecule follow-up:** Task 1's completed repository checks remain valid. Task 11
will include layout/legend and retirement-log preservation in its reusable NFS
scenario; Tasks 3, 11–13 below now own the planned tooling and integration coverage.
Task 11's NFS Molecule scenario now covers these regressions; Task 1.5 remains a
separate live acceptance gate.

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

**Local verification (2026-10-04):** All three tests in
`tests/test_snapraid_config.py` passed with SnapRAID 13.0, Python 3.12.10 and Jinja
3.1.6. The parity-count subtests parsed all three configurations and checked actual
scan inclusion/exclusion on three temporary data roots. Duplicate first parity
failed with the expected parser error. No parity/content files were created and no
NAS commands ran. The test binary was built in `/tmp` from upstream tag `v13.0`
(using its `.version` build metadata); no project dependency versions changed.
See [the repeatable command and fixture limits](./implementation.md#snapraid-excludes).
Live configuration acceptance remains in Task 8.

**Regression and review:** Running the same suite against the original template
produced five expected assertion failures and no execution errors. Isolated external
code review (Gemini 3.1 Pro) found no required fixes; its optional explicit
`check=False` suggestion was left unchanged because that is already the subprocess
default. The code-reviewer sub-agent could not access the Nix daemon under its
read-only permissions, so only the external reviewer completed independent review.

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

**Local verification (2026-10-04):** The locked packages provide `b3sum 1.8.2`
and Molecule `25.11.1` with Python `3.13.11`, Ansible Core `2.19.4` and
`molecule-plugins 23.5.3`. Version and scenario-help commands passed; executable
paths and package metadata confirm the Nix runtimes satisfy Molecule's requirements.
See [the commands and environment limits](./implementation.md#devshell-b3sum).
No NAS commands or Molecule scenarios ran; backend provisioning and scenario
acceptance remain in Tasks 11–12.

**Validation and review:** `nix flake check --no-build --no-update-lock-file`
passed for `x86_64-linux`; other platforms were not checked. Revised Markdown
link targets passed. Git whitespace checks passed with only the user-level
`indent-with-non-tab` rule disabled, preserving the existing Nix space indentation.
The isolated code-reviewer found no issues in the supplied patch; its read-only
environment could not access the Nix daemon, so runtime verification remained with
the implementing session. The external reviewer returned no findings but reported
zero embedded files; its response is not counted as independent source inspection.

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

**Local verification (2026-10-04):** Helm `3.19.1` strict lint and offline rendering
passed using the cached `csi-driver-nfs 4.13.0` dependency. Parsed all ten rendered
resources and compared them with the pre-change values: only the PV name, capacity,
CSI handle and share changed. Assertions verified `pv-nfs-media`, `4Ti`, `Retain`,
`ReadWriteMany`, the class-less static binding and unchanged mount options.
`kubeconform` was unavailable, so Kubernetes API schema validation was skipped;
see [repeatable commands and coverage limits](./implementation.md#nfs-media-share).
The changes remain on `feat/nas_layout`; the checked-in ArgoCD configuration targets
`master`. No NAS, Ansible or cluster commands ran. Task 5 still owns joint release,
old-resource cleanup and live acceptance after Task 8.

**Review:** The isolated code reviewer found no actionable issues in the supplied
patch and source snapshots. Its read-only environment could not access the Nix
daemon, so filesystem inspection and test execution remained with the implementing
session. The external reviewer returned no findings but reported zero embedded
files; that response is not counted as independent source inspection. No findings
needed indexing. All 29 local links/anchors in the implementation and task documents
passed; whitespace checks passed with the user-level `indent-with-non-tab` rule
disabled to preserve existing YAML indentation.

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
- **Status:** pending
- **Depends on:** Task 1
- **Size:** S
- **Can run in parallel with:** Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8, Task 11, Task 12, Task 13
- **Docs:** [implementation.md#legend-docs](./implementation.md#legend-docs)

### Subtasks
- [ ] 9.1 Write the vault legend note (manual, in Obsidian vault) mirroring `00_meta/README.md`
- [ ] 9.2 Point `docs/info/todo.md` storage section at `docs/feat/wip/nas-storage-layout/` (supersedes "Future shares (Pictures, Documents, Music, Backups)" naming)
- [ ] 9.3 Run `python3 -m mkdocs build --strict --site-dir /tmp/ktchn8s-docs-check` and check revised local links; document any unrelated baseline warnings rather than weakening the check

**Docs baseline (2026-10-04):** Strict build already reports nine broken-link
warnings after the review documents were moved into `reviews/archive/`. This is
outside the Molecule planning change. Before completing 9.3, update the review
links in `design.md` and `docs/reference/architecture/decision_records.md`, fix the
relative feature/ADR links inside the two dated archived reviews, and rerun strict
mode. Do not count an unchanged warning baseline as a passing strict build.
The Molecule planning update adds no warnings: the before/after warning sets are
identical. Local links/anchors in the revised implementation/tasks documents and
their dependency graph/parallel markers pass validation.

## Task 11: NFS export lifecycle acceptance
- **Status:** in-progress
- **Repository work:** done; live NAS/Kubernetes acceptance in 11.6 remains deferred
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
- [ ] 11.6 When the NAS returns, complete Task 1.5, quiesce clients and apply the mount changes; prove live active options, fixed-owner operations, two-client idle/reopen and controlled remount/recovery, RO rejection, backing links and NAS memory. Run the required live Kubernetes probes and verify clients/fixtures are removed. These live checks are deferred, not satisfied by the VM results

**Local verification (2026-10-04):** The three-VM QEMU/KVM scenario passed with
mergerfs 2.41.1 and a checksum-pinned Debian 12 image. The second real-role converge
reported zero changes. Both clients passed UID/GID-1000 operations, a deliberate
permission-denied test, 65-second idle/reopen, exact-byte reads, backing hardlink
identity, RO rejection and normal unmount/remount recovery. All 40 directories,
legend paths, operator retirement entries, legacy data and restrictive descendant
metadata passed preservation checks. An injected failure after client mounts
returned nonzero and completed cleanup/destroy; a subsequent fresh full run passed.
Six local regression tests passed. See `metal/roles/storage/molecule/nfs-lifecycle/README.md`
for repeatable commands, versions, resource requirements and log locations.

**Validation and review:** Offline Ansible lint passed with the existing short-module
and unprefixed-role-variable conventions excluded; shell checks and Nix flake
evaluation passed. Both Kubernetes manifests rendered and parsed locally, including
a delegated-controller case proving the original inventory server address survives.
No live Kubernetes test was run. Isolated review fixes strengthened cleanup ordering,
exact-byte/error checks, delegated server addressing and process-exit cleanup. The
external review's proposed undefined loop-register issue did not reproduce: the
real Ansible 2.19.4 scenario executes that loop successfully. No NAS commands ran.
The final full VM rerun also passed after the cleanup and log-retention fixes;
its controller transcript is `/tmp/nas-nfs-final.log`. Strict MkDocs validation
still fails on the same nine archived-review links already tracked in Task 9;
none of its warnings concern the revised implementation/task documents.

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

**Local verification (2026-10-04):** The independent QEMU/KVM scenario passed with
SnapRAID 13.0, systemd 252.39 and four distinct scratch filesystems on the pinned
Debian 12 image. The second configuration converge reported zero changes. First
sync, second-parity expansion, two full scrubs, real-process interruption/retry,
and injected exit-42 failure/recovery passed with six distinct invocation IDs.
Configuration preserved existing parity/content bytes and inodes, never started
jobs, and stopped previously enabled maintenance; changed timer handlers kept
disabled maintenance stopped. Original payload SHA-256 hashes matched before and
after every invocation. An intentional failure after first sync returned nonzero
and completed evidence collection/cleanup/destroy; fresh recreation then passed.
No NAS commands ran. Live configuration, sync/scrub and drive release remain Task 8.

**Evidence and commands:** See
`metal/roles/storage/molecule/parity-lifecycle/README.md`. Controller transcripts
are `/tmp/nas-parity-injected.log` and `/tmp/nas-parity-final.log`; retained guest
journals, JSON results, baseline hashes, versions and scrub output are under
`/tmp/nas-parity-evidence/`. These are local artifacts, not committed evidence.
All 13 local storage regression tests passed (three config, six NFS, four parity
evidence tests). YAML/offline Ansible lint and whitespace checks passed; the existing
short-module, role-variable and lowercase-handler conventions were retained.
All 29 implementation/task document links and anchors passed. Strict MkDocs still
fails on the same nine archived-review links tracked in Task 9, with no new warnings.

**Implementation adjustment and review:** Successful inactive oneshot units lost
their exit metadata immediately in the guest. `RemainAfterExit=yes` now retains
`active (exited)` results; every explicit attempt uses `systemctl restart --no-block`
and must have a new invocation ID/start timestamp. Plain `start` after completion
does not run again. The independent reviewer approved after adding payload-baseline
checks and preserving original errors when evidence capture fails. The final VM
pass exercised payload checks and journal-error handling; the subsequent JSON-write
error guard passed the local regression suite. External review reported zero
embedded files, so its proposals were checked against source independently:
the credential-bearing runner config is now `0600`, PID/teardown safeguards remain
fail-loud, and runtime journals did not reproduce the proposed invocation-ID issue.

## Task 13: Migration inventory and audit tooling
- **Status:** in-progress
- **Repository work:** done; NAS preparation in 13.4 is deferred while offline
- **Depends on:** Task 3, Task 11
- **Size:** M
- **Can run in parallel with:** Task 2, Task 4, Task 9, Task 12
- **Docs:** [implementation.md#migration-audit-tooling](./implementation.md#migration-audit-tooling)
- **Slicing:** Risk-First — validate the acceptance mechanism before handling real sources

### Subtasks
- [x] 13.1 Create `scripts/nas-migration-audit.py` with the documented inventory/compare/verify/access contract, read-only dataset handling, versioned JSONL, explicit exit codes and atomic completed generations
- [x] 13.2 Add `tests/test_nas_migration_audit.py` covering the specified data/metadata/error/retry cases; run standard-library unittest discovery from the dev shell
- [x] 13.3 Extend Task 11's `molecule/nfs-lifecycle` verifier with the restrictive-permission audit fixture; require UID/GID 1000 reads over a read-only NFS mount to fail before the declared repair and pass afterward, then clean up clients. Record helper/tool revisions for Task 6; keep unit tests in 13.2 and actual migrated-content acceptance in Task 7
- [ ] 13.4 When the NAS is available, prepare Python 3/b3sum outside the storage role and compare their versions with the fixture record; rerun unit/access checks for differing versions before Task 6. Defer this NAS preparation while offline

**Offline completion (2026-10-04):** Subtasks 13.1–13.3 are complete. Task 11's
completed repository/scenario work supplied the offline prerequisite; its live
acceptance remains deferred. No NAS commands ran. Subtask 13.4 remains unchecked,
and Task 13 stays in progress until NAS preparation/version acceptance completes.
Actual source inventories, migrated-content access and drive-release gates remain
Tasks 6–8. See the [helper and ledger guide](../../../guides/nas_migration_audit.md).

**Verification:** All 44 local storage regression tests passed, including 31 new
audit-helper tests, with Python 3.12.10 and b3sum 1.8.2. The final `nfs-lifecycle`
Molecule run passed configuration idempotence, the existing lifecycle checks and
the new audit fixture. All 31 helper tests also passed with guest Python 3.11.2
and b3sum 1.2.0. The fixture's foreign-owned `0700` directory, restrictive ACL and
two hardlinked files produced three access/reconciliation failures before the
declared repair and zero afterward. Real UID/GID 1000 reads used no supplementary
groups and an RO NFS mount; mergerfs backing identities, hashes, xattrs and matching
ledger digests were checked. Clients and VM disks were removed after verification.

**Failure/retry evidence:** `NFS_AUDIT_FAIL_AFTER_DENIAL=1` deliberately failed with
the audit client mounted; cleanup and destroy succeeded. A fresh normal run then
passed with the final helper. Transcripts are `/tmp/nas-audit-molecule-injected.log`
and `/tmp/nas-audit-molecule-final.log`. Final JSONL evidence remains under
`/tmp/ktchn8s-audit-nfs-final/audit-evidence/`, with the guest unit transcript under
`vms/nfs-server/audit-unit.log`. These local artifacts were checked after teardown.
The tested helper SHA-256 is
`2ab80625954ce51e68551b224917cb7390d0e4fed39b44937c69b2189164243a`;
Task 6 must preserve the relevant tool/helper revisions with its own evidence.

**Review and checks:** Independent code review approved after fixing intermediate
symlink search semantics, empty-directory search checks and repeated ancestor
enumeration. Resource-initialization cleanup and three-way collision regressions
also pass. External review reported zero embedded files; its resource-cleanup
suggestions were inspected independently, and its response is not counted as
independent source inspection. No P0/P1 findings required indexing. YAML lint,
offline Ansible lint and whitespace checks pass. Revised local documentation links
pass; strict MkDocs still reports the same nine archived-review warnings tracked
in Task 9, with none added by this task. Molecule evidence retention needed an
explicit file glob; the final run confirmed its reports survive pruning.

## Task 10: Final verification
- **Status:** pending
- **Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8, Task 9, Task 11, Task 12, Task 13
- **Size:** S
- **Can run in parallel with:** —

### Subtasks
- [ ] 10.1 Run `/kk:test` — both Molecule scenarios (including Task 13's access fixture), layout idempotency, direct parity config/audit-helper tests, complete migration/access/release evidence, live NFS and real application acceptance, separate network smoke test, strict docs build. Scenario passes do not replace live gates
- [ ] 10.2 Run `/kk:document` — finalize docs, move feature out of wip when done
- [ ] 10.3 Run `/kk:review-code` — review the ansible/helm/nix changes
- [ ] 10.4 Run `/kk:review-spec` — verify implementation matches design/implementation docs

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
