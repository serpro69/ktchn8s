# Design Review: NAS Storage Directory Layout

> Reviewed: 2026-08-22 · Reviewer: /kk:review-design (standard mode)

**Scope:** design.md + implementation.md + tasks.md
**Overall assessment:** CONCERNS_FOUND
**Documents:**

- Design: `docs/wip/nas-storage-layout/design.md`
- Implementation: `docs/wip/nas-storage-layout/implementation.md`
- Tasks: `docs/wip/nas-storage-layout/tasks.md`

**Summary:** 8 findings: 0 critical, 2 high, 2 medium, 4 low

---

## Findings

### P0 - Critical

(none)

### P1 - High

- **[TECH_RISK]** Write-path UID model is unresolved: `root_squash` is not `all_squash`, and the writers are linuxserver images with no PUID/PGID
  - **Section:** design.md § Security posture; implementation.md § jellyfin-remount
  - **Confidence:** 7/10 — export options and chart contents verified in-repo; the s6/fsGroup interaction is well-known linuxserver behavior but not tested here
  - **Description:** design.md claims "every write from the cluster lands as `1000:1000`". The actual export (`metal/roles/storage/defaults/main.yml:6`) is `root_squash` — only uid 0 is remapped to `anonuid=1000`. Non-root container UIDs pass through unchanged. The three writers in the new mount matrix (transmission, radarr, sonarr) are all `lscr.io/linuxserver` images, which drop to their internal `abc` user (default uid 911) via s6 — and s6's privilege drop discards pod-level `fsGroup` supplemental groups, so the chart's `fsGroup: 1000` does not grant group-write on `1000:1000/0775` dirs. As specified, writes and the hardlink verify step will likely fail with EACCES. Assumption 5 acknowledges the question ("verify per chart at mount time") but the jellyfin-remount plan — the chart being remounted *now* — contains no alignment step.
  - **Evidence:** `default_nfs_options: "rw,sync,no_subtree_check,root_squash,insecure"`; `apps/jellyfin/values.yaml` sets no `PUID`/`PGID` env on any lscr container.
  - **Recommendation:** Add `PUID=1000`/`PGID=1000` env to transmission/radarr/sonarr (and prowlarr for config-volume consistency) as an explicit jellyfin-remount step; correct the security-posture sentence to "root writes are squashed to 1000; non-root containers must run as 1000 via PUID/PGID".

- **[MISSING]** Parity-drive size precondition (parity ≥ largest data branch) is never stated or checked before drives are wiped
  - **Section:** design.md § Migration plan step 7; implementation.md § parity-enablement; tasks.md Task 8
  - **Confidence:** 7/10 — the snapraid constraint is certain; whether B/C actually violate it is unknown from the docs (which is the finding)
  - **Description:** snapraid requires each parity device to be at least as large as the largest data disk. The plan wipes drive B, adds it to `parity_drives`, and only then runs the initial sync. Neither the drive sizes nor a size-check precondition appear anywhere. If B (or C) is smaller than the largest data branch, the wipe destroyed a verified backup copy for nothing and the drive-release end state (success criterion 1) is unreachable.
  - **Evidence:** implementation.md parity-enablement step 1 goes straight from "Wipe drive B" to running the role; the Assumptions section covers drive *readability* (assumption 7) but not size.
  - **Recommendation:** Record the actual sizes of drives A/B/C and the data branches in the design (or `00_meta/migration/`); add an explicit "verify candidate parity device ≥ largest data branch" gate before the wipe step in the runbook and tasks.md 8.1.

### P2 - Medium

- **[INCONSISTENT]** `20.02_camera` contradicts grammar rule 2 and the parity-threshold rationale
  - **Section:** design.md § Grammar rules 2 & 6; § Parity & backup policy
  - **Confidence:** 7/10 — the textual contradiction is direct; operational impact depends on culling volume
  - **Description:** Rule 2: numbered = human-curated, unnumbered = machine-owned and parity-excluded ("one glance tells you who owns a dir"). Rule 6 lists `20.02_camera` as a *machine tier* (Immich RW; UI culling deletes files from disk). It is numbered, therefore parity-included — correctly so (dumps are the sole copy pre-promotion), but the parity section's claim that "churn thresholds stay meaningful because machine churn is excluded" does not hold for this dir: a culling session deleting >40 files trips `delete_threshold: 40` and aborts the snapraid-runner sync.
  - **Evidence:** `snapraid_maintenance.delete_threshold: 40` in `metal/roles/storage/defaults/main.yml`; design rule 6 explicitly names `20.02_camera` a machine tier.
  - **Recommendation:** Acknowledge the exception in rule 2 (deliberate: triage tier is parity-protected because it holds sole copies) and note the operational interplay in the parity section: large culls may require a manual `snapraid sync` or one-off threshold override.

