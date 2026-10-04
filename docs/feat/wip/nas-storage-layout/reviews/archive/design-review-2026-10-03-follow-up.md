# NAS Storage Layout — Full Readiness Review

Reviewed: 2026-10-03 · Baseline: `7c15aae` · Method: kk:review-design, standard

**Scope:** [design](./design.md), [implementation plan](./implementation.md),
[tasks](./tasks.md), [AD-0003–AD-0007](../../../reference/architecture/decision_records.md),
and both existing review/resolution records as historical context.

**Overall assessment before corrections:** CONCERNS_FOUND

**Current disposition:** all six findings addressed in the planning documents;
implementation and live acceptance remain pending.

**Summary:** 6 findings: 0 critical, 1 high, 4 medium, 1 low.

The architecture and document organization are workable. The original nine corrections
remain represented in the plans. This broader read found gaps where the expanded
workflow crosses task and validation boundaries, plus one migration-access concern.
The documents are suitable for starting independent foundation work, but are not yet
a clean, unambiguous end-to-end execution plan.

The findings below describe baseline `7c15aae`. The user subsequently requested fixes;
the [resolution](#resolution) records the changes. Infrastructure has not been applied.

## Findings

### P0 — Critical

(none)

### P1 — High

#### R4-01 [MISSING] Migrated content has no explicit service-access acceptance policy

- **Section:** implementation.md, tree-skeleton (lines 24–29), migration-runbook
  (lines 241–255, 273–279), and jellyfin-remount verification (lines 212–232).
- **Confidence:** 9/10 — preservation behavior and the limited scope of the ownership
  task are explicit; actual source permissions have not been inspected.
- **Problem:** The role creates named skeleton directories as `1000:1000`, but the
  migration preserves source permissions and ACLs inside copied trees. For example,
  a migrated directory owned by UID 2000 with mode 0700 remains inaccessible to an NFS
  client operating as UID 1000. Newly generated scratch files and an application
  import can pass every current access check while the preserved library is unreadable.
  The final migration audit checks preservation, not accessibility to the intended
  service identity.
- **Evidence:** `metal/roles/storage/tasks/nfs.yml:14` sets ownership only on entries
  in `storage_dirs`, without recursive normalization. The prescribed `rsync -aHAX`
  preserves permissions and ACLs, and ownership when run with the necessary privilege.
  See the official [rsync manual](https://download.samba.org/pub/rsync/rsync.1).
- **Recommendation:** Define per-tier access requirements for migrated served content
  and the service-side UID/GID used to test them. Verify traversal/read access on actual
  migrated media before freezing the accepted dataset; record any intended permission
  transformations in the ledger. Preserve archival metadata where restoration needs
  it, rather than recursively changing ownership of all backup trees. Add a restrictive
  source-permission fixture and a final read/playback check of migrated content.
- **When needed:** Before migration acceptance and the first production media rollout;
  it does not prevent implementing the empty skeleton.

### P2 — Medium

#### R4-02 [INCOMPLETE] The audit procedure is specified as requirements but has no owned implementation step

- **Section:** implementation.md, migration-runbook (lines 241–281); tasks.md, Tasks 6–7.
- **Confidence:** 8/10 — a manual runbook is valid, but these particular guarantees
  require a concrete, reproducible audit mechanism.
- **Problem:** The plan now requires complete object inventories, escaped filenames,
  a per-entry JSONL disposition ledger, final checksum reconciliation, and fixture
  tests covering collisions and failed hashes. Tasks 6–7 remain manual operations and
  refer to the eventual commands/helper without identifying where it is prepared,
  what invokes it, or who completes that preparation before scanning real sources.
  The existing repo has no migration-audit helper to reuse. This leaves material
  implementation work inside the operational migration step.
- **Recommendation:** Add a bounded prerequisite for the audit commands or a small
  helper: name its location, supported entry types, inputs/outputs, failure exit
  behavior, and partial-run/retry handling. Run the already-listed fixtures before
  Task 6 begins. Keep this scoped to inventory and verification; human curation can
  remain manual.
- **When needed:** Before copying/scanning the real sources under Task 6.

#### R4-03 [INCONSISTENT] Task 7 consumes exclusion rules without depending on Task 2

- **Section:** tasks.md:94–105; implementation.md:282–285.
- **Confidence:** 10/10 — the declared graph and the acceptance requirement disagree.
- **Problem:** Task 7.4 must check retained content against the rendered SnapRAID
  exclusions. Those corrected/rendered rules are Task 2's output, yet Task 7 depends
  only on Task 6 and explicitly permits parallel work with Task 2. The graph's
  ancestors for Task 7 are `{1, 3, 6, 11}`; Task 2 is absent.
- **Recommendation:** Add Task 2 as a prerequisite of Task 7, or move the exclusion
  acceptance check to the start of Task 8, which already depends on Task 2. Update
  the dependency graph and parallel markers to match the chosen boundary.
- **When needed:** Before following the migration task order. This is a semantic
  dependency defect; an acyclic graph and symmetric parallel markers do not detect it.

#### R4-04 [AMBIGUOUS] Task completion mixes preparation with later live acceptance

- **Section:** tasks.md:53–80, 134–145; implementation.md:79–112, 165–173.
- **Confidence:** 9/10 — the Task 4/5 completion conflict is direct; Task 11's intended
  fixture scope is inferable but inconsistent with its wording.
- **Problem:** Task 4 requires a completed ArgoCD sync as its acceptance check. Task 5
  depends on Task 4, while the plan requires both changes to land in one commit/sync
  window. A task-by-task implementer cannot both finish Task 4 first and postpone its
  sync until Task 5 is prepared. Separately, the early Task 11 fixture is described as
  using `99_tmp`, but its promotion check names the production media mount and requires
  the remaining link to keep seeding; the actual media stack arrives only in Task 5.
- **Recommendation:** Give Tasks 4/5 one deployment/acceptance boundary, either as a
  single vertical task or with Task 4 accepted by offline rendering and joint live
  acceptance owned by Task 5. Make Task 11 explicitly synthetic NFS validation;
  keep real application seeding/promotion acceptance in Task 5, or specify a fully
  independent disposable torrent fixture for Task 11.
- **When needed:** Before completing Task 11 or executing Tasks 4/5. This does not
  invalidate the single-mount architecture.

#### R4-05 [INCONSISTENT] The frozen-pool rule still conflicts with a runbook write destination

- **Section:** implementation.md:282–302, 324–329.
- **Confidence:** 10/10 — both conflicting instructions are explicit.
- **Problem:** Migration step 6 freezes included paths and requires parity-time
  evidence outside the pool. The subsequent parity-size gate says to record the
  numbers in `00_meta/migration/`, an included path, before every wipe. Repeating that
  instruction for C occurs after first-parity verification. Updating an existing
  record changes the verified snapshot; even creating a new record violates the
  documented freeze and needs separate coverage/accounting.
- **Recommendation:** Direct every Task 8 evidence write to the same independent
  evidence workspace/NAS journal until release is complete, then archive it to
  `00_meta`. Clarify that original source dataset entries remain frozen while the
  separately recorded safety-copy area may receive new files.
- **When needed:** Before Task 8. The intended safety rule is sound; the command-level
  destinations need to follow it consistently.

### P3 — Low

#### R4-06 [STRUCTURE] A short consistency/editing pass is still warranted

- **Section:** design.md:128–130, Reliability posture; decision_records.md:245.
- **Confidence:** 10/10 for the textual defects; these are not architecture blockers.
- **Evidence:** The hardlink paragraph contains the broken construction “which the
  single-PV topology avoids that particular failure.” AD-0006 says machine-generated
  churn never reaches the SnapRAID pool, although `rotation` lives on that pool and is
  parity-excluded. The reliability introduction declares rollout strategy N/A because
  no pods are added, while the same section describes replacing the pod. Existing-pod
  replacement still has a rollout policy, even if inherited.
- **Recommendation:** Narrow the statements: one mount avoids the identified EXDEV
  failure; excluded churn does not enter parity calculations; the workload inherits
  its current rollout policy. Keep invariants in design.md, operational details in
  implementation.md, and task checkboxes linked to their acceptance criteria rather
  than repeating long procedures in several places.
- **When needed:** Before calling the docs editorially clean; independent coding need
  not wait for this polish.

## Clean Areas

- The taxonomy, two-tier content model, scoped mounts, and one mount per linking
  container still agree across the design, plan and tasks.
- The original parity-size, UID, bind-mount, parity-numbering, full-sync/full-scrub,
  per-file redundancy, and complete-reconciliation corrections remain explicit.
- Assumptions, exclusions, trade-offs, failure handling, task sizes and pending status
  are present. Future Immich/documents deployment and monitoring are clearly scoped.
- Task IDs are stable and the broad graph is readable. Appending prerequisite Tasks
  11/12 rather than renumbering history is acceptable; a short execution-order outline
  would make the file easier to scan.
- `root_squash` compatibility and NFS lifecycle behavior are correctly treated as
  implementation-time acceptance gates. Lack of a live proof today is not itself
  another design finding.
- Existing review records identify their baseline and resolutions. Their historical
  findings are not counted again as open defects.

## Readiness and Verification

Foundation work on Tasks 1–3 can begin. Resolve the audit/access requirements before
the operational migration, make the Task 11 and Task 4/5 acceptance boundaries clear,
and correct the freeze/evidence destinations before parity release. No wholesale
architecture redesign is indicated.

All scoped documents and historical reviews were re-read, with current role/chart
references checked where needed. The strict MkDocs build passes. The declared task
graph is acyclic and its parallel markers are consistent; the additional semantic
dependency check exposes R4-03. Those mechanical checks establish syntax/link quality,
not end-to-end execution readiness. No live NAS/cluster tests were run.

The corrections below complete the focused planning pass. The remaining work is the
explicit pending implementation and runtime acceptance, beginning with the foundations.

## Resolution

Revised on 2026-10-03 using kk:design. The original findings and baseline references
are retained above; this section describes their current disposition.

| Finding | Correction |
|---|---|
| R4-01 | Added the per-tier migrated-content access policy, a UID/GID-1000 probe on actual migrated media before the freeze, recorded metadata transformations that preserve archive requirements, and real migrated-library playback in Task 5. |
| R4-02 | Added Task 13 for `scripts/nas-migration-audit.py` and its tests, with inventory/compare/verify/access contracts, versioned JSONL, explicit exit codes and partial/retry behavior. Task 6 now depends on that tested prerequisite. |
| R4-03 | Task 7 explicitly depends on Task 2. Its exclusion check consumes finalized rules; the graph and parallel markers reflect that dependency. |
| R4-04 | Task 4 completes with offline rendering on a non-deployed branch. Task 5 owns the joint release, old-resource cleanup and all application acceptance after Task 8. Task 11 uses only synthetic `99_tmp/nfs-readiness` fixtures; no seeding client is required there. |
| R4-05 | Defined one authoritative controller evidence workspace outside the NAS pool and A/B/C. All Task 8 records go there, with NAS spool/journal as working copies. `00_meta` is updated only before the freeze or after release. Original source entries and separately tracked safety copies have distinct write rules. |
| R4-06 | Corrected the hardlink paragraph and rollout-policy wording, aligned AD-0006's churn statement, added an execution-order outline, and shortened task checkboxes to reference their authoritative procedures. |

The design and ADRs retain the invariants; the implementation plan owns command and
acceptance details; tasks name deliverables and dependencies. All thirteen feature
tasks remain pending: documenting the audit helper does not implement it, and declared
NFS/media checks do not constitute live validation.

### Validation of the resolution

- The strict MkDocs build passes; local file links, all thirteen pending task records,
  graph acyclicity and parallel-marker consistency pass. Semantic assertions cover
  Task 7 → Task 2, migration → audit tooling, and Task 5 → offline PV work plus parity
  acceptance. Whitespace checks pass.
- A focused PAL `gemini-3.1-pro-preview` review reported no material correctness,
  security or architecture defect in these corrections. Its two LOW comments were
  optional diagram clarity and Python-environment clarification.
- The compact diagram intentionally uses transitive paths; the redundant Task 2 →
  Task 8 edge remains explicit in Task 8's metadata and the diagram note. No dependency
  is omitted from the executable task metadata.
- Author verification confirmed `python3` in the existing dev shell imports unittest
  successfully. The stale pip launcher does not prevent this standard-library runner;
  its separate environment-repair follow-up remains documented. Task 13's future
  helper suite has not been run because that implementation is still pending.
- No deployment, migration, source-disk operation, or implementation-task completion
  is implied by these documentation checks.
