# Tasks: NAS Storage Directory Layout

> Design: [design.md](./design.md)
> Implementation: [implementation.md](./implementation.md)
> Status: in-progress

Keep this file to task status and actionable work. The detailed destination
review, approvals, source identities, command receipts and execution history are
private under `.nas-audit-evidence/`. The current review is
`.nas-audit-evidence/reviews/destination-map-review.md`; preserve and transfer
private evidence separately from Git. Do not copy inventory-derived filenames,
device identifiers, run transcripts or approval-by-approval logs into tracked docs
or documentation snippets.

The owner has approved the complete A destination map. A's provisional copy and
targeted metadata repair are accepted; no inventory, copy or repair restart is
needed. B's comparison is closed and B is excluded from active destination
verification. A sorting and its sealed ledger are complete. On 2026-11-17 the owner
deferred C in its entirety, confirmed it unmounted/disconnected, and selected
A-only acceptance in order 7.2, 7.3, 7.4. That sequence completed on
2026-11-18. On 2026-11-20 the owner reviewed the completed C comparison
and selected zero C additions. The joint B+C full scrub of A's verified
dataset passed on 2026-11-21. The owner released A as an offline cold spare.
The operator archived the release evidence and restored routine maintenance.
Exact observations and commands stay private.
Originals and receipts remain intact through final acceptance and release gates.
There is no routine staging rehash. The operator executes workstation and NAS/cluster
commands; the assistant prepares and explains each step without executing it.