- **[INCOMPLETE]** Where `b3sum` runs for the NAS-side manifest is unspecified, and nothing installs it on the NAS
  - **Section:** implementation.md § devshell-b3sum, § migration-runbook step 2; tasks.md Task 3/6
  - **Confidence:** 8/10 — verified: flake devshell is workstation-side; the storage role installs no hashing tool
  - **Description:** The runbook says `nas-copy.b3` is generated "on the NAS", but Task 3 only adds `b3sum` to the workstation dev shell. The NAS (Fedora, provisioned by the storage role) has no b3sum. The fallback — hashing the NAS copy from the workstation over NFS — re-reads terabytes over the network, contradicting the design's stated rationale for manifests ("reads each dataset once"). Task 6's dependency on Task 3 implies workstation execution, deepening the ambiguity.
  - **Recommendation:** Decide and document: either install `b3sum` on the NAS (one-off `dnf install b3sum`, recorded in the runbook, or via the storage role) or explicitly accept over-NFS hashing with its cost. Update Task 6 dependencies accordingly.

### P3 - Low

- **[INCONSISTENT]** Design's Jellyfin write matrix omits the `/media/music` → `30.03_music` mount that implementation.md adds
  - **Section:** design.md § Service integration vs implementation.md § jellyfin-remount step 2
  - **Confidence:** 8/10
  - **Description:** The design's matrix is presented as exhaustive but lists only movies/shows/rotation; implementation adds music. Harmless superset, but the matrix is the reviewable contract.
  - **Recommendation:** Add music (and note audiobooks are intentionally unmounted for now) to the design matrix.

- **[STRUCTURE]** Asymmetric `Can run in parallel with:` markers
  - **Section:** tasks.md Tasks 4, 5, 7, 9
  - **Confidence:** 9/10
  - **Description:** Task 7 lists Task 5, but Task 5 lists only Task 6; Task 9 lists Tasks 4–7, none of which reciprocate. The dependency graph is consistent; only the markers drift.
  - **Recommendation:** Make parallel markers symmetric.

- **[AMBIGUOUS]** Exit-audit re-rooting procedure is under-specified
  - **Section:** implementation.md § migration-runbook step 5; tasks.md 7.3
  - **Confidence:** 6/10
  - **Description:** `moves.log` records directory-level `src → dst` moves, but the sampled `b3sum -c` audit needs per-file destination paths. The mapping from manifest paths through dir-level moves is left to operator improvisation mid-runbook.
  - **Recommendation:** One sentence fixes it: e.g. "for each sampled hash, derive the destination by applying the longest-prefix-matching moves.log entry to the manifest path".

- **[MISSING]** Intermediate ArgoCD state between Task 4 and Task 5 syncs
  - **Section:** tasks.md Tasks 4–5; implementation.md § nfs-media-share
  - **Confidence:** 6/10 — low impact given the stack has never run
  - **Description:** If Task 4's commit syncs alone, `pv-nfs-videos` is deleted while the still-deployed jellyfin chart claims it via `pvc-nfs-videos` — the app degrades until Task 5 lands. Self-healing, but unmentioned.
  - **Recommendation:** Note in tasks.md that Tasks 4 and 5 should land in one commit/sync window (or accept the transient degradation).

---

## Clean Areas

