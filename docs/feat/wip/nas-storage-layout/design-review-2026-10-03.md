# Design Review: NAS Storage Directory Layout

Reviewed: 2026-10-03 · Mode: kk:review-design, standard · Repository: `bc3a816`

**Scope:** design.md + implementation.md + tasks.md

**Overall assessment before corrections:** MAJOR_GAPS

**Current disposition:** all nine findings corroborated and addressed in the planning
documents; infrastructure implementation and live acceptance remain pending.

**Documents:**

- [Design](./design.md)
- [Implementation](./implementation.md)
- [Tasks](./tasks.md)

**Summary:** 9 findings: 0 critical, 5 high, 3 medium, 1 low.

The directory taxonomy and corrected container mount topology are coherent. The migration and parity-release procedure needs revision before execution: its safety guarantees do not follow from its checks, and it assumes capabilities the existing storage role does not provide.

The findings below describe the pre-revision baseline. They were subsequently corroborated and **addressed in the design, implementation plan, tasks and ADRs** at the user's request; see [Corroboration and resolution](#corroboration-and-resolution). Infrastructure implementation and live acceptance remain pending. The August review and its resolution record remain historical context.

## Findings

### P0 - Critical

(none)

### P1 - High

#### R3-01 [TECH_RISK] Keeping drive A does not protect unique content from drive B during the first parity build

- **Section:** design.md:249, 267–291; implementation.md:161–165, 185–193; tasks.md:105.
- **Confidence:** 10/10 — the plan explicitly permits content unique to B/C and wipes B before any parity exists.
- **Description:** A file present only on B is copied to the NAS as a delta. Wiping B leaves that file with one copy until the first sync completes. A data-disk failure in that interval destroys it; keeping A and C does not help. The assertion that a migration-time disk loss is recoverable by re-copying from a source is therefore false for an explicitly supported input.
- **Evidence:** Manifest comparison copies B/C-only hashes to the NAS. No step copies them to another surviving source before the corresponding source is wiped. The existing AD-0007 guarantees a surviving source drive, not a surviving copy of each retained file.
- **Recommendation:** Before every wipe, prove that each retained file from that drive exists on another independent surviving device, or is already covered by completed, verified parity. For the first parity drive, copy and verify its unique delta onto A/C or temporary independent storage, with a capacity gate. Make this a Task 8 precondition and amend the failure narrative and AD-0007.

#### R3-02 [INCONSISTENT] The implementation replaces complete migration accounting with a sample

- **Section:** design.md:273–285; implementation.md:149–174; tasks.md:83–97.
- **Confidence:** 9/10 — the design requires every manifest entry accounted for, while the executable exit check checks only sampled hashes.
- **Description:** Different backup generations can contain different files that map to the same final pathname. Ordinary `mv` can overwrite the earlier file; an empty staging directory and a sampled audit can still pass. Once the sources are wiped, parity preserves the surviving result rather than recovering the overwritten version. Hash-set comparison before sorting does not close this gap. Drive A also has no independent source manifest in the implementation's dataset list.
- **Evidence:** Step 4 specifies `mv` and a move log without a collision policy. Step 5 checks regular-file count zero and samples N hashes. There is no exhaustive reconciliation of retained source entries against final destinations and explicit discards.
- **Recommendation:** Specify collision handling that stops before overwriting differing content. Record source identity, destination, and explicit deduplication/discard decisions; generate an A source manifest as well as B/C manifests. Require complete final reconciliation and checksum verification of retained content before any source release. Define handling of symlinks and other entries excluded by `find -type f`, and abort on copy/hash/read errors.

#### R3-03 [INCOMPLETE] The existing role cannot perform the documented second-parity transition

