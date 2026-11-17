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
A-only acceptance in order 7.2, 7.3, 7.4.
Assume no C contribution for this acceptance scope; this is an explicit scope
decision, not a completed C comparison. Later C additions require a complete
source inventory, explicit mappings and scoped destination verification of every
addition and affected existing entry. Exact observations and commands stay private.
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
- Live configuration, full sync and full scrub remain Task 8.

## Task 3: Storage test tooling
- **Status:** done
- **Depends on:** —
- **Docs:** [Development tooling](./implementation.md#devshell-b3sum)
- [x] Add and verify the locked checksum and Molecule tooling.
- Before fresh/full role convergence, resolve the documented Debian package-cache ordering and checksum-tool package-provenance follow-ups.

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
- **Status:** in-progress
- **Depends on:** Task 1, Task 3, Task 11, Task 13
- **Docs:** [Migration runbook](./implementation.md#migration-runbook)
- [ ] 6.1 Preserve accepted A/B evidence. After A sorting, establish C's inspected read-only source mount and publish its complete inventory.
- [x] 6.2 Complete and preserve A's provisional copy and metadata-only acceptance. Stored content remains subject to final verification.
- [ ] 6.3 Compare C with retained A coverage and final mappings; copy additional keepers directly to chosen homes with collision and metadata checks. Prepare and verify C-keeper audit-input selection without changing the original C inventory or silently omitting ledger entries.
- C is entirely deferred by the owner after workstation read-only setup. No C
  inventory or comparison has run. The owner subsequently unmounted/disconnected C.
  This work no longer blocks A-only Task 7 acceptance.
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

## Task 7: Migration — sort into numbered homes
- **Status:** in-progress
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
- The owner-approved Education directory-only accounting correction is included in the sealed A ledger; all file/bundle routes remain unchanged.
- All retained A payloads and source records are moved. Confirmed-empty staging wrappers are removed and affected destination metadata is captured. This establishes sorting completion, not final content/access acceptance; exact evidence stays private.
- [x] 7.2 Check migrated-media directory listing/traversal and file-open/minimal-read access as UID/GID 1000 through temporary read-only NFS; remove the client. Accepted with one specific owner-approved access exception. Do not hash or read complete media files in this step; full content verification belongs to 7.3.
- [ ] 7.3 Verify A's final tree against its unchanged source inventory and matching ledger. Exclude B and deferred C. Require complete content/metadata/link/disposition and access acceptance within A's scope, with no unresolved staging entries.
- [ ] 7.4 Confirm parity inclusion for the accepted scope, archive evidence before the freeze and preserve independent evidence through Task 8. Later C writes require a new accepted dataset state before parity work can proceed on that changed dataset.
- Owner-selected order is 7.2 → 7.3 → 7.4. A-only acceptance does not certify C
  coverage or authorize release of C; its later source accounting remains Task 6.
- **7.2 accepted, 2026-11-17:** 37,148 entries passed required read access; the
  owner explicitly waived the sole thumbnail-entry denial. The entry is retained
  and remains in 7.3. Cleanup and mount removal were confirmed, and the original
  difference report/receipts were collected and checked independently. No repair
  or new ledger generation was needed. Do not turn the original nonzero result
  into a fabricated clean report or generalize the exception.
- The bounded-read helper passed all 36 operator-run tests on workstation and
  NAS. Independent source review is complete. The earlier full-read permission
  run was cancelled, its cleanup confirmed and its launcher disabled; do not
  restart it or repeat completed tests merely to recover context.
- **7.3 launched, 2026-11-17:** the operator started the reviewed A-only local-NAS
  verification batch. Its last supplied state was active/running at startup.
  Completion, full report and acceptance remain unknown. Inspect this exact job;
  do not relaunch it to check progress. Keep dataset writers stopped. Unit identity,
  immutable input pins and controller/NAS evidence paths are recorded privately.
- Next: obtain the existing 7.3 result; require matching invocation, zero verify/job
  exits and a complete zero-difference report, then collect/check it independently.
  Diagnose any failures before planning repairs or another scan. Only after 7.3
  acceptance proceed to 7.4 parity-inclusion, evidence and freeze work.
- Keep backup/library/vault internals intact except for exact approved omissions; preserve all originals. Record obsolete directory wrappers as merges; do not create empty archival shells or add a blanket timestamp-repair pass.

## Task 8: Parity enablement and drive release
- **Status:** pending
- **Depends on:** Task 2, Task 7, Task 12
- **Docs:** [Parity and release](./implementation.md#parity-enablement)
- [ ] 8.0 Verify firmware/settings and drive health against private baseline records.
- [ ] 8.1 Check B's physical identity/size and independent recovery coverage using completed comparison evidence and surviving A/final mappings. No B destination ledger is required.
- [ ] 8.2 Quiesce maintenance; release B only after its gate, configure first parity and record a successful explicit full-sync invocation.
- [ ] 8.3 Complete a full scrub with zero errors and full coverage before C release.
- [ ] 8.4 Repeat C's recovery/size gate, add second parity, then complete explicit full sync and full scrub.
- [ ] 8.5 Release A last after successful two-level protection and recovery checks; record its chosen role.
- [ ] 8.6 Preserve release/job evidence privately during the freeze, archive it afterward and re-enable maintenance.
- Failed checks or insufficient independent recovery stop the release sequence.
- A-only Task 7 acceptance does not release deferred C. Its later inventory,
  retained-content accounting and scoped verification must precede its release gate.

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
- Actual data protection and disk release remain Task 8.

## Task 13: Migration inventory and audit tooling
- **Status:** done
- **Depends on:** Task 3, Task 11
- **Docs:** [Migration audit tooling](./implementation.md#migration-audit-tooling)
- [x] Complete the original helper, unit/scenario checks and live tool/access acceptance.
- Task 7 owns the approved dispositions and final ledger; its identified special-entry omissions use existing discard support. Task 6.3 owns later C-keeper input selection. Historical tooling acceptance is not migrated-data acceptance.

## Task 10: Final verification
- **Status:** pending
- **Depends on:** Tasks 1–9 and 11–13
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
Deferred C → later inventory/comparison/additions → scoped verification → C release eligibility
Parity acceptance + offline PV work → live media rollout
All implementation and operational gates → final feature verification
```