## Task 1: Tree skeleton via storage role
- **Status:** done
- **Depends on:** —
- **Docs:** [Tree skeleton](./implementation.md#tree-skeleton)
- [x] Implement the layout, ownership/modes and generated legend; complete repeat-apply and preservation acceptance.
- New approved layout additions belong to Task 7 preparation; the original acceptance remains historical evidence.

## Task 2: SnapRAID excludes and parity configuration
- **Status:** done
- **Depends on:** —
- **Docs:** [SnapRAID configuration](./implementation.md#snapraid-excludes)
- [x] Implement root-anchored exclusions and correct multi-parity directives; verify isolated configuration cases.
- Task 8 records the accepted live configuration, full sync and full scrub.

## Task 3: Storage test tooling
- **Status:** done
- **Depends on:** —
- **Docs:** [Development tooling](./implementation.md#devshell-b3sum)
- [x] Add and verify the locked checksum and Molecule tooling.
- Task 14.2 covers Debian package-cache ordering and checksum-tool provenance before fresh/full role convergence.

## Task 4: Prepare the NFS media PV offline
- **Status:** done
- **Depends on:** Task 1
- **Docs:** [NFS media share](./implementation.md#nfs-media-share)
- [x] Prepare and render the media PV contract, retaining existing storage semantics.
- Deployment is part of Task 5 after parity acceptance.

## Task 5: Jellyfin stack remount end-to-end
- **Status:** pending
- **Depends on:** Task 4, Task 8
- **Docs:** [Media application rollout](./implementation.md#jellyfin-remount)
- [ ] 5.1 Replace the old claim with the media PVC/PV binding.
- [ ] 5.2 Use one volume mount per linking container; keep Jellyfin mounts read-only and Ceph storage for configuration.
- [ ] 5.3 Configure the actual writer processes as UID/GID 1000.
- [ ] 5.4 Align downloader and application paths without remote-path translation.
- [ ] 5.5 Update the media guide, render both charts and record rollout behavior.
- [ ] 5.6 Release both charts together after Task 8; retire old resources only after their state is safe.
- [ ] 5.7 Complete live import, hardlink, seeding, promotion/rescan, playback, read-only and NFS acceptance. Keep network smoke checks separate.

## Task 6: Migration — source comparison and provisional copies
- **Status:** done
- **Depends on:** Task 1, Task 3, Task 11, Task 13
- **Docs:** [Migration runbook](./implementation.md#migration-runbook)
- [x] 6.1 Preserve accepted A/B evidence. After A sorting, establish C's inspected read-only source mount and publish its complete inventory.
- [x] 6.2 Complete and preserve A's provisional copy and metadata-only acceptance. Stored content remains subject to final verification.
- [x] 6.3 Compare C with retained A coverage and final mappings, account for every source entry, and verify the scope of any additions. The owner selected zero additional keepers.
- The owner resumed C on 2026-11-19 after the A-only acceptance, completed
  its read-only setup on the NAS and started its inventory.
- B needs no new inventory, comparison, copy, alias ledger or metadata transformation.

### Execution context

- **2026-11-17, explicitly accepted:** perform C inventory/comparison from its USB
  connection to the workstation. The owner executes commands/scripts; the assistant
  prepares and explains them. This supersedes the previous C hold.
- **Operator-reported:** C's read-only preparation succeeded, with device and
  filesystem write protection verified by the script's completion output.
- **2026-11-17, explicitly deferred:** the owner stopped the USB full-inventory plan
  before any scan began, then deferred C in its entirety. Resume only on a new owner
  instruction; prepare identity/mount checks for the chosen host before inventory.
- **2026-11-17, accepted later-C scope:** copy additional retained content and check
  every addition in full against C's inventory, including expected metadata and links.
  Recheck existing entries affected by copying or permission changes. Unchanged A
  payloads do not need a full rehash. Assistant owns preparing the scoped audit-input
  mechanism and baseline/change evidence when C resumes; the current helper has no
  incremental mode. Acceptance requires complete C accounting and zero unexplained
  differences in the affected scope. This replaces the earlier combined full rehash.
- **2026-11-19, operator-reported and receipt reviewed:** A is disconnected.
  C's recorded disk and ext4 filesystem identities matched on the NAS. The
  mount completed with device write protection, read-only filesystem and
  journal replay disabled. The initial status receipt matched the launch and
  showed partial output. Its first NAS SMART observation is retained privately.
- **2026-11-20, scan finished.** The operator's completion receipts match the
  original invocation and show a successful exit and an accepted footer with
  zero failures. The operator preserved the report and receipts in the
  independent controller archive. The validator checked the complete
  generation, source binding, entry count and NAS-to-controller digest.
  The saved acceptance marker and validation summary agree. Task 6.1 is complete.
- **2026-11-20, 6.3 comparison complete.** The private controller report
  accounts for every C entry against A's accepted inventory and amended
  final mappings. Two regular-file versions have no payload match on A.
  The owner chose A's existing destinations and metadata and omitted the two
  versions and C's counterparts to A's omissions. The private decision binds
  each disposition to the checksummed comparison. Both the copy set and the
  affected-destination verification set are empty.

## Task 7: Migration — sort into numbered homes
- **Status:** done
- **Depends on:** Task 2; Task 6.2; C work is deferred outside the current A-only acceptance
- **Docs:** [Migration runbook](./implementation.md#migration-runbook)
- [x] 7.0a Complete owner review of the full A destination map, including collection boundaries and shared subject names.
- [x] 7.0b-policy Record the explicit owner-approved discards and operator-confirmed deletion; the existing auditor needs no change. Exact approvals and disposition rows remain private.
- [x] 7.0b-draft Expand the approved A map into a complete private draft with all source entries and approved discards; verify source/routing bindings.
- [x] 7.0b-metadata Record observed deletion-parent timestamps and non-time container expectations privately; preserve other source metadata.
- [x] 7.0b Capture final timestamps for directories changed by sorting and seal the A audit ledger, including declared split/merge container expectations. Preserve this generation; later C contributions need new evidence covering their additions and affected existing entries. Sealing is not content/access acceptance.
- [x] 7.0c-layout Implement, locally verify and apply the four approved directory/legend additions.
- [x] 7.0c Complete the first operator batch and its namespace/metadata preflight. Every later move batch still requires its own collision and metadata checks.
- [x] 7.1 Sort A using the reviewed map, collision stops and recorded dispositions while C remains disconnected; integrate C additions later under 6.3.
- The sealed A ledger includes the approved directory accounting correction.
- All retained A payloads and source records are moved. Confirmed-empty staging wrappers are removed and affected destination metadata is captured. This establishes sorting completion, not final content/access acceptance; exact evidence stays private.
- [x] 7.2 Check migrated-media directory listing/traversal and file-open/minimal-read access as UID/GID 1000 through temporary read-only NFS; remove the client. Accepted with one specific owner-approved access exception. Do not hash or read complete media files in this step; full content verification belongs to 7.3.
- [x] 7.3 Verify A's final tree against its unchanged source inventory and matching ledger. Exclude B and deferred C. Require complete content/metadata/link/disposition and access acceptance within A's scope, with no unresolved staging entries.
- [x] 7.4 Confirm parity inclusion for the accepted scope, archive evidence before the freeze and preserve independent evidence through Task 8. Later C writes require a new accepted dataset state before parity work can proceed on that changed dataset.
- Owner-selected order is 7.2 → 7.3 → 7.4. A-only acceptance does not certify C
  coverage or authorize release of C; its later source accounting remains Task 6.
- **7.2 accepted on 2026-11-17.** The owner approved one access exception.
  The entry remained in the full verification scope. The operator confirmed
  mount removal and preserved the original difference report and receipts.
- The bounded-read helper passed all 36 operator-run tests on workstation and
  NAS. Independent source review is complete. The earlier full-read permission
  run was cancelled, its cleanup confirmed and its launcher disabled; do not
  restart it or repeat completed tests merely to recover context.
- **7.3 accepted.** The operator independently validated the complete report
  against the original A inventory and sealed ledger. All retained entries matched.
- **7.4 accepted.** After the approved discards and directory metadata updates,
  all retained A entries fall within the configured parity rules. The operator
  verified the archived evidence and its independent copy. Writers and promotions
  stayed frozen through the final Task 8 scrub.
- Keep backup/library/vault internals intact except for exact approved omissions; preserve all originals. Record obsolete directory wrappers as merges; do not create empty archival shells or add a blanket timestamp-repair pass.

## Task 8: Parity enablement and drive release
- **Status:** done
- **Depends on:** Task 2, Task 7, Task 12
- **Docs:** [Parity and release](./implementation.md#parity-enablement)
- [x] 8.0 Verify firmware/settings and drive health against private baseline records.
- [x] 8.1 Check B's physical identity/size and independent recovery coverage using completed comparison evidence and surviving A/final mappings. No B destination ledger is required.
- [x] 8.2 Finalize C under Task 6. Verify independent recovery for its retained entries, including C-only additions, on storage that survives both wipes. Verify C's identity and size.
- [x] 8.3 Quiesce maintenance and prepare B and C individually after both release gates pass. Configure both parity levels before starting the job.
- [x] 8.4 Run one explicit full sync with B and C configured, then one full scrub. Require successful exits, unchanged included data, complete coverage and zero errors.
- [x] 8.5 Release A last after successful two-level protection and recovery checks; record its chosen role.
- [x] 8.6 Preserve release/job evidence privately during the freeze, archive it afterward and re-enable maintenance.
- Failed checks or insufficient independent recovery stop the release sequence.
- A-only Task 7 acceptance covers A. C's inventory, retained-content accounting
  and scoped verification precede its release gate.

### Execution context

- **2026-11-21, 8.4 accepted.** The complete controller journal and exit
  receipts match the joint run. Both parity levels participated in the full
  sync and scrub. Both diffs found zero changes. The scrub checked all data
  blocks and reached 100%. Final status confirmed full coverage and zero errors.
- **2026-11-21, 8.5 accepted.** The accepted per-entry A verification and final
  inclusion amendment cover all recorded keepers on the protected NAS.
  There are zero retained exclusions and no retained B or C additions.
  The owner confirmed there are no additional safety copies on A and
  released it as an offline cold spare. Keep its files intact until it is
  needed as a replacement. The current array uses four data disks and B+C parity.
- **2026-11-21, 8.6 accepted.** The NAS archive under `00_meta/migration/`
  matched the independent controller copy by SHA-256. The operator restored
  both inventory flags and verified that the runner and scrub timers were
  enabled, active and scheduled. The archived timer receipt also passed its
  checksum check. The operator added an encrypted copy of the closeout archive
  and receipts to the existing GitHub evidence draft and verified the download
  byte for byte against the controller ciphertext. Keep the controller copy
  until a successful normal sync protects the new NAS archive and receipt.
- **2026-11-20, B/C snapshot reviewed.** The disk identities and four branch
  mappings match the receipts. The private review records a GPT layout for
  either candidate matching the largest data partition, and the retained
  dataset is recoverable from offline A through both wipes. All six drives
  passed SMART. B's direct firmware reads confirm its update. The operator
  subsequently verified both vendor file digests and a positive C firmware
  selector match. C was unmounted normally and remained write-protected.
  C's firmware update completed. Two direct readbacks confirm the new
  revision and passing SMART. The operator restored C's EPC setting after
  activation. PowerBalance and all four EPC timer rows match the pre-update
  baseline. Task 8.0 is complete.
- **8.3, maintenance quiescence verified on 2026-11-20.** The operator
  found no runner or scrub timer files, loaded maintenance units, queued
  jobs or manual SnapRAID processes. The operator subsequently released B
  and C individually. Both partition receipts confirm the planned GPT
  geometry and blank signatures. One Ansible apply mounted both parity
  filesystems and installed the two-level configuration with zero failures.
- **2026-11-20, migration closed.** Offline A supplies the independent
  recovery source for the retained dataset through both planned wipes.
  Keep A intact through the full scrub.
- **2026-11-19, owner-selected sequence.** Shut down the NAS normally and
  disconnect A once fully powered off. Keep A intact as an offline recovery
  copy. No new A/B source scan or live-detachment check is needed. Finalize C
  before building parity on B and C together. The assistant must adapt and
  locally verify the focused play's existing-first-parity-file check for a
  fresh two-level bootstrap before the operator prepares the second partition.
  Leave hardware actions open until the operator confirms them.
- **2026-11-19, operator instruction.** The assistant prepares the code and
  commands. The operator runs all NAS commands, including read-only inspection
  and Ansible. Begin with the private drive-health snapshot for 8.0. Review
  firmware, power settings, SMART changes and the physical branch mapping
  against the private baselines before proceeding to B's recovery check.
  C remains disconnected. Live checks and release decisions are outstanding.
- **2026-11-19, prepared and checked locally.** The read-only snapshot launcher
  retains a fresh controller log on success or failure. The separate
  `metal/storage-parity.yml` play takes the released partition's by-id after
  its gate and reuses the Task 12 configuration. This avoids full storage
  convergence during the freeze. All 20 synthetic preflight cases passed,
  including first/second parity, retries and rejected devices. ShellCheck,
  YAML/Jinja checks for both stages, simulated SSH log capture, and offline
  systemd timer-file checks passed. Independent source review approved the
  configuration path after the runtime timer-mask check was added. The
  first live action was 8.0 in the [runbook](./implementation.md#parity-enablement).
- **2026-11-19, 8.0 snapshot reviewed.** The operator completed the read-only
  collection. The four data-branch identities and all six SMART and power
  readings were checked against the source snapshots and the installation-log
  baseline. The private review records the counter changes and the firmware
  difference. The operator selected B for firmware preparation while C is
  scanning. Use the installed SeaChest tool and the matching vendor package.
  Check B's live RAID/LVM and mount state before any firmware write, then
  capture its revision, SMART and power settings after activation. Leave B's
  source layout intact until both release gates pass. The later operator step
  creates the GPT partition, and the focused Ansible play formats it as ext4.
- **2026-11-19, B firmware update confirmed.** The operator deactivated B's
  logical volumes and stopped its five md devices. The resulting partition
  tree had no mounts or holders. SeaChest activated and validated the selected
  firmware. A separate SMART query confirmed B's identity, new revision and
  passing overall health. PowerBalance matched the baseline. Two current EPC
  idle timers showed enabled after the update. The operator's subsequent
  readback confirmed all four current timers disabled, matching the
  pre-update baseline. Formatting stays under 8.3.

## Task 9: Legend and documentation
- **Status:** done
- **Depends on:** Task 1
- **Docs:** [Legend documentation](./implementation.md#legend-docs)
- [x] Complete the original legend/reference updates and documentation acceptance.
- Task 7 owns the newly approved layout additions. Keep source-specific decisions and execution evidence private.

## Task 11: NFS export lifecycle acceptance
- **Status:** done
- **Depends on:** Task 1, Task 3
- **Docs:** [NFS export readiness](./implementation.md#nfs-export-readiness)
- [x] Complete isolated and live lifecycle, fixed-owner access, remount/recovery, read-only, backing-link and cleanup acceptance.
- Do not repeat completed live runs merely to recover context.

## Task 12: Explicit parity bootstrap and expansion jobs
- **Status:** done
- **Depends on:** Task 2, Task 3
- **Docs:** [Parity job readiness](./implementation.md#parity-job-readiness)
- [x] Implement explicit jobs and verify isolated creation, expansion, interruption/retry, failure propagation and maintenance quiescence.
- Task 8 records the verified two-level protection and drive releases.

## Task 13: Migration inventory and audit tooling
- **Status:** done
- **Depends on:** Task 3, Task 11
- **Docs:** [Migration audit tooling](./implementation.md#migration-audit-tooling)
- [x] Complete the original helper, unit/scenario checks and live tool/access acceptance.
- Task 7 owns the approved dispositions and final ledger; its identified special-entry omissions use existing discard support. Task 6.3 owns later C-keeper input selection. Historical tooling acceptance is not migrated-data acceptance.

## Task 14: Storage provisioning on new and existing NAS hosts

- **Status:** in-progress
- **Depends on:** Task 11, Task 12
- **Docs:** [Task 14 implementation and acceptance criteria](./implementation.md#task-14-storage-provisioning), [provision from scratch](../../../guides/how_to_use_nfs_for_persistent_storage.md#provision-from-scratch)

These follow-ups come from the 2026-11-21 review of `metal/storage.yml` at
`717199f` against `master` (`ee52ee4`). Complete the fixes and the Molecule VM
acceptance run before starting Task 10. Task 8 records the existing array's
accepted migration.

- [x] 14.1 **Disk admission (P1).** Ordinary provisioning in
  `metal/roles/storage/tasks/disks.yml` treats any nonzero `blkid` status as permission
  to format and any zero status as grounds to skip formatting. Check device
  identity, parent, current backing mount and signature before mutation. Accept
  verified existing ext4 and positively identified, explicitly authorized blank
  partitions. Test a blank GPT partition, a retry, an ambiguous probe and
  duplicate or conflicting data/parity devices. The focused parity play already
  has several of these checks.
- [ ] 14.2 **Package bootstrap (P1).** Supply a reproducible, verified SnapRAID
  installer for each supported OS, or document how to produce and stage it.
  The production DEB/RPM inputs are ignored by Git. Even an NFS-only install
  reaches the OS setup tasks. Fix the Fedora mergerfs asset name against the
  pinned release and test the supported OS/version combinations. On Debian,
  refresh the package index before the first package task, verify the source of
  `b3sum`, and preserve any pre-existing `xz-utils` on install or retry.
- [ ] 14.3 **Parity activation (P1).** The main role applies the timer flags
  immediately, and both default to true. Document and verify a reusable
  first-install/expansion path that keeps maintenance paused through the
  explicit full sync, unchanged-data checks and full scrub. Check for active
  manual processes and queued jobs before transition. A repeat apply to an
  accepted array must preserve its chosen maintenance policy and parity files.
- [ ] 14.4 **Disk health (P1 when strict checks are enabled).** Include every
  requested physical disk in the health decision. `smartctl_utils.yml` drops
  nonzero exit statuses, including a failing SMART result. Test a reported
  failure and an unreadable device with `fail_on_unhealthy_drives: true`.
- [ ] 14.5 **Network settings for another homelab (P1).** Make network
  reconfiguration an explicit operator choice. Provide a sanitized NAS
  inventory example using the operator's own SOPS recipients, interfaces,
  gateway, client CIDRs and drive IDs. Remove the personal workstation address
  from reusable defaults. Verify SSH remains reachable after applying network
  and firewall policy. The current check suppresses failure and probes the
  gateway before the networking restart. Exercise firewall validation with the
  target's default shell, including shells without `pipefail`.
- [ ] 14.6 **Repeat apply and backups (P2).** Gate hardware detection on actual need
  and recover when the drivetemp file exists but the module is unloaded.
  `sensors-detect --auto` runs and reports changed every time. Make the
  content-backup timer start and stop according to policy, and make its service
  report copy errors. All configured content files currently share one basename
  and overwrite the same timestamped backup. Define and test which verified
  copy or copies the backup retains.
- [ ] 14.7 **Full-role acceptance.** After 14.1–14.6, run `metal/storage.yml`
  from a clean checkout using the existing Molecule/QEMU tooling. Give the
  guest the documented base OS, pre-partitioned virtual scratch disks and a
  synthetic NAS inventory. Run fresh VM instances in turn for data-only and
  parity-enabled configurations. In each case, write a sentinel file and
  reapply the same inventory. Require zero changes on the second apply and
  verify the file contents, backing devices, active export and timer states.
  Record both recaps and verification results before closing Task 14.

### Execution context

- 2026-11-21, observed at `cbee3df`. Tasks 11 and 12 are complete. The
  existing scenarios prepare filesystems or install SnapRAID before convergence.
  Task 14 exercises the public storage play on disposable guest disks.
- 2026-11-21, implemented. Ordinary admission validates all identities and
  checks them again before mutation. Regression fixtures cover a positively
  identified blank GPT partition, reuse, missing authorization, ambiguous
  probes, duplicate parents and incorrect backing mounts. Existing mounted
  legacy arrays can retain running schedules or adopt prior acceptance
  explicitly. Initial and expanded layouts stay pending through verification.
- 2026-11-21, verified offline. The three focused Python suites passed 17 tests
  and the shell fixture passed 34 parity admission cases. The pinned SnapRAID
  13.0 source built successfully. A synthetic 2 MiB single-filesystem run
  using its test-only device override passed full sync, both diffs and a full
  scrub of eight parity blocks with zero errors. All 15 pinned mergerfs
  artifacts matched the upstream release digests. The public and fixture
  playbooks passed syntax checks. YAML and shell lint passed.
- 2026-11-21, review corrections. Focused admission now succeeds before
  creating a pending marker. The provisioning VM uses sparse 8 GiB disks to
  exceed the mergerfs creation threshold. The verified upstream Fedora RPM
  installs in a local-only transaction. Content backups retain every configured
  copy under its source path in each completed generation.
- 2026-11-21, verified on clean local candidate `2a16e81`. The focused suites,
  lint and Ansible syntax checks passed. Molecule resolved the provisioning
  test sequence. Independent source review found no outstanding code defect
  and left execution acceptance open.
- 2026-11-21, unresolved. The operator owns package installation evidence on
  the target Fedora release. Run the scenario's package-only play twice on a
  disposable guest and retain the installed versions and zero-change retry.
- 2026-11-21, unresolved. The operator owns the two clean-checkout VM runs.
  This workspace has no `/dev/kvm`. Record both first and repeat recaps and
  the guest verification results here before closing the task.

## Task 10: Final verification

- **Status:** pending
- **Depends on:** Tasks 1–9, 11–13, and [Task 14](#task-14-storage-provisioning-on-new-and-existing-nas-hosts)
- [ ] 10.1 Complete the required storage, parity, audit, inventory, network, documentation and live-application checks; retain evidence of actual migration/release acceptance.
- [ ] 10.2 Finalize public documentation and the private operational record; move the completed feature out of WIP when appropriate.
- [ ] 10.3 Complete code review of the implementation.
- [ ] 10.4 Verify conformance with the design and implementation contracts.
- A prior synthetic or scoped review does not replace final acceptance.

## Dependency Graph

```
Layout/tooling readiness → A copy + map approval → A sorting
A sorting → A access audit (7.2) → A full verification (7.3) → evidence/freeze (7.4)
A acceptance + parity-job readiness → applicable recovery/parity/release gates
C inventory/comparison/additions → scoped verification and independent recovery → B+C bootstrap
Parity acceptance + offline PV work → live media rollout
Storage provisioning fixes (14.1–14.6) → full-role acceptance (14.7) → final verification (10)
All implementation and operational gates → final feature verification
```
