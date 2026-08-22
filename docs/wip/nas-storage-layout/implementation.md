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
   → verify: `ansible-playbook … --check --diff` shows only the new dirs; a second real
   run reports zero changes (idempotent).
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
- **replace** the existing `exclude downloads/` with nothing (superseded by the rotation
  entry) and review `exclude appdata/` the same way — both are name-anchored and would
  hit backup-dump content; keep `/tmp/` and the dot-file excludes as-is

Keep a one-line comment per exclude stating *why*.
→ verify: rendered `/etc/snapraid.conf` on the NAS contains the three lines;
`snapraid status` parses the config without error (parity may not exist yet — config
parse is the check, not sync).

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

→ verify (after ArgoCD sync, in order):
  a. `helm template apps/jellyfin` — every media mount resolves to the single
     `pvc-nfs-media` claim; Jellyfin's mounts carry `readOnly: true`; radarr/sonarr have
     exactly one media volumeMount each; PUID/PGID env present on all lscr containers.
  b. UID proof: `kubectl exec` into radarr — `id` shows the s6-dropped app user as
     1000:1000 (after PUID applies), and `touch /data/downloads/.writetest` succeeds.
  c. Hardlink proof: in radarr —
     `touch /data/downloads/complete/.linktest && ln /data/downloads/complete/.linktest
     /data/movies/.linktest && stat -c %h /data/movies/.linktest` prints `2`; clean up
     both names.
  d. RO proof: in the jellyfin container, `touch /media/movies/x` fails with EROFS.
  e. `./tests/metal.sh` still passes (NFS validation tasks).

## migration-runbook

Manual/operational — executed from the controller or NAS shell, not by ArgoCD. Record
everything under `/mnt/storage/00_meta/migration/`.

1. **Copy drive A** (attach to NAS or workstation):
   `rsync -aHAX --info=progress2 /mnt/driveA/ /mnt/storage/99_tmp/driveA/`.
   `-H` preserves any hardlinks in the source; no `--delete` ever during migration.
2. **Manifests** (hash-set method — see design.md § Migration plan for why not `rsync -c`):
   for each dataset run `find <root> -type f -print0 | xargs -0 b3sum > <name>.b3` —
   `nas-copy.b3` (generated **on the NAS** so terabytes are read locally, not over NFS),
   `driveB.b3`, `driveC.b3` (hash B/C wherever they are attached; can run in parallel
   with the NAS-side hashing). The NAS needs b3sum installed: one-off
   `apt install b3sum` (Debian; fall back to the static binary from the upstream BLAKE3
   releases if the package is unavailable) — a migration-only tool, deliberately NOT
   added to the storage role; record the install + version in
   `00_meta/migration/README`. Store all `.b3` files in `00_meta/migration/`.
3. **Hash-set diff:** hashes present in `driveB.b3`/`driveC.b3` but absent from
   `nas-copy.b3` (compare field 1 only, e.g. `comm -13` on sorted hash columns) → copy
   those files into `99_tmp/driveB_delta/` (preserving relative paths), regenerate
   `nas-copy.b3`, repeat until the diff is empty or every remaining line is a conscious
   discard recorded in `00_meta/migration/discarded.txt`.
4. **Sort:** `mv` content from `99_tmp` into numbered homes per design.md § Migration
   mapping. Append each move as `src → dst` to `00_meta/migration/moves.log`. Delete
   cruft (`.@__thumb`, `.streams`, `Thumbs.db`, superseded archive generations) and log
   deletions to `discarded.txt`.
5. **Exit check:** `find /mnt/storage/99_tmp -type f | wc -l` → 0, and spot-audit:
   sample N hashes from `nas-copy.b3` and derive each file's destination by applying the
   **longest-prefix-matching `moves.log` entry** to the manifest path (moves are logged
   at directory level; the longest matching `src` prefix rewrites to its `dst`), then
   `b3sum -c` the sampled hash against that destination path.

## parity-enablement

One drive at a time; **drive A last**.

0. **Parity-size gate (before ANY wipe):** snapraid requires each parity device to be at
   least as large as the largest data branch. All drives are same-model 18TB Seagates
   (owner-confirmed 2026-08-22), so this holds — still, compare `lsblk -b` byte sizes of
   the candidate parity drive vs every `/mnt/data*` device and record the numbers in
   `00_meta/migration/`. Abort the wipe if the candidate is smaller.
1. Wipe drive B (`make -C metal wipe` targets k8s nodes — for the NAS use manual
   `wipefs`/`blkdiscard` per the drive's disk-by-id), add its id under `parity_drives` in
   the sops inventory (`metal/inventory/metal.yml`), run the storage role
   (`make metal` limited to the storage host, or the role's play). The role formats,
   mounts `/mnt/parity1`, templates `snapraid.conf`, and (see
   `tasks/snapraid_initial_sync.yml`) runs the initial sync as a systemd unit.
   → verify: `snapraid status` shows the parity file; initial sync completes in the unit
   log (`journalctl -u snapraid-initial-sync`).
2. Repeat for drive C (`2-parity`). → verify: `snapraid status` healthy with 2 parity.
3. `snapraid scrub -p 100` (or the role's scrub unit) once. → verify: zero errors.
4. Only now wipe drive A; decide (and record in `00_meta/migration/`) whether it becomes
   a third parity, a data branch, or a cold spare.
5. Update `snapraid_maintenance` thresholds in role defaults only if the first weeks show
   false-positive aborts — do not pre-tune.

## legend-docs

1. Vault legend note (outside this repo, in the Obsidian vault's `000_Infra/001_Legend/`):
   a `cosmarchy_of_the_nas.md`-style note mirroring `00_meta/README.md` — tree, grammar
   rules, working-set test, "machines feed, humans promote". Manual step; the repo-side
   task is only to keep `00_meta/README.md` authoritative.
2. `docs/info/todo.md`: under "Storage Node / NFS Optimizations", add a line pointing to
   `docs/wip/nas-storage-layout/` as the layout source of truth (the "Future shares
   (Pictures, Documents, Music, Backups)" naming in the NFS-review follow-up is
   superseded by this design's names).
3. `docs/guides/how_to_for_media_management.md`: updated as part of
   [jellyfin-remount](#jellyfin-remount) step 4.
→ verify: `make docs` (mkdocs) builds without broken-link warnings.

## Deferred / follow-ups (explicit)

- **restic policy values** per tier — design names the tiers; concrete
  frequencies/retention are future work (`scripts/backup.py` / backup docs).
- **NFS health monitoring** — pre-existing todo.md item; becomes more urgent once media
  serving depends on the NAS. Not part of this feature.
- **`use_ino` cleanup** in `tasks/mergerfs.yml` mount options — legacy no-op on 2.41.x;
  remove opportunistically next time the role changes (needs remount to apply).
- **Immich & documents-service deployment** — their mount requirements are binding
  (design.md § Service integration); the deployments are separate features.
