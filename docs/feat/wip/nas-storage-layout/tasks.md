# Tasks: NAS Storage Directory Layout

> Design: [./design.md](./design.md)
> Implementation: [./implementation.md](./implementation.md)
> Status: in-progress
> Created: 2026-08-22
> Revised: 2026-11-11 — A copy running; A/B inventories accepted/preserved and overlap examined; final-only destination content reconciliation approved; C inventory and later acceptance remain pending
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
Task 6 completes source comparison and provisional copying; Task 7 owns the full
destination-content acceptance after sorting. There is no routine full staging
rehash. All originals remain intact through final acceptance and drive-release gates.

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
- **Status:** in-progress
- **Depends on:** Task 1, Task 3, Task 11, Task 13
- **Size:** M
- **Can run in parallel with:** Task 2, Task 4, Task 9, Task 12
- **Docs:** [implementation.md#migration-runbook](./implementation.md#migration-runbook)
- **Completion boundary:** source comparison and provisional copies; destination-content acceptance belongs to Task 7

### Subtasks
- [ ] 6.1 Establish `implementation.md#migration-evidence` workspace; freeze original source entries and use Task 13's tested helper to publish complete A/B/C JSONL inventories, recording NAS Python/b3sum versions
- [ ] 6.2 Copy A locally to `99_tmp/driveA/data/` beneath a private outer staging directory with metadata preservation; retain successful copy status/logs and a clean metadata-only rsync dry-run per the runbook. May proceed after A's accepted inventory/preflight while C remains disconnected. Publish copy receipts to the independent workspace; do not hash staging or claim content acceptance
- [ ] 6.3 Plan B/C deltas from accepted source inventories and planned A/B coverage, copy them with metadata preservation and metadata-only checks, and record every source/path identity, copy receipt and proposed disposition. Stop on execution/incomplete-input errors; defer destination content reconciliation to Task 7

### Execution context

At the previous handoff, no real source had been mounted, inventoried or copied.
Tasks 1, 3, 11 and 13 satisfied the tooling/storage prerequisites, but the owner
stopped before migration. On resumption, the owner must reconcile the A/B/C labels,
logical source relationships and independent recovery copies with the actual
sources before mounting or copying anything. Preserve original data and RAID/LVM
structures. The assistant prepares reviewed batches; the owner executes them.

**Resumed 2026-11-10:** The owner authorized proceeding with Task 6 in chat.
The repository was clean at `48c72ced009617b3143d9022d620d7f061eca9fa`;
the recorded prerequisite acceptance remains complete. Preparation resumed with
no real-source mount, inventory or copy yet executed in this session.
The first operator batch inspects host/block-device/mount/active-MD topology and
Python/b3sum versions without changing storage. Topology and tool-version output
have now been received below.

**Owner-reported 2026-11-10:** A/B/C are separate filesystems. A and B are
connected and accessed through RAID/LVM; the owner can mount them to access their
data. C is a separate, currently disconnected drive. Exact host, device/array/LV
identities and current mount state remain unverified. Separate filesystems alone
do not establish physical independence or verified recovery-copy coverage.

**Observed from owner output 2026-11-10:** The source host is `yggdrasil`.
Betelgeuse is ext4 UUID `16806807-1e4e-4f7e-9ffd-de387168a12f` on
`sda3 -> md2 -> vg288/lv2`; Magrathea is ext4 UUID
`987b7d40-677d-4bc6-a584-6257eea09980` on `sdb3 -> md3 -> vg289/lv3`.
Neither filesystem is mounted in the supplied output. Both active data arrays
report RAID1 `[1/1] [U]`, with one member each; this supplies no second physical
copy within either array. The source disks each report 18,000,207,937,536 bytes;
their displayed model/serial fields are truncated, so stable physical identifiers
remain to be recorded. The destination is a separate four-branch mergerfs pool:
`sdc1 -> data1`, `sdd1 -> data2`, `sdf1 -> data3`, `sde1 -> data4`.

Inactive arrays `md9`, `md13`, `md256` and `md322` have partitions from both source
disks. Preserve these existing structures; owner and assistant must account for
their recovery relevance before Task 8 releases either disk. No array assembly,
activation, repair, mount or data scan was performed by this session. Next batch:
full physical identifiers, data-array details, LVM segment mappings and ext4
superblock state. Before mounting, check journal-recovery requirements: ext4
`ro` alone may replay the journal; `ro,noload` prevents that write but can expose
inconsistent state after an unclean shutdown (see the
[kernel ext4 mount documentation](https://docs.kernel.org/admin-guide/ext4.html#options)).

**Owner-reported backup history 2026-11-10:** A and B were backups made roughly
at the same time, one after the other, when the QNAP was retired/sold. The owner
recalls C as a later redundancy copy of either A or B, but is uncertain which.
There is no established primary or verified equality between these copies.
Preserve this uncertainty: inventories and content comparisons must establish
overlap and unique entries; age or remembered provenance does not authorize
discarding any source. Use the filesystem names during inspection; select and
record the initial-copy A/B mapping before migration invocations.

**Source inspection received 2026-11-10:** Both disks are model
`ST18000NM000J-2TV103`, 18,000,207,937,536 bytes. Betelgeuse's disk is serial
`WR501QBM`, WWN `0x5000c500ed0f3cca`; Magrathea's is serial `WR508J63`, WWN
`0x5000c500ed088111`. `mdadm --detail` reports both data arrays clean with one
configured/active member and no failed devices. LVM segment reports place all
`vg288` LVs on `md2` and all `vg289` LVs on `md3`, using linear segments. The
old-PV-header warnings were observed; no VG/header update is part of this migration.
Both ext4 superblocks report clean state, no `needs_recovery` feature, and journal
start zero. These header observations are not a full filesystem or data-read check.
NAS Python 3.13.5 and b3sum 1.8.1 match the accepted Task 13.4 versions.

**Mount output received 2026-11-10:** Both source filesystems are mounted under
`/mnt/nas-migration-20261110/{betelgeuse,magrathea}` through the expected LVs.
The issued options were `ro,noload,nodev,nosuid,noexec`; supplied runtime output
confirms `ro,nosuid,nodev,noexec` but is truncated after `relatime,`, so the full
journal-recovery option remains to be verified using untruncated JSON output.
The rounded `df -hT` report shows about 12 TiB used per source and 62 TiB available
on the destination pool. This is a capacity observation, not content verification.
Top-level source layouts differ: Betelgeuse includes `backup`, `bet-backup`, `ejcd`
and QNAP housekeeping entries; Magrathea includes `ejcd`, `mag-backup` and
housekeeping entries. Inventories must include the entire source filesystems;
none of these entries has been approved for omission or discard. No inventory or
copy has started.

**Helper identity checked locally 2026-11-10:** The repository helper SHA-256 is
`2ab80625954ce51e68551b224917cb7390d0e4fed39b44937c69b2189164243a`, matching
the Task 13 live acceptance record. Its last modifying commit is
`e0b8947e0fa54c4c7339e785c7e7a7bd042e55bc`. Controller checkout and the eventual
NAS-installed copy must match this digest before source scans.

**Controller storage observed locally 2026-11-10:** The checkout is on
`serenity`, backed by local ext4 `/dev/nvme0n1p3` with about 11 GiB available
(98% used). The original checkout-local evidence proposal is superseded by
`/var/lib/ktchn8s-nas-migration-20261110` on serenity's root ext4 partition,
`/dev/nvme0n1p2`, with about 41 GiB available. This is independent of yggdrasil's
source disks and NAS pool. At this inspection the proposed directory did not yet
exist; its creation was subsequently reported below. These free-space
observations are not an allocation or a report-size bound; monitor space as
inventories/comparisons grow. A broad `df -h -l` encountered an unrelated stale
AppImage mount; focused checks of the checkout and `/var/lib` succeeded.

**Mount/workspace acceptance 2026-11-10:** Owner-supplied JSON confirms both
expected ext4 sources at their named mountpoints with
`ro,nosuid,nodev,noexec,relatime,norecovery,stripe=128`; the journal flag is now
verified. The controller workspace exists with `sergio:sergio` ownership and
mode `0700`, about 41 GiB available. The NAS root filesystem reports about
408 GiB available for the spool under `/var/log/snapraid/migration/20261110`.

**Run mapping selected 2026-11-10:** Use A = Betelgeuse (WWN
`0x5000c500ed0f3cca`) and B = Magrathea (WWN `0x5000c500ed088111`) for this run.
This is the initial-copy ordering, not a claim that A is newer or authoritative.
Run ID: `migration-20261110`. The next operator batch creates the private NAS
spool, transfers the unchanged helper, checks its SHA-256 and A's mounted UUID
and RO/no-recovery flags, then starts A's inventory as transient service
`nas-inventory-A-20261110.service`. Its output is `driveA.jsonl` in the spool.
Use the locally resolved Python/b3sum executables, inode identity and a retained
service result; no automatic restart or runtime time limit. Successful launch
is not completion. Preserve partial output and job evidence on failure; do not
blindly repeat a setup/start batch with an uncertain outcome.

**A startup observed 2026-11-10:** The owner reports successful NAS helper
SHA-256 verification and A's UUID/RO/no-recovery mount checks. Unit
`nas-inventory-A-20261110.service` is `active/running`, MainPID `12937`, invocation
`95b6389a6ca3448095d3c4a26b1027a2`. The current `Result=success` and exit-status
field do not establish completion while the process is running. At the owner's
request, operator commands are saved as numbered `nas-migration-*.txt` files in
the project root. Files 01/02 supplied transfer/A launch; file 03 starts B's
independent scan, and file 04 inspects both jobs without changing their state.
The assistant has not executed these live commands.

**C connection clarified 2026-11-10:** The owner will use a USB enclosure/dock.
C can remain disconnected until A/B inventories finish; simultaneous attachment
is unnecessary. Inspect its actual identity/filesystem before mounting or scanning.
The runbook still requires complete A/B/C source inventories before staging copies.

**A/B running checkpoint 2026-11-10:** Owner-supplied status shows A still
`active/running` with its recorded invocation and MainPID `12937`, started
12:15:44 CET. B is `active/running`, MainPID `35761`, invocation
`d7a5628d72a543bda32dde32fd0eb0ba`, started 12:20:19 CET. Both have empty exit
timestamps and `ExecMainCode=0`; neither has completed. Supplied journal entries
show startup only, with no reported errors. Their partial reports are about
2.4 MiB and 970 KiB respectively, with 408 GiB still available on the NAS spool
filesystem. Report sizes do not establish a completion percentage or ETA.

**Unresolved at the 2026-11-10 checkpoint — superseded by completion below:** Owner to leave the scans running and use
`nas-migration-04-status.txt` for later checkpoints; report either completion or
failure. Require the retained successful exit state and validate each completed
generation before acceptance, then handle C's attachment/inspection. No inventory completion or copy
is claimed. Completed generations and job evidence must be transferred to the
independent controller workspace and verified there. C remains disconnected and must
also produce a complete source inventory before the copy stage begins.
Task 6.1 stays open until that mapping, evidence location, source freeze and
complete successful inventories are recorded; discovery output alone is not
migration acceptance.

**Drive-health observation preparation 2026-11-10:** The owner requested
temperature/attribute readings during the inventories and reports the executable
`/root/utils/SeaChestUtilities/Linux/Non-RAID/x86_64/SeaChest_SMART_linux_x86_64`
is available and executable on yggdrasil. File 05 now uses that absolute path;
file 06 streams it from the controller through SSH without a working-directory
assumption. Inspected the storage
role's `disk_health.yml`, `seachest_utils.yml`, `smartctl_utils.yml`, defaults and
main task caller. The existing native query is `--smartAttributes hybrid` on
SCSI generic handles; the role selects configured data/parity disks, and health
checks default to disabled. Source A/B monitoring uses the same query directly
in `nas-migration-05-drive-health.txt`, with explicit WWNs, exact sysfs sg-handle
resolution, private fresh snapshots and retained raw output/exit status.
It does not run provisioning, self-tests or drive-setting changes. The first
operator snapshot was subsequently received below. The command
file passed `bash -n` locally (captured run
`073170e2-a8ec-40ff-a07d-38b320911e8d`, exit 0); this validates syntax only.

**Deferred health-parser issue — assistant, before relying on role health
acceptance:** Both native and smartctl parsing skip nonzero tool results, while
missing parsed counters can default to zero. Therefore an absent/unreadable
result must not be treated as proof of a healthy source in this migration.
The direct snapshot retains output and status for explicit interpretation.
Repair the role separately to require one valid result per selected device and
distinguish command failure, health failure and missing attributes; verify those
cases with representative tool-output fixtures. Deferred because this step only
observes the running source scans and does not change storage-role behavior.

**First source SMART snapshot 2026-11-10 14:05:35 CET:** Owner execution of file
06 queried A through `/dev/sg0` and B through `/dev/sg1`, with serial/WWN identity
matching the source mapping. SeaChest SMART 2.6.1 (2025-07-30 build), firmware
SN02 on both disks; both queries exited 0. Raw reports are retained on yggdrasil
under `/var/log/snapraid/migration/20261110/drive-health-PTPNi6mW`.

| Attribute | A / Betelgeuse | B / Magrathea |
| --- | ---: | ---: |
| Current temperature (194) | 41 C | 41 C |
| Reported lifetime maximum temperature (194) | 49 C | 49 C |
| Retired sectors (5) | 0 | 0 |
| Reported uncorrectable (187) | 0 | 0 |
| Pending sectors (197) | 0 | 0 |
| Offline uncorrectable sectors (198) | 0 | 0 |
| Interface CRC errors (199) | 0 | 0 |
| Command timeout displayed raw value (188) | 1 | 0 |
| Power-on hours (9) | 10086 | 10083 |
| Lifetime reads displayed raw value (242) | 342683359474 | 153567498841 |

No failing/previously failed/warning markers appear in the supplied attributes;
the `?` prefix requests more detailed raw interpretation, not a failure. A's
timeout has unknown timing because no pre-inventory SMART baseline is available;
do not attribute it to this scan or dismiss a later increase. Temperatures are
within the model's 5–60 C operating specification. This is a SMART attribute
observation, not proof of full readability or completed migration verification;
no separate SMART status query or self-test was run. Owner: repeat file 06 after
roughly 30 minutes to establish a trend and report increases in error counts or
temperature; retain this snapshot with the eventual controller evidence transfer.

**Second source SMART snapshot 2026-11-10 15:00:03 CET:** Owner output is
retained under `/var/log/snapraid/migration/20261110/drive-health-XHisegFJ`;
identities/tool versions match the first snapshot and both queries exited 0.
Across 54 minutes 28 seconds, temperature changed A 41 -> 43 C and B 41 -> 42 C.
Retired/pending/reported-uncorrectable/offline-uncorrectable/CRC counts remain
zero on both; command timeout remains A=1, B=0. Emergency-retract, load/unload,
start/stop and power-cycle counts are unchanged, as are lifetime-write raw values
(A `61415440082`, B `63331400305`). Power-on hours are now A `10087`, B `10084`.
Normalized Read Error Rate changed A 82 -> 80 and B 81 -> 76, both above threshold
44, with displayed raw error values still zero. No failure/warning markers appear.
Lifetime-read raw values are now A `369385539386`, B `171631730297`; preserve
these as raw counters, without assuming units or deriving scan progress/throughput.
This snapshot supplies no reason to interrupt the inventories, but does not prove
their completion. Continue periodic health observations and use file 04 for job
state; transfer both health snapshots with the completed inventory evidence.

**Pause/resume guidance prepared after handoff, 2026-11-10:** The owner asked
whether scans can be paused for cooling. The helper has no persisted resume:
termination or reboot requires a fresh full inventory generation; a `.partial`
cannot be resumed or accepted. For the current live processes, systemd's cgroup
freezer can suspend the entire service, including b3sum children, and thaw it
without losing in-memory progress. Prepared controller-side command files
`nas-migration-07-pause.txt` and `nas-migration-08-resume.txt`, with cgroup-v2
prechecks and per-unit state output even after a freeze/thaw failure. File 04
now includes `FreezerState`, since SubState can remain running while frozen.
Reference: [systemctl freeze/thaw](https://man7.org/linux/man-pages/man1/systemctl.1.html).
Keep the NAS running and original RO mounts unchanged; stopping/restarting a
unit is not a pause (systemd thaws units before executing stop jobs). Pausing
does not power down disks. NAS freezer capability and actual pause/resume have
not been exercised; nothing was paused by this session. On any command error
or interrupted SSH outcome, inspect each unit before assuming both transitioned.
The earlier published handoff predates these two new files; this local note is
the continuation update. The user has not requested a plan change or scan stop.
Local Bash syntax checks passed for file 04, both controller launchers and their
remote heredoc bodies. These checks did not execute SSH or change service state.

**Resumed and reconciled 2026-11-11:** Read the owner's
[handoff](https://gist.github.com/serpro69/ee217699fe71129ee951d391274fa643)
and compared it with branch `feat/nas_layout`, still at
`48c72ced009617b3143d9022d620d7f061eca9fa`. Existing uncommitted Task 6 notes and
operator files 01–08 were preserved; the handoff predates files 07/08. The audit
helper still has the tested SHA-256 recorded above. The independent controller
workspace is empty, mode 0700 owned by sergio, with 43,218,923,520 bytes available
on `/dev/nvme0n1p2` at inspection. No NAS commands were run by the assistant.

**Owner-supplied completion evidence 2026-11-11:** Both retained units report
`LoadState=loaded`, `active/exited`, `MainPID=0`, `FreezerState=running`,
`Result=success`, `ExecMainCode=1`, `ExecMainStatus=0`, with original invocation IDs.

| Source | Start (CET) | Exit (CET) | Elapsed wall time | Published filename / rounded size |
| --- | --- | --- | --- | --- |
| A / Betelgeuse | Nov 10 12:15:44 | Nov 11 05:08:14 | 16h 52m 30s | `driveA.jsonl` / 1.2 GiB |
| B / Magrathea | Nov 10 12:20:19 | Nov 11 04:29:02 | 16h 08m 43s | `driveB.jsonl` / 1.5 GiB |

The NAS spool reports 2.7 GiB total and about 406 GiB available on its OS disk.
These observations supersede the running checkpoint: the processes finished
successfully, but footer/digest/count/schema/entry validation and independent
preservation are still unverified. The supplied unit journal shows startup
messages only; preserve full unit properties and invocation journals before any
reset or reboot. Do not rerun launch files 01–03, rename partials, or restart scans.

**Owner-supplied SMART snapshot 2026-11-11 08:58:08–09 CET:** Both expected
serial/WWN pairs were queried successfully with the same SeaChest version, retained
under `drive-health-H4xl2BwG`. Both temperatures are 39 C; retired, pending,
reported-uncorrectable, offline-uncorrectable and CRC counts remain zero.
Timeout values remain A=1/B=0; lifetime writes remain A=`61415440082`,
B=`63331400305`; power-on hours are A=10105/B=10102 and lifetime-read raw values
A=`404463195098`, B=`219585833297`. No failure/warning markers appear. Raw counters
are not scan progress or proof of equal content. The spool also lists four
intermediate health directories whose contents have not been supplied; preserve
all available snapshots without inventing their readings.

**Prepared 2026-11-11 — A/B acceptance batch:** Project-root
`nas-migration-10-preserve-completed.txt` runs on serenity as sergio, using
`nas-migration-09-validate-reports.py`. It captures fresh NAS evidence directories,
preserves originals/partials, validates the reports through the unchanged helper's
`Index.inventory`/`read_generation`, and checks exact run/source/root/disk/tool and
unit invocation identities. It retains entry counts/types and special-entry counts;
special entries still need later dispositions. It copies the completed reports,
helper, unit properties, journals and health snapshots to a fresh private directory
under the independent controller workspace, checks all transfer hashes, and repeats
report validation there. It never scans a source tree, starts/stops a unit, mounts a
drive or copies dataset content. Failed/interrupted captures stay for diagnosis;
an `ACCEPTED.txt` marker is written only after both validations and transfer checks.
Owner: execute this batch and return the output/path; assistant: inspect acceptance
evidence before advancing. Actual large-report execution remains unverified.

**Owner steering 2026-11-11:** C is still disconnected. The owner requested an
overall-plan discussion and an explanation of C's value before starting its read.
No C attachment, mount or inventory commands are prepared or authorized by this
continuation. C's possible unique content, independent recovery coverage, and
eventual second-parity role remain distinct and unverified. The existing runbook
requires A/B/C inventories before staging A; discussing earlier non-destructive A
copying does not amend that order. Owner/assistant to resolve C's role and any
sequencing change explicitly before dependent work. Task 6.1–6.3 remain open;
source recovery coverage, copying, final sorting/reconciliation, and parity gates
have not been satisfied by scan process success or SMART observations.

**Local verification 2026-11-11:** Nine disposable fixture tests passed without
skips under `nix develop` (captured run
`0c9cba40-eaec-4857-905e-126f7c9416b5`, exit 0). They exercise repeatable validation
without changing input bytes, truncation/digest corruption, duplicate/orphan paths,
wrong source/disk/root/identity/tool/helper values, running/failed/wrong-invocation
units, and Bash syntax for the launcher plus both remote bodies. The fixture was
`/tmp/test_nas_completion_20261111.py`; real source trees and SSH were not used.
The already documented stale virtualenv pip-launcher warning recurred on shell
entry but did not prevent these tests. `git diff --check` passed. These checks
validate the new preparation code, not the actual reports or Task 6 completion.

**Review 2026-11-11:** Isolated code-reviewer (OpenAI) approved the preparation
with no findings. External backend was PAL `clink`: only `claude` was eligible
(Anthropic, initially assumed from client mapping, observed model
`claude-opus-5-5`; configured model unknown). `agy` and `codex` executables were
absent; `gemini` is retired. External review executed and returned COMMENT with
four P3 observations, no P0–P2. Its source-receipt trace was not fully assessed,
so no independent corroboration is claimed; a candidate-check shell command was
denied while its read-only review still returned findings. Neither reviewer ran
tests or inspected actual NAS reports. No systemic findings require indexing.

External P3 outcomes: changed SCP to transfer the named capture directory rather
than `/.`; changed the failure reminder to an EXIT trap; documented interrupted
SQLite scratch and inspection-before-retry handling. Foreground report validation
is retained; it does not restart the source scans. The optional automated
`ExecStart` check is deferred: owner/assistant must inspect captured command
arguments against files 02/03 before accepting the returned evidence. Parsing
systemd's serialized command string was not added to this one-run validator;
exact known invocation IDs, tested helper bytes, full generation validation and
exact report identities remain mandatory automatic gates. This manual provenance
check is still open until the actual capture is available.
The independent code-reviewer re-reviewed the final transfer/trap/retry edits
and approved them without findings; it also assessed the manual `ExecStart`
comparison as sufficient for this fixed run. All nine local fixture checks passed
again after those edits (run `b0e6010d-88f5-40b0-8636-b73abd0efe81`, exit 0).

**Preservation started, owner output 2026-11-11:** File 10 created capture
`ab-completion-N6CeYbWC` in the recorded NAS/controller workspaces. A/B unit
properties still match the original successful invocations. Supplied `ExecStart`
arguments match files 02/03 (helper, source/root/disk IDs, inode identity, tools,
run ID and output paths), completing that manual provenance check for this
capture. Original-to-NAS-capture SHA-256 checks passed for both inventories and
the helper; validator upload completed. No NAS validation completion or report
transfer has yet been reported. Local inspection confirms the controller capture
currently contains only the prepared scripts and HEAD record.

**Validation visibility 2026-11-11:** The owner reported apparent hanging after
upload. File 10 redirects validator stdout/stderr to the NAS capture and displays
stderr only after the process exits; file 09 emits only per-source start messages
and the final summary. Quiet output is therefore expected but does not establish
progress. File 11 (`nas-migration-11-validation-status.txt`) provides two read-only
NAS observations 15 seconds apart: logs/exit status, scratch sizes, matching
validator CPU/process state, I/O counters and open inventory positions. It leaves
the running batch and reports unchanged. Owner: run from a second terminal and
return output if progress is uncertain. No live status command was executed by
the assistant. SQL parent checks can continue after the inventory descriptor
closes and scratch size stops growing; cached reads need not increase `read_bytes`.
Controller and remote Bash syntax checks passed (captured run
`0f55f2c0-61cc-452d-9c25-92c7acf590ce`, exit 0); `git diff --check` passed.

**Deferred visibility improvement — assistant, before reusing file 10:** Surface
phase/progress messages while validation runs, without losing its retained logs
or failure status. Deferred to avoid altering this active capture; the concrete
next step is live stderr/heartbeat output with a check that failure propagation
and report preservation remain intact. Actual report validity, transfer and A/B
overlap remain pending until this capture finishes and is inspected.

**Owner validation observation 2026-11-11 09:54:04 CET:** Capture
`ab-completion-N6CeYbWC` has both per-source start messages; the B message was
written at 09:50:07. From the sequential validator code, reaching B establishes
that A passed NAS report/unit/header checks and summary collection. B completion
and overall acceptance remain unverified: no exit-status file exists and the
final summary partial is still empty, as expected until both sources finish.
PID 1464885 is runnable, with 538 CPU seconds over 542 elapsed seconds, 99.2%
reported CPU and 23,280 KiB RSS. Its SQLite scratch is 3,765,223,424 bytes and
the NAS OS filesystem has about 400 GiB free. Exact captured inventory sizes
are A=1,224,710,226 and B=1,597,208,934 bytes. No inventory descriptor was observed;
this is consistent with subsequent SQLite parent/summary checks, not evidence
of a failure. Only observation 1 was supplied, so no 15-second counter delta is
claimed. Leave the existing batch running; require its completed validation,
transfer and controller checks before acceptance or overlap analysis.

**A/B evidence acceptance 2026-11-11:** Owner output reports file 10 completed;
local inspection confirms `ACCEPTED.txt`, identical NAS/controller validation
summaries, NAS validation exit 0 and retained successful transfer-check output in
`/var/lib/ktchn8s-nas-migration-20261110/ab-completion-N6CeYbWC`.
The full captured generations, unchanged helper, command/unit/journal evidence
and all seven available health snapshots are retained there under
`received/ab-completion-N6CeYbWC`. Their original NAS copies remain intact.
The previously inspected `ExecStart`/invocation identities match this run.

| Accepted inventory | A | B |
| --- | ---: | ---: |
| Total entries | 2,644,514 | 2,644,483 |
| Regular-file paths | 2,242,022 | 2,241,992 |
| Directories | 389,676 | 389,675 |
| Symlinks | 12,589 | 12,589 |
| FIFOs / sockets | 6 / 221 | 6 / 221 |
| Logical regular-file bytes by path | 12,322,542,459,865 | 12,288,773,198,904 |

A generation `d80cec2c-13f3-4e0a-a402-9a6881a96852` has whole-file SHA-256
`b7350f2df3456abe9ecf541d31da0c72bb827e59fc0a985b557de7933a361a93`;
B generation `62cd592f-fdd7-4391-b068-8d56e729ba46` has whole-file SHA-256
`dbe3e3b201f5ca48031aaac48e949029fe0349dce67ac8d0363bceeeb223e77b`.
Counts and byte totals alone do not establish equal content or recovery coverage.
The 227 special entries on each source require explicit later dispositions;
they were inventoried successfully, not read as regular files or discarded.
Task 6.1 remains open for C and the agreed source-set decision; 6.2/6.3 copying
has not started. C stays disconnected pending discussion.

**Report-only overlap preparation 2026-11-11:** The owner authorized examining
A/B overlap after validation/preservation. Project-root files 12/13 provide a
controller-only analysis using the accepted inventory bytes. It rechecks full
generation digests and accepted counts while building a compact SQLite index;
content equality uses BLAKE3 plus size. It groups distinct content before joining
so duplicated files do not produce all-pairs candidate output. It reports shared
and source-only content/path totals, exact-path differences, metadata-signature
agreement and special-entry paths. Original datasets/evidence remain unchanged;
this does not replace copy verification, dispositions or independent-copy gates.
Five disposable tests passed without skips (run
`9bf1b49e-0e33-412a-816c-83539ded4d53`, exit 0), including duplicates, moved names,
same-path content/metadata changes, unusual names, corruption, unaccepted input,
input-byte preservation and output overwrite refusal. Launcher Bash syntax and
`git diff --check` passed. Actual overlap analysis was launched locally using
scratch directory `/tmp/ktchn8s-ab-overlap-20261111-0913`; completion follows below.
No NAS commands run.

**Overlap completed 2026-11-11:** Captured run
`2c66e96f-078f-481e-b964-01c7f5e5b056` exited 0 after 194.591 seconds
(09:13:42–09:16:57 UTC). It read the preserved reports, reconciled the original
accepted hashes/counts and produced a 4,398,100,480-byte SQLite index; about
33 GiB remained free on the controller root filesystem. No source data was read.
Independent totals/detail-list cross-checks passed in run
`9d07e7f2-52d9-4f22-a884-1a1cd0bcabe2` (exit 0).

| Regular-file content category | Distinct BLAKE3+size values | Logical bytes, duplicates counted once |
| --- | ---: | ---: |
| Present on both A and B | 1,131,387 | 11,870,496,541,949 |
| Present only on A | 30 | 34,299,613,854 |
| Present only on B | 5 | 530,352,971 |

The A-only and B-only contents each occur at one path on their respective source.
Shared content occurs at 2,241,992 A paths and 2,241,987 B paths; adding the unique
paths reconciles the accepted regular-file counts exactly. These logical totals
are not physical allocation estimates and do not establish hardlink equivalence.

Seventeen A-only document-archive files account for 34,299,437,462 bytes; the
remaining A-only files total 176,392 bytes, including a readme and apparent QNAP
bookkeeping. B-only paths are two `.job_config` files, `aquota.user`, `.qextension`
and a 530,338,965-byte file under `.md5datadir`. Their apparent bookkeeping role is
an inference from paths; contents have not been inspected and no discard is
authorized. A remains the selected initial-copy source, not a declaration that
all differing A versions are authoritative. Preserve both versions pending
explicit dispositions and any C evidence.

At exact matching relative paths, 267,525 regular files were paired: 267,523
have equal bytes and restorable metadata signatures; only `aquota.user` and
`.qextension` differ. Of 24,003 matching directories, four have differing metadata
signatures. All 254 matching symlinks and the 6 FIFOs/221 sockets match their
restorable signatures. Most entries have different backup-container paths
(`bet-backup/...` versus `mag-backup/...`), so this is not a normalized-tree or
hardlink-topology equivalence claim. Original inventories retain all identities.

**Durable overlap artifacts:** Private, Git-ignored directory
`.nas-audit-evidence/ab-overlap-20261111/` (mode 0700) now contains `summary.json`,
`unique-files-A.jsonl`, `unique-files-B.jsonl`, `same-path-different-files.jsonl`,
`special-entries.jsonl`, and `analysis-script-as-run.py`. Raw private path lists
are intentionally not copied into tracked docs. Summary SHA-256:
`541da00d0912c4563f65125d8d7884703e47068dd6e79c34d212af12406fa60a`;
as-run script SHA-256:
`b2ee0374de7dba71c1bf1a77075dc7f812bed3a511866aee2fd9d00f2adf5dc5`.
The accompanying `SHA256SUMS` binds all five result files and the as-run script;
its SHA-256 is `213042c5bb832e56853243c23a57335d2ccd90729c8cad53a4dd546d593f82a0`.
`README.txt` records completion, grouping semantics and evidence limits beside
the private results.
The 4.1 GiB SQLite index remains disposable derived scratch under the `/tmp`
directory; completed summaries and difference lists survive its removal. Source
inventories/job evidence remain in the independent `/var/lib` capture above.

**Overlap review and follow-up 2026-11-11:** Isolated code-reviewer (OpenAI)
approved source and completed-summary consistency with no findings, then approved
the final launcher/documentation changes. External PAL `clink` used `claude`
(Anthropic; observed `claude-opus-5-5`, configured model unknown); `agy`/`codex`
executables unavailable and `gemini` retired. Criteria and candidate Read receipts
were observed; an attempted task-note Git diff was denied, and those notes were
read directly. External review returned COMMENT with four P3 observations and
no P0–P2: temporary-sort filesystem, completion-marker documentation, top-group
labeling, and launcher usage/failure messages. The launcher now sets
`SQLITE_TMPDIR` to the checked filesystem, shows explicit Bash usage and a
low-space error. Documentation now states that only completed `summary.json`
marks success; detail files without it are provisional. First-ancestor grouping
is explicitly defined: direct root entries belong to `.`; group counts are not
subtree counts including their own root. The internal reviewer accepted this
existing convention; it was clarified rather than changing calculated results.
No systemic findings require indexing.

The calculation code is unchanged from the completed full run (AST-equivalence
check `62832672-6308-46af-86d4-540f14bcebc8`, exit 0); final launcher syntax passed
(`97ebe9dc-9d96-445d-8f6c-77f73d8d668d`). The external focused follow-up closed
all four P3 observations and independently reconciled the completed summary's
counts/bytes, while retaining COMMENT for documentation/evidence limits. It had
read the earlier in-progress task note before the completion record above was
added; that requested durable record is now present. Its additional request to
bind detail-list digests is satisfied by the retained `SHA256SUMS` above. Neither
reviewer treats content overlap as dataset-copy or source-release acceptance.
Owner/assistant next: discuss C's role and review the 35 unique file contents;
do not infer discard authority from overlap or start copying under a changed
sequence without the explicit source-set/order decision. Task 6 remains in progress.

**Accepted requirement change 2026-11-11 — owner:** After comparing the existing
`copy → hash staging → sort → hash final` sequence with the lower-I/O alternative,
the owner selected the latter: “Doing a full intermediate read only to do another
full read of the sorted result is excessive.” This supersedes the former Task
6.2 full staging inventory/path-compare requirement and Task 6.3 staged-delta
readback. Source inventories remain authoritative for expected bytes; use them
to plan deltas and provisional dispositions. Task 6 requires successful rsync
copy receipts and metadata-only dry-run checks, not verified destination bytes.
Task 7 remains responsible for full final content/metadata/disposition acceptance.
The dependency stays 6 → 7 → 8: completing Task 6 does not authorize any source
release. Keep all original entries unchanged and available until final acceptance
and each drive's later recovery/parity gate. No copies or audits were launched by
this documentation change.

**Trade-off and boundaries:** Content problems may be discovered after sorting;
the per-source/path ledger must locate originals for repair. The final comprehensive
audit, served-media UID/GID-1000 read-only access audit, independent-copy checks,
parity sync/full scrubs and failure retries remain required. Thus the change
removes a staging-sized read, not all subsequent reads. C stays disconnected;
the separate proposal to copy A before C's inventory is not settled by this
verification-timing decision. Existing completed evidence remains valid. Earlier
execution notes describe the then-current requirements and are retained as history.

**Next operator observation:** Project-root file 14,
`nas-migration-14-copy-a-preflight.txt`, checks A's expected UUID/RO/no-recovery
mount, rsync availability/capabilities, current pool/branch mounts and space,
and absence of the proposed staging destination on the pool and all four known
branches. It performs no copy, hash, mount change or source scan. Owner to execute
and return output; assistant to reconcile topology/capacity before preparing a
copy batch. This independent readiness check does not settle C's sequencing or
authorize a copy. Strict MkDocs validation passed for the revised plan (run
`eae779c8-fa6e-41e9-8984-7a519a29b2cb`, exit 0); existing non-nav/info messages and
the known virtualenv pip-launcher warning remain unrelated to this change.
File 14's controller/remote Bash syntax checks passed (run
`df046622-1199-4dff-b625-b6bad7bcfc7d`, exit 0); `git diff --check` passed.
These checks did not contact the NAS or establish live copy readiness.

**Preflight diagnostic update 2026-11-11:** Owner supplied only the timestamp
`2026-11-11T12:08:48+01:00` from file 14. This does not establish completion or
identify the cause: the next operations check hostname and rsync availability,
and previously could exit without an explanation. File 14 now prints each early
phase and the reported hostname, explicitly reports wrong-host/missing-rsync
failures, and reports unexpected command failures with status and command.
Staging-parent failures are explicit too. No copy or installation is included.
Local admission fixtures exercised wrong hostname, missing rsync, present rsync
and hostname-command failure, with expected statuses/messages; both Bash bodies
passed syntax checks (run `e7f3d5c5-5195-43f9-a8c6-99ffae634bb9`, exit 0).
Owner: return the revised preflight output; actual hostname/tool availability and
mount/capacity readiness remain unverified. Do not infer missing rsync solely
from the timestamp, and do not treat this diagnostic repair as a passed preflight.

**Owner preflight result 2026-11-11 12:11:51 CET:** The hostname is confirmed as
`yggdrasil`; file 14 stopped because `command -v rsync` found no executable.
No source/destination mount or capacity checks ran after that failure. A PATH
miss alone does not prove the package is absent. File 14 now also checks the
usual absolute binary locations, and project-root file 15
(`nas-migration-15-install-rsync.txt`) reports an existing executable or installs
the configured Debian repository candidate if none is found. It checks root/host
and OS identity, refreshes package indexes with errors fatal, records/pins the
selected rsync version for this transaction, disables recommended packages and
refuses package removals. Required dependencies may be installed or upgraded;
this is not a general upgrade, autoremove or storage-role application.
Setup logs/version records go to a fresh `rsync-setup-*` NAS spool directory.
Package operations have not been executed by the assistant. Owner: run file 15,
then rerun file 14 on success and return both outputs. No copy begins in either
file. Bash syntax and mocked preflight admission checks passed (run
`45fdef68-f0c8-46ee-ba9d-ec9bfc408521`, exit 0); APT execution remains unverified.

**Owner package-management policy 2026-11-11:** Packages installed manually on a
host must also be represented in Ansible. Added `rsync` and the previously
manually prepared `b3sum` to the storage role's shared base package list with
explicit `state: present`; the existing `smartmontools` entry is retained.
The role already targets the NAS through `metal/storage.yml`; no cluster-node
package list, disk/mount task, service or scan invocation was changed. Debian
and Fedora provide both package names; actual repository/version availability
remains a host execution check. `acl` is already managed by the dedicated audit
acceptance play, so it needs no duplicate declaration.

This supersedes the earlier manual-only ownership of the NAS's b3sum package,
not the requirement to compare tool versions or keep audit execution separate.
File 15 remains the targeted live-host fix for rsync and now names its Ansible
declaration. It does not reinstall b3sum or apply the full storage role. No host
package change or storage-role application has been executed by the assistant;
operator install/preflight output is still required before copy readiness.
Offline syntax validation loaded the actual storage role through a temporary
play with synthetic localhost inventory under Ansible Core 2.19.4; it passed
without executing tasks or using the production inventory. File 15 Bash syntax
and `git diff --check` also passed (captured run
`5b97a53b-0af7-4eff-bd27-51dc4157c141`, exit 0). This confirms syntax, not a live
package transaction or role idempotence on the NAS.

**Package declaration review 2026-11-11:** The isolated code-reviewer and PAL
`clink` external reviewer approved the scoped four-line package declaration and
related docs/comments. External client `claude` used observed model
`claude-opus-5-5` (Anthropic; configured model unknown); `agy`/`codex` executables
were unavailable and `gemini` retired. Common-criteria and relevant-source Read
receipts were observed. No reviewer ran commands or contacted the NAS. No P0/P1
systemic findings require indexing. External review retained these nonblocking
follow-ups rather than claiming host installation or provenance was verified:

- **Existing Debian cache ordering — assistant before fresh/direct storage-role
  application:** The shared package task precedes `setup_debian.yml`'s cache
  refresh. Missing packages with stale indexes can fail installation. Deferred
  from this package-list change because file 15 refreshes indexes before the
  current targeted install. Before relying on a fresh/direct role application,
  ensure the Debian refresh precedes required package installation and verify
  that missing-package/stale-cache and already-present cases behave correctly.
- **b3sum package provenance — operator/assistant before the next full role apply:**
  The tested executable is `/usr/bin/b3sum` version 1.8.1; package-manager ownership
  was not recorded. Query its dpkg package/version/ownership and reconcile that
  with the executable before applying package convergence. If its actual tool
  version changes, perform the already-required version comparison/revalidation.
  Deferred because file 15 only installs rsync and no full role apply is requested.

**Owner install/preflight output 2026-11-11 12:32:41–46 CET:** File 15 installed
Debian security-repository package `rsync=3.5.0+ds1-0+deb13u1` with APT 3.0.3:
one new package, zero upgraded/removed, no autoremove; rsync service was not
started. Debconf fell back to noninteractive and package configuration completed.
`/usr/bin/rsync` reports 3.5.0/protocol32 with hardlink, ACL, xattr, symlink and
special-link capabilities. Setup evidence is at
`/var/log/snapraid/migration/20261110/rsync-setup-c4VO8W5U`.

File 14 confirms A's original serial/WWN, filesystem UUID and
`ro,nosuid,nodev,noexec,relatime,norecovery,stripe=128` mount through vg288/lv2.
The pool is mounted writable as mergerfs; all four original ext4 branches are
mounted `rw,noatime` with recorded UUIDs. Available bytes: pool
68,109,913,055,232; data1/data3 each 17,027,478,261,760; data2/data4 each
17,027,478,265,856. Each branch alone exceeds A's 12,322,542,459,865 logical bytes,
with substantial metadata headroom. The staging destination is absent on the
pool and all branches; the OS spool has about 403 GiB free. These are current
readiness observations, not reservations or evidence that copying has occurred.

**Accepted source-order change 2026-11-11 — owner:** In response to the explicit
ordering question, the owner selected “Copy A now; inspect C later”. This
supersedes the old all-source-inventories-before-any-copy gate and the earlier
notes leaving that decision unresolved. A may be copied after its accepted
inventory/preflight. C stays disconnected until its inspection is separately
prepared; C's complete inventory/comparison remains required to finish Task 6
and for final reconciliation/release. All source originals remain intact.

**Prepared A copy batch:** Root file 16 starts one retained
`nas-copy-A-20261111.service` using reviewed rsync 3.5.0 flags, local paths,
`-aHAX`, numeric IDs and nanosecond timestamp comparison, without deletion or
a staging hash. It rechecks source identity/RO flags, accepted source-report
digest, exact mounted branch UUIDs, runtime mergerfs branches/create/inode policy,
fresh destination/job paths and capacity before staging creation. Controller
launch receipts go to the independent workspace's `copy-A-20261111` directory;
NAS per-file, progress and error logs go to the matching spool directory.
File 17 reads retained unit state, bounded log tails and space without walking
the dataset. An uncertain launch or failure requires inspection, never an
automatic restart/retry. No copy has been executed by the assistant.

**Staging/access detail:** A's accepted root entry is UID/GID 0:0, mode 0777.
Use root-owned mode-0700 `99_tmp/driveA` as the outer directory and preserve the
original tree/root metadata in its `data` child. This limits ordinary access;
the operator must still keep other clients/local writers out of staging. Do not
interpret the outer directory as an original source entry in the disposition
ledger; account for/remove the empty staging wrapper before final verification.

**Metadata-check detail:** Copy preserves hardlinks with `-H`. The later dry-run
uses `-aAX` without `-H`: mergerfs's accepted `path-hash` mode gives hardlinked
names different presented inode numbers, while rsync's receiver identifies an
already-correct hardlink through equal device/inode values. Therefore rsync's
hardlink dry-run is not a reliable backing-identity gate on this pool. Final
verification still uses the helper's `--identity mergerfs` checks. Sources:
[mergerfs 2.41.1 inode calculation](https://trapexit.github.io/mergerfs/2.41.1/config/inodecalc/)
and [rsync 3.5.0 hardlink handling](https://github.com/RsyncProject/rsync/blob/v3.5.0/hlink.c).

**Copy-batch local verification 2026-11-11:** Twelve disposable checks passed
without skips (run `5f579924-5ec7-4966-85bc-2ac9d4661ff0`, exit 0), covering
read-only admission, wrong source/disk/branch identities, writable source,
unexpected runtime branches/create policy, existing staging and low capacity,
plus both controller/remote Bash bodies. A real local rsync fixture using the
extracted copy flags preserved bytes, hardlinks, symlinks, empty directories,
newline filenames, xattrs and the source-root/private-wrapper modes. It also
confirmed that a same-size/mtime content mutation is invisible to the metadata
dry-run: final content verification remains necessary. This fixture used local
rsync 3.2.7/protocol31, not the NAS's 3.5.0/protocol32 or actual mergerfs/systemd;
privileged special-file handling and real copy completion remain unverified.
The full fixture is `/tmp/test_nas_copy_batch_20261111.py`; no NAS calls ran.

**Copy-batch review and corrections 2026-11-11:** The isolated code-reviewer
approved the scoped launch/status preparation, then approved the final changes.
PAL `clink` external review (`claude`, observed `claude-opus-5-5`/Anthropic,
configured model unknown) returned COMMENT with four P3 observations and no
P0–P2; criteria/source Read receipts were observed. `agy`/`codex` were unavailable
and `gemini` retired. No systemic findings require indexing. Corrections capture
SSH stderr in the controller receipt, bind the mounted UUID **and major:minor**
to A's disk tree, align actual runbook paths/flags and clarify missing-unit and
receipt-publication handling. File 17 now explicitly treats lost unit state as
unverified; log endings cannot replace completion evidence. Fourteen local tests
passed after these changes, including a cloned UUID on a different mounted
device and retained SSH failure output (run
`7ef353ec-ef70-4d01-9538-3ac1e8b8ac6e`, exit 0). The internal reviewer rechecked
the changed evidence with no findings. Strict MkDocs passed (run
`4c5c4d1e-c677-4985-9b76-4cc9db8dbdff`), as did `git diff --check`.

**Remaining copy work — owner/assistant:** Owner monitors the launched copy
with file 17. After successful completion,
assistant prepares the metadata-only check and transfer/checksum-preservation of
completed unit/log receipts to the independent workspace before any reboot or
unit cleanup. These depend on the actual copy outcome and are not claimed done.
If admission/launch/copy fails, preserve controller/NAS receipts and partial data;
assistant must inspect unit, evidence and staging state before issuing a targeted
retry. No generic resume or automatic restart is authorized by the launch batch.

**A copy startup accepted 2026-11-11 13:11:44 CET:** Owner output and the locally
inspected controller receipt confirm `nas-copy-A-20261111.service` is
`active/running`, MainPID `1465367`, invocation
`379fe650ddf74d8ab1f5d1d854b85940`. Its exit timestamp is empty and
`ExecMainCode=0`; `Result=success`/status 0 at this point establish startup only.
The actual command matches the reviewed source/destination and preservation flags:
Betelgeuse → `/mnt/storage/99_tmp/driveA/data/`, without deletion or a staging hash.

Live admission also confirmed A's mounted device `253:3` belongs to the expected
disk tree, its original UUID and RO/no-recovery flags, all four branch UUIDs,
`/mnt/data1=RW:...:/mnt/data4=RW`, `category.create=mfs`, `inodecalc=path-hash`,
recorded per-branch headroom and the accepted source-inventory SHA-256.
Controller receipt: `/var/lib/ktchn8s-nas-migration-20261110/copy-A-20261111`;
NAS receipt/logs: `/var/log/snapraid/migration/20261110/copy-A-20261111`.
The controller's captured launcher matches the reviewed project file, SHA-256
`877454e17e8ed786c5a9753c68d4214a24f2a370d2b01addc533bab7e02acbd2`.
The owner executed the launch; the assistant only inspected the local receipt.
C remains disconnected. Completion, metadata-only checking and completed receipt
publication remain open; do not rerun file 16 or restart this invocation for status.

**Owner copy checkpoint 2026-11-11 13:16:05 CET:** Same invocation/PID remains
active/running and unfrozen, with no exit timestamp. Latest supplied progress is
50,185,882,241 bytes, `xfr#4627`, `ir-chk=1301/7700`, displayed rate 183.78 MB/s;
stderr is empty. Pool usage is about 47 GiB, spread roughly 12 GiB per branch,
and the OS spool still has about 403 GiB free. This shows ongoing copying with no
reported errors so far, not completion. The displayed 89% covers discovered work
while incremental enumeration continues, not all A data. The reported bytes are
about 0.407% of A's recorded logical bytes by path; that ratio is only context,
not a hardlink-adjusted completion percentage. File 17 now documents the `ir-chk`
interpretation; executable commands were unchanged. Leave the existing copy running.

## Task 7: Migration — sort into numbered homes (manual ops)
- **Status:** pending
- **Depends on:** Task 2, Task 6
- **Size:** M
- **Can run in parallel with:** Task 4, Task 9, Task 12
- **Docs:** [implementation.md#migration-runbook](./implementation.md#migration-runbook)

### Subtasks
- [ ] 7.1 Curate/move content per the mapping with collision stops and explicit keep/deduplicate/discard records; tooling fixtures must already have passed Task 13
- [ ] 7.2 Apply `implementation.md#migrated-content-access`: record necessary permission/ACL transformations, preserve archive metadata, and prove actual migrated-media reads as UID/GID 1000 through a temporary RO NFS mount; remove that client afterward
- [ ] 7.3 Run the helper's comprehensive destination-content reconciliation after sorting against all source inventories and the ledger; require metadata/content/disposition checks and access acceptance against the same ledger generation, with no unresolved staging entries. Repair mismatches from unchanged originals and rerun the required checks before acceptance
- [ ] 7.4 Check retained content against Task 2's finalized exclusions, archive the accepted evidence before the freeze, and follow `implementation.md#migration-evidence` through Task 8



## Task 8: Parity enablement & drive release (manual ops)
- **Status:** pending
- **Depends on:** Task 2, Task 7, Task 12
- **Size:** M
- **Can run in parallel with:** Task 4, Task 9
- **Docs:** [implementation.md#parity-enablement](./implementation.md#parity-enablement)

### Subtasks
- [ ] 8.0 Both parity drives are on SN02 firmware version. Upgrade firmware and disable PowerBalance and EPC features (See `how_to_prepare_seagate_exos_drives.md`). Research and confirm optimal settings for these drives in a homelab setup. Ensure that PowerBalance and EPC disabled features are enough to prevent unnecessary load_cycle_count. Confirm all drives on latest firmware and correct settings, record current SMART data on all drives and compare with earlier attributes (obsidian vault: evergreen-dissemination-light/010_Black_Hole/proxmox_behemoth_installation_log.md; was only recorded for the data drives).
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