- **Codebase cross-references: exceptional.** Every checked path, line number, and quoted value is accurate: `storage_dirs` contents, `tasks/nfs.yml:21` loop (current mode 0755 → 0775 change correctly identified), mergerfs include at `tasks/main.yml:48`, `nfs_anon_uid/gid=1000`, snapraid excludes (`downloads/`, `appdata/`, `/tmp/`), thresholds 40/500, `fsid=1`/`no_subtree_check` root export, csi-driver-nfs `videos/Videos/1Ti` entry and 4.13.0 pin, `pv-nfs-<name>` template derivation, Retain policy, `pvc-nfs-videos` binding pattern, jellyfin `anothervideos` block and `data`-PVC media subPaths, `Temp` references in `k8s_validation.yml:63`/`nfs_validation.yml:71` (anticipated by the docs), `snapraid_initial_sync.yml`, `parity_drives: []` in the sops inventory (correctly mapped to `parity_devices` via `facts.yml`), todo.md sections, and the media guide's `/movies`//`/shows` root folders.
- **Single-PVC hardlink topology** — sound and verified (subPath bind mounts share `st_dev`); EXDEV reasoning matches VFS semantics; matches `kk:arch-decisions` record.
- **Migration safety ordering** — "no source wiped until every later safety net exists," drive A last after first sync+scrub: internally consistent across all three docs.
- **snapraid exclude semantics** — name-anchored vs root-anchored usage is correct against the actual template; `exclude inbox/` cannot match `90_inbox` (exact component match).
- **Assumptions & Not Doing** — both present; assumptions are specific and falsifiable (with the P1 size gap noted above); Not Doing items are genuine scope exclusions with rationale, none hides a blocking requirement.
- **Task format** — sizes on all tasks (no unbroken L), Not Doing in header, dependency graph present and consistent with per-task `Depends on`, vertical slicing sound.
- **Failure-mode narrative** — impact/detection/recovery/owner per mode; accepted risks explicit.
- **Rejected alternatives** — each carries a concrete, verifiable reason.

---

# Design Review 2: NAS Storage Directory Layout

Scope: design + implementation + tasks
Overall assessment: MAJOR_GAPS (one P0; otherwise a high-quality design)
Documents:

- Design: docs/wip/nas-storage-layout/design.md
- Implementation: docs/wip/nas-storage-layout/implementation.md
- Tasks: docs/wip/nas-storage-layout/tasks.md

Summary: 5 findings: 1 critical, 0 high, 1 medium, 3 low
(capy tools unavailable this session — prior-context search and finding indexing skipped per protocol)

---

## Findings

### P0 - Critical

- [TECH_RISK] Separate subPath mounts of a single PVC still fail hardlink/rename with EXDEV — the core import mechanism won't work as designed
  - Section: design.md § Service integration (mount topology principle), § Two-tier media; implementation.md § jellyfin-remount step 2; tasks 5.2
  - Confidence: 9/10 — verified empirically on this machine, not just from docs
  - Description: The design assumes hardlinks work because subPaths of one PVC share one st_dev. But the kernel's EXDEV check in link(2)/rename(2) compares vfsmounts, not devices — and Kubernetes implements each subPath as a distinct bind mount. Radarr with /downloads (subPath downloads) and /movies (subPath rotation/movies) gets EXDEV on every import; the *arrs then silently fall back to copy — exactly the 2× degradation the single-PV design claims to prevent. I reproduced it: two bind mounts of the same fs, identical st_dev (66306), ln fails with "Invalid cross-device link". "Verified claims" row 2 is therefore wrong in its implication, and the rejected alternative "Downloads under 90_inbox" was rejected partly on reasoning that also applies to the chosen design.
  - Evidence: Your own verify step (impl § jellyfin-remount verify b, task 5.5 hardlink proof) would fail-loud at deploy — the check is well-designed; the topology isn't.
  - Recommendation: Containers that link across paths need those paths under one mount. Naively mounting the whole 30_media RW in the *arrs would destroy the "automation physically cannot touch 30.0x" safety boundary — instead, restructure the machine tier under one parent, e.g. 30_media/rotation/{downloads,movies,shows}, mounted once (subPath rotation → /data) in transmission/radarr/sonarr. Paths stay identical across containers (/data/downloads/...), Jellyfin's RO subPath mounts are unaffected (it never links), and exclude rotation/ then covers downloads too. Fix before Task 1 — the never-rename rule makes this maximally painful after the tree exists.

### P1 - High

(none)

### P2 - Medium

- [TECH_RISK] Name-anchored snapraid excludes (downloads/, rotation/, inbox/) match at any depth — including inside 70_backups dumps
  - Section: design.md § Parity & backup policy; implementation.md § snapraid-excludes
  - Confidence: 7/10 — case-sensitivity (Downloads vs downloads) and zip-heavy content lower the odds, but the failure is silent in the tier meant to be most protected
  - Description: Machine-backup dumps (home dirs, mobile dumps, extracted archives) can contain directories named downloads/inbox, which would be silently parity-excluded.
  - Recommendation: Root-anchor the machine-dir excludes (/30_media/rotation/, /10_documents/inbox/) — mergerfs branches mirror tree paths, so disk-root anchoring works and costs nothing under the new tree.

### P3 - Low