- **Section:** implementation.md:185–193; tasks.md:105–106.
- **Confidence:** 10/10 — the two-drive template was rendered locally, and the sync guard was inspected directly.
- **Description:** Adding C and rerunning the role does not provide the promised second parity. The current template renders `1-parity /mnt/parity2/snapraid.1-parity` after `parity`: `1-parity` aliases the first level, so this repeats that level instead of defining `2-parity`. Independently, the initial-sync task skips whenever the first parity file exists, so correcting the directive alone still does not initialize the new level.
- **Evidence:** `metal/roles/storage/templates/snapraid.conf.j2:10` uses `loop.index - 1`; `tasks/snapraid_initial_sync.yml:27–56` checks only the first parity file. Neither prerequisite correction is assigned a task. Additional levels are documented in the [SnapRAID manual](https://www.snapraid.it/manual#configuration); the alias is explicit in upstream [lev_config_scan](https://github.com/amadvance/snapraid/blob/master/cmdline/state.c).
- **Recommendation:** Add prerequisite work for correct parity numbering and an explicit, completion-checked parity-expansion operation. Validate rendered configurations for one, two, and three parity drives before wiping anything. Test the transition from an existing first parity to a newly configured second level, not just fresh initialization. These are pre-existing defects that this runbook relies on resolving.

#### R3-04 [TECH_RISK] The last-drive release gate can accept incomplete parity verification

- **Section:** implementation.md:190–196; tasks.md:105–108.
- **Confidence:** 10/10 — the permitted scrub alternative and failure reporting differ directly from the stated gate.
- **Description:** The runbook permits the role's scrub unit as an alternative to a full scrub, but that unit requests only 10% with a ten-day age filter. It cannot establish full verification immediately after initialization. The initial-sync unit also pipes `snapraid sync` through `tee` without `pipefail`, allowing systemd success when SnapRAID fails. A parity file's existence is not evidence of completed initialization.
- **Evidence:** `templates/snapraid-scrub.service.j2:8` uses `scrub_percentage` and `scrub_older_than_days`, defaulting to 10/10. `templates/snapraid-initial-sync.service.j2:8` uses a pipeline whose status comes from `tee`. The [SnapRAID manual](https://www.snapraid.it/manual#scrub) distinguishes full coverage from percentage/age-filtered scrubbing.
- **Recommendation:** Require an explicit full, unfiltered scrub with verified coverage, zero errors, and a successful command exit before Task 8.4. Remove the maintenance-unit alternative unless overridden to equivalent full coverage. Ensure sync failures propagate to the service result, document recovery from interrupted initialization, and capture evidence for every configured parity level before releasing A.

#### R3-05 [TECH_RISK] The claimed NFS baseline omits documented mergerfs export prerequisites

- **Section:** design.md:177–178, 244–248, 372; implementation.md:92–142.
- **Confidence:** 9/10 — the role's options and pinned-version upstream guidance disagree; the live NAS configuration was not inspected.
- **Description:** The plan treats the existing export as sufficient and limits stale-handle recovery to mergerfs restarts. The role configures neither node retention nor `inodecalc=path-hash`. Mergerfs 2.41.1 documents those settings for NFS exports because retained NFS handles can outlive FUSE node state, and inode changes can disrupt clients. A short initial write/link test does not exercise this lifecycle. NAS-local promotion also needs consideration while NFS clients retain handles.
- **Evidence:** `metal/roles/storage/tasks/mergerfs.yml:9–12` specifies `allow_other,use_ino,cache.files=off,category.create=mfs` plus mount dependencies. The version-matched [mergerfs NFS guidance](https://trapexit.github.io/mergerfs/2.41.1/remote_filesystems/#nfs-exporting-mergerfs) describes additional prerequisites and export-permission constraints; its general notes caution about server-side changes bypassing NFS.
- **Recommendation:** Add a prerequisite to reconcile the export configuration with the pinned guidance, explicitly resolving the existing `root_squash` choice rather than silently relaxing it. Validate sustained reopen/link operations and the chosen promotion procedure with active clients. Treat this as integration readiness, distinct from the deferred health-monitoring feature.

### P2 - Medium

#### R3-06 [INCONSISTENT] Task 2's live acceptance check depends on the later parity-enablement task

- **Section:** implementation.md:62–64; tasks.md:23–32, 99–105.
- **Confidence:** 10/10 — the storage role skips the entire configuration include without parity drives.
- **Description:** Task 2 is independent and must finish before Task 8, yet it requires applying and inspecting `/etc/snapraid.conf` on the parity-less NAS. The role does not render that file until parity drives exist. This is not merely a missing parity file that `snapraid status` can tolerate.
- **Evidence:** `metal/roles/storage/tasks/main.yml:54–67` guards `snapraid.yml` with `parity_drives | length > 0`; the first drive is added in Task 8.1.
- **Recommendation:** Give Task 2 an offline render/config-validation check using representative parity inputs. Move its live configuration acceptance check into Task 8 after parity configuration, preserving the dependency on the exclude-rule change itself.

#### R3-07 [TECH_RISK] The UID proof tests an exec process rather than the application identity

- **Section:** implementation.md:135–139; tasks.md:71.
- **Confidence:** 9/10 — privilege dropping in a service launcher does not change the identity assigned to a new container exec process.
- **Description:** Bare `kubectl exec ... id` does not inherit the Radarr service's s6 privilege drop. In the root-started LinuxServer container it tests root; root-squashed NFS writes can succeed as anonymous UID 1000 even when the application still runs under the wrong UID. The proposed check therefore either fails its expected `id` assertion or gives a misleading successful write/link result.
- **Evidence:** The plan deliberately omits `runAsUser`. The [LinuxServer Radarr launcher](https://github.com/linuxserver/docker-radarr/blob/master/root/etc/s6-overlay/s6-rc.d/svc-radarr/run) drops the application to `abc`; it does not redefine arbitrary exec sessions.
- **Recommendation:** Inspect the actual service process credentials, and run the write/link proof explicitly as the configured application user, such as through the image's supported s6 user-switch helper. Include a real import as the end-to-end check.

#### R3-08 [INCOMPLETE] Several named validation commands cannot establish their advertised result

- **Section:** implementation.md:28–29, 142, 212; tasks.md:21, 71, 120, 129.
- **Confidence:** 10/10 — all three command contracts are directly contradicted by repository contents.
- **Description / evidence:** `tests/metal.sh` exercises cluster networking and nginx, not the storage role's NFS validation tasks. A whole-role second run cannot report zero changes because `tasks/main.yml:33–35` unconditionally marks `sensors-detect` changed. `make docs` runs `mkdocs serve` (`Makefile:166–167`), not a terminating documentation build.
- **Recommendation:** Name a storage-play invocation enabling `validate_nfs=true`, keep network checks separately identified, scope idempotency acceptance to the changed layout resources, and use `mkdocs build --strict` for a terminating documentation check. Explain any pre-existing warning baseline rather than treating it as this feature's regression.

### P3 - Low

#### R3-09 [STRUCTURE] The design's durable ADR link points to a nonexistent directory

- **Section:** design.md:4.
- **Confidence:** 10/10 — resolved locally and checked for existence.
- **Description / evidence:** `../../reference/architecture/decision_records.md` resolves to `docs/feat/reference/architecture/decision_records.md`. The actual file is under `docs/reference/architecture/`.
- **Recommendation:** Change the relative link to `../../../reference/architecture/decision_records.md` and include it in the documentation link check.

## Clean Areas

- The human-facing taxonomy, two-level numbering, working-set rule, and explicit exclusions support the stated owner/household use cases.
- Assumptions and Not Doing sections are present; tasks have size tags, parallel markers, dependencies, and a dependency graph. The execution dependency defect is specifically R3-06.
- The prior single-mount correction is consistently reflected in the tree, writer matrix, implementation, and tasks. Linking containers receive one `rotation` mount; read-only Jellyfin mounts remain scoped.
- Explicit PUID/PGID configuration, root-anchored machine-tier exclusions, the camera parity exception, and parity-device size checks carry forward the earlier review resolutions.
- Static PV/PVC naming, Retain policy, chart versions, repository file references other than the ADR link, and the proposed media/config split match the current repository.
- Future service deployment, backup schedules, and monitoring are explicitly deferred. The NFS integration prerequisite in R3-05 is required for the current consumer rather than a request to expand those features.

## Verification and Limits

- Read all three scoped documents, the existing review and resolutions, relevant ADRs, and the storage role, chart, test, and Makefile paths cited above.
- Searched `kk:arch-decisions` and `kk:review-findings`; prior knowledge corroborates the already-fixed bind-mount issue.
- Rendered the existing SnapRAID Jinja template in memory with two parity devices; confirmed it emits `parity` plus its `1-parity` alias instead of a second level. Checked the ADR link on disk and verified relevant upstream behavior against primary sources.
- Re-read findings against the full plan and existing resolutions; no earlier resolved finding is repeated as still open.
- No live NAS/cluster checks, migration, provisioning, or disk operations were performed. Findings concern the proposed procedure and repository baseline, not observed production failures.
- Commands ran inside `nix develop`. Its existing pip hook references the differently-cased `ktchn8S` path and failed; read/render checks still worked. Environment follow-up: repair/recreate the stale virtualenv before package-dependent validation. `TOOLBOX_PLUGIN_ROOT` was unset, so the session-provided Codex skill path was used.

## Next Steps

Implement the revised pending tasks and satisfy their acceptance gates before migration or parity-drive release. Documentation correction does not establish operational readiness.

## Corroboration and resolution

The user requested a second verification of every finding and fixes for confirmed
issues, with `kk:design` governing the edits. The initial answer is the nine findings
above; their original section/line references identify the reviewed baseline.

### Verification questions

1. For different source generations, what remains recoverable after each proposed
   wipe, and what can an empty staging tree plus a sample actually prove? (R3-01/02)
2. What do the pinned SnapRAID parser, current role, and unit exit/scrub policies do
   during first initialization, interruption, and adding a parity level? (R3-03/04)
3. Which mergerfs 2.41.1 export settings are documented, what identity do hardlinks
   expose with them, and what can be established without a live NAS? (R3-05)
4. When does the role render SnapRAID configuration, and whose identity does a new
   container exec process test? (R3-06/07)
5. What do the named validation commands actually run, and do both directions of the
   design/ADR links resolve? (R3-08/09)

### Evidence and disposition

| Finding | Corroboration / qualification | Resolution in revised documents |
|---|---|---|
| R3-01 | Confirmed by the counterexample `A={a}, B={b}, C={c}, NAS={a,b,c}`: after wiping B and before first parity, b has one copy. | Design migration/failure narrative, runbook release gates, Task 8, AD-0007 now require per-file recoverability and measured capacity for independent safety copies. |
| R3-02 | Confirmed: two different hashes can map to one final pathname; an overwrite empties staging while a sample can miss the loss. Rsync's transfer checks do not verify later sorting decisions. | A/B/C source inventory, collision stops, per-entry ledger, explicit dedup/discard decisions, and complete final verification in Tasks 6–7 and AD-0007. |
| R3-03 | Confirmed: in-memory rendering emits `parity` plus `1-parity`. The [v13.0 parser](https://github.com/amadvance/snapraid/blob/v13.0/cmdline/state.c) maps both to level zero and rejects a repeated level. The role independently skips on the first file's existence. | Task 2 corrects/tests one-to-three parity layouts; new Task 12 prepares an explicit full-sync lifecycle without a file-existence completion guard. |
| R3-04 | Confirmed: the unit uses `sync \| tee` without pipefail; a harmless `false \| cat` reproduction exits zero. The scrub template requests 10%/ten days. The [v13.0 manual](https://github.com/amadvance/snapraid/blob/v13.0/snapraid.1) distinguishes full sync/scrub operations. | Direct job exit propagation, operator-controlled retries, disabled competing maintenance and full coverage after each parity transition in Tasks 8/12. |
| R3-05 | Confirmed as a prerequisite gap, **not** proof of a live failure or permission to disable root squashing. The role omits the pinned export settings; [path-hash documentation](https://trapexit.github.io/mergerfs/2.41.1/config/inodecalc/) also clarifies that presented inode inequality does not disprove hardlinks. | Task 11 configures/validates lifecycle and UID-1000 operations; keep root_squash with an explicit rollout gate. Use scoped NFS operator promotion and finish local sorting before production rollout. ADRs 4–6 aligned. |
| R3-06 | Confirmed by `tasks/main.yml`'s parity-drive guard; no file is rendered before first parity configuration. | Task 2 accepts offline fixtures; Task 8 performs the live check after configuration. |
| R3-07 | Confirmed by the service launcher's per-process privilege drop and chart's absence of runAsUser; exec identity is not the application's. | Inspect service credentials, run probes through `s6-setuidgid abc`, and verify an actual application import in Task 5. |
| R3-08 | Confirmed by Makefile, test script and unconditional sensors-detect change. Existing `python3 -m mkdocs` is usable despite the stale pip launcher. | Layout-specific idempotency, an explicit NFS-enabled storage invocation, separately labelled network checks, and a strict terminating docs build. |
| R3-09 | Confirmed by filesystem resolution and a strict baseline build: both the design-to-ADR link and ADR-to-design backlink produce warnings. | Corrected both relative links. |

All nine survive verification with the R3-05 evidence limit above. The parity alias
wording is pinned-source verified, rather than treating `1-parity` as an unknown
keyword. No production code was changed or live storage operations performed during
this correction; prerequisite implementation is explicitly tracked in pending tasks.

### Review of the corrections

- **Independent review:** PAL `gemini-3.1-pro-preview` reviewed the diff, revised
  documents and relevant baseline role files. It found one **LOW** issue: the complete
  hardlink probe needed explicit quotes as the `sh -c` argument so every command runs
  under `s6-setuidgid abc`. The implementation plan now provides that quoted command.
  No high-severity correction issue was reported.
- **Reviewer availability:** the separate code-reviewer agent could not access the
  required Nix environment and reviewed no files. Its empty findings are not approval;
  the independent result above comes from PAL alone.
- **Author recheck:** production rollout now follows Task 8, so promotion acceptance
  cannot mutate included data during parity verification. Live evidence is written
  outside the pool during that freeze and archived afterward.
- **Validation:** the baseline strict MkDocs build failed on the design/ADR link pair;
  the revised build passes. Task references, graph acyclicity, and parallel-marker
  symmetry were checked programmatically; implementation tasks remain pending.
- No new systemic high-severity review finding needed indexing; the original risks
  and their resolutions are already recorded in this report and the revised ADRs.
