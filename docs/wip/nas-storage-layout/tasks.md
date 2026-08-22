# Tasks: NAS Storage Directory Layout

> Design: [./design.md](./design.md)
> Implementation: [./implementation.md](./implementation.md)
> Status: pending
> Created: 2026-08-22
> Not Doing: SMB shares, documents-service selection (Nextcloud/Copyparty/OpenCloud), Plex/second media service, automated photo promotion, vault reorganization, ZFS migration planning, Gitea code-archive extraction, restic policy values, NFS health monitoring

## Task 1: Tree skeleton via storage role
- **Status:** pending
- **Depends on:** —
- **Size:** M
- **Can run in parallel with:** Task 2, Task 3
- **Docs:** [implementation.md#tree-skeleton](./implementation.md#tree-skeleton)

### Subtasks
- [ ] 1.1 Replace `storage_dirs` in `metal/roles/storage/vars/main.yml` with the designed tree as a flat path list (top-level dirs, `NN.MM` subdirs, `30_media/rotation/{movies,shows}`, `30_media/rotation/downloads/{complete,incomplete}` — downloads nests INSIDE rotation, `10_documents/inbox`)
- [ ] 1.2 Ensure the `storage_dirs` loop in `tasks/nfs.yml` sets owner/group `1000:1000`, mode `0775`
- [ ] 1.3 Add `templates/storage-readme.j2` (legend: grammar rules, working-set test, machine-vs-human convention) rendered to `00_meta/README.md` from the same variable; create `00_meta/RETIRED.md` with `force: false`
- [ ] 1.4 Grep the role for references to old dirs (`Temp`, `Videos` in validation tasks) and repoint to `99_tmp`
- [ ] 1.5 Run the role against the NAS twice: first run creates, second run reports zero changes; manually remove empty legacy dirs (`Videos`, `Backups`, …) and verify `find /mnt/storage -maxdepth 1` shows only the new tree

## Task 2: snapraid exclude rules
- **Status:** pending
- **Depends on:** —
- **Size:** S
- **Can run in parallel with:** Task 1, Task 3, Task 4, Task 5, Task 6, Task 7, Task 9
- **Docs:** [implementation.md#snapraid-excludes](./implementation.md#snapraid-excludes)

### Subtasks
- [ ] 2.1 Add root-anchored `exclude /30_media/rotation/`, `exclude /10_documents/inbox/`, `exclude /99_tmp/` with why-comments to `metal/roles/storage/templates/snapraid.conf.j2`; remove the name-anchored `exclude downloads/` (superseded; deep-matches inside 70_backups dumps) and review `exclude appdata/` for the same hazard
- [ ] 2.2 Apply via the storage role; verify rendered `/etc/snapraid.conf` contains the lines and `snapraid status` parses the config

## Task 3: b3sum in the dev shell
- **Status:** pending
- **Depends on:** —
- **Size:** S
- **Can run in parallel with:** Task 1, Task 2, Task 4, Task 5, Task 9
- **Docs:** [implementation.md#devshell-b3sum](./implementation.md#devshell-b3sum)

### Subtasks
- [ ] 3.1 Add `b3sum` to `devShells.default` packages in `flake.nix`
- [ ] 3.2 Verify `nix develop -c b3sum --version`

## Task 4: NFS media PV (csi-driver-nfs)
- **Status:** pending
- **Depends on:** Task 1
- **Size:** S
- **Can run in parallel with:** Task 2, Task 3, Task 6, Task 7, Task 8, Task 9
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
- **Can run in parallel with:** Task 2, Task 3, Task 6, Task 7, Task 8, Task 9
- **Docs:** [implementation.md#jellyfin-remount](./implementation.md#jellyfin-remount)

### Subtasks
- [ ] 5.1 Rename `apps/jellyfin/templates/pvc-videos.yaml` → `pvc-media.yaml` binding `pvc-nfs-media` → `pv-nfs-media`
- [ ] 5.2 Rework `persistence` in `apps/jellyfin/values.yaml`: single NFS claim; **ONE volumeMount per linking container** (radarr `/data`→subPath `rotation`; sonarr `/data`→subPath `rotation`; transmission `/data/downloads`→subPath `rotation/downloads`; Jellyfin all-`readOnly` incl. `/media/music`→`30.03_music`); strip media subPaths from the Ceph `data` PVC (configs only)
- [ ] 5.3 Add `PUID: "1000"`/`PGID: "1000"` env to all lscr.io containers (transmission, radarr, sonarr, prowlarr); no `runAsUser` on them
- [ ] 5.4 Update transmission download-dir config to `/data/downloads/complete` + `/data/downloads/incomplete`; *arr root folders `/data/movies`, `/data/shows`
- [ ] 5.5 Update `docs/guides/how_to_for_media_management.md` (root folders, Jellyfin library paths for both tiers)
- [ ] 5.6 Verify: helm template shows single-claim mounts, exactly one media mount on radarr/sonarr, RO flags, PUID/PGID env; in-cluster UID proof (write to `/data/downloads` succeeds as 1000); hardlink proof (`ln` `/data/downloads/complete/…`→`/data/movies/…`, `stat -c %h` = 2); EROFS in Jellyfin's `/media/movies`; `./tests/metal.sh` passes

## Task 6: Migration — copy & cross-drive verification (manual ops)
- **Status:** pending
- **Depends on:** Task 1, Task 3
- **Size:** M
- **Can run in parallel with:** Task 2, Task 4, Task 5, Task 9
- **Docs:** [implementation.md#migration-runbook](./implementation.md#migration-runbook)

### Subtasks
- [ ] 6.1 rsync drive A → `99_tmp/driveA/` (`-aHAX`, no `--delete`)
- [ ] 6.2 Generate b3sum manifests: NAS copy (hash locally on the NAS — one-off `apt install b3sum`, recorded in `00_meta/migration/README`), drive B, drive C → `00_meta/migration/*.b3`
- [ ] 6.3 Hash-set diff; copy unique B/C content into `99_tmp/drive{B,C}_delta/`; iterate until diff empty or discards logged in `discarded.txt`

## Task 7: Migration — sort into numbered homes (manual ops)
- **Status:** pending
- **Depends on:** Task 6
- **Size:** M
- **Can run in parallel with:** Task 2, Task 4, Task 5, Task 9
- **Docs:** [implementation.md#migration-runbook](./implementation.md#migration-runbook)

### Subtasks
- [ ] 7.1 `mv` content from `99_tmp` per design.md § Migration mapping, appending to `00_meta/migration/moves.log`
- [ ] 7.2 Delete cruft (`.@__thumb`, `.streams`, `Thumbs.db`, superseded archives) → `discarded.txt`
- [ ] 7.3 Exit check: `99_tmp` empty; sampled `b3sum -c` audit — derive each sampled file's destination via the longest-prefix-matching `moves.log` entry applied to its manifest path

## Task 8: Parity enablement & drive release (manual ops)
- **Status:** pending
- **Depends on:** Task 2, Task 7
- **Size:** M
- **Can run in parallel with:** Task 4, Task 5, Task 9
- **Docs:** [implementation.md#parity-enablement](./implementation.md#parity-enablement)

### Subtasks
- [ ] 8.1 Parity-size gate: compare `lsblk -b` sizes of candidate parity drive vs every data branch (all 18TB Seagates, confirmed — abort wipe if candidate smaller); then wipe drive B, add to `parity_drives` in sops inventory, run storage role; initial sync completes (`journalctl -u snapraid-initial-sync`)
- [ ] 8.2 Repeat for drive C (2-parity); `snapraid status` healthy
- [ ] 8.3 Full scrub, zero errors
- [ ] 8.4 Wipe drive A last; record its new role (parity/data/cold spare) in `00_meta/migration/`

## Task 9: Legend & docs
- **Status:** pending
- **Depends on:** Task 1
- **Size:** S
- **Can run in parallel with:** Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8
- **Docs:** [implementation.md#legend-docs](./implementation.md#legend-docs)

### Subtasks
- [ ] 9.1 Write the vault legend note (manual, in Obsidian vault) mirroring `00_meta/README.md`
- [ ] 9.2 Point `docs/info/todo.md` storage section at `docs/wip/nas-storage-layout/` (supersedes "Future shares (Pictures, Documents, Music, Backups)" naming)
- [ ] 9.3 Verify `make docs` builds clean

## Task 10: Final verification
- **Status:** pending
- **Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8, Task 9
- **Size:** S
- **Can run in parallel with:** —

### Subtasks
- [ ] 10.1 Run `/kk:test` — role idempotency, `./tests/metal.sh`, in-cluster mount/hardlink/RO proofs
- [ ] 10.2 Run `/kk:document` — finalize docs, move feature out of wip when done
- [ ] 10.3 Run `/kk:review-code` — review the ansible/helm/nix changes
- [ ] 10.4 Run `/kk:review-spec` — verify implementation matches design/implementation docs

## Dependency Graph

```
Task 1 ─┬─→ Task 4 ─→ Task 5 ──────────┐
        ├─→ Task 6 ─→ Task 7 ─→ Task 8 ─┤
        └─→ Task 9 ─────────────────────┼─→ Task 10
Task 2 ─────────────────→ Task 8        │
Task 3 ─→ Task 6                        │
(Tasks 6–8 are manual/operational runbook executions)
```