- [AMBIGUOUS] Grammar rules 1 and 2 contradict literally at depth ≥3: rule 1 mandates plain names deeper down, rule 2 says "unnumbered = machine-owned, parity-excluded" — so 10.01_personal/ids/ reads as machine-owned. Scope rule 2 to the two numbered levels; the generated README legend inherits this wording. (Confidence 8/10)
- [INCONSISTENT] Design's write matrix omits Jellyfin's /media/music → 30.03_music mount that implementation.md § jellyfin-remount includes; 30.04_audiobooks is mounted nowhere. Align the matrix. (Confidence 7/10)
- [STRUCTURE] Parallel markers asymmetric: Task 7 claims parallel with Task 5 but not vice versa; Task 9 lists 4/5/6/7, none reciprocate. (Confidence 9/10)

---

## Clean Areas

- Every codebase cross-reference checked out: storage_dirs, nfs.yml loop + nfs_anon_uid/gid, snapraid template excludes/thresholds, csi-driver-nfs values + PV naming, pvc-videos.yaml, flake.nix packages, mergerfs use_ino/mfs, parity_drives → parity_devices derivation, inventory, snapraid-initial-sync unit name, todo.md items, media-guide paths, Temp references in both validation files (impl anticipated them).
- Migration ordering ("no wipe until later safety nets exist"), assumptions (specific, falsifiable), Not Doing (genuine scope cuts), task format (sizes, deps, graph consistent), and the verification steps (idempotency, helm template, EROFS/hardlink proofs) are all solid.

---

# Resolution (2026-08-22)

Every finding was independently corroborated against the repo, an empirical kernel test, and upstream sources before fixing. All findings were confirmed VALID and addressed in the same session; drive sizes (the R1-P1 open question) were owner-confirmed as uniform 18TB Seagates.

**Contradiction arbitration:** Review 2's P0 defeats Review 1's clean-area claim ("subPath bind mounts share st_dev → sound"). Empirical reproduction: two bind mounts of one filesystem show identical `st_dev` (66306) yet `ln` fails with `EXDEV`; a single parent mount succeeds. The kernel compares vfsmounts, not devices. R1's premise was true, its conclusion false.

| Finding | Resolution |
|---|---|
| R2-P0 subPath EXDEV | Machine tier restructured: `30_media/rotation/{downloads,movies,shows}`; one volumeMount per linking container (radarr/sonarr `/data`→`rotation`, transmission `/data/downloads`→`rotation/downloads`). design.md (tree, topology principle, write matrix, verified-claims row 2, failure mode 3), implementation.md § jellyfin-remount, tasks 1.1/5.2/5.6, AD-0004 amended. |
| R1-P1 UID model | PUID/PGID=1000 on all lscr containers (no `runAsUser`); security-posture sentence corrected (root_squash remaps only uid 0; fsGroup inert on NFS). design.md, implementation.md § jellyfin-remount step 3, task 5.3, assumption 5 rewritten. |
| R1-P1 parity size | Precondition documented + `lsblk -b` gate before any wipe (impl § parity-enablement step 0, task 8.1, migration step 7, assumption 7). All drives 18TB — gate holds trivially. |
| R1-P2 camera exception | Rule 2 scoped to numbered levels with explicit `20.02_camera` exception; parity section notes the >40-file cull / `delete_threshold` interplay. |
| R1-P2 b3sum on NAS | Decided: one-off `apt install b3sum` on the NAS (recorded in `00_meta/migration/README`), deliberately not in the storage role. impl § migration-runbook step 2, task 6.2. |
| R2-P2 deep-matching excludes | All machine-dir excludes root-anchored (`/30_media/rotation/`, `/10_documents/inbox/`, `/99_tmp/`); pre-existing name-anchored `downloads/` removed, `appdata/` flagged for the same review. |
| R2-P3 rules 1v2 contradiction | Rule 2 scoped to the two numbered levels; deeper dirs inherit ancestor's tier. |
| R1-P3/R2-P3 matrix drift | Design write matrix now includes `/media/music`; `30.04_audiobooks` documented as intentionally unmounted. |
| R1-P3/R2-P3 parallel markers | Recomputed exhaustively from dependency edges; all markers now symmetric. |
| R1-P3 audit re-rooting | Longest-prefix-matching `moves.log` rule documented (impl step 5, task 7.3). |
| R1-P3 Task 4/5 sync gap | One-commit/sync-window note added to Task 4 and impl § nfs-media-share. |
