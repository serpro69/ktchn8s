# NAS Storage Directory Layout — Design

> Status: designed (2026-08-22, revised same day after design review — see [design-review.md](./design-review.md) § Resolution) · Implementation: [implementation.md](./implementation.md) · Tasks: [tasks.md](./tasks.md)
> Key decisions recorded as ADRs [AD-0003 … AD-0007](../../reference/architecture/decision_records.md) — the ADRs are the durable record; this doc carries the full working detail.

## Problem statement

**How might we design a NAS directory tree that the owner (and household members via
services) can navigate from memory years from now — where every service (Jellyfin/*arr,
Immich, a future documents service) mounts a scoped subtree — under the constraint that
a directory, once created, is never renamed** (snapraid parity, rsync-style backups, and
NFS-mounted PVs all punish renames)?

### Personas

- **Primary:** the owner, at the filesystem (ssh/rsync/mc on the NAS). The numbered tree
  exists for him-in-5-years to find things without a search index.
- **Secondary:** household members, exclusively through service UIs (Jellyfin/Jellyseerr,
  Immich). They never see directory names; their interface is libraries/albums.
- Automation (*arr stack, consume dirs) is **accommodated, not authoritative**: its layout
  requirements are honored where they are hard constraints (hardlinks, single mounts), but
  it does not reshape the human taxonomy.

### Success criteria

1. **Migration completes and drives are freed** — all backup-drive content has exactly one
   home, `99_tmp` is empty, source drives verified and released to parity duty.
2. **Zero renames, ever** — no numbered directory is ever renamed after creation;
   extension happens by adding numbers, never reshuffling.
3. **Service-scoped mounts only** — every PV points at a subtree, never the root; no
   service writes outside its assigned subtree.
4. **Findable from the legend alone** — any category is locatable by reading
   `00_meta/README.md` (or the vault legend note); no `find` archaeology.

## The tree

```
/mnt/storage/
├── 00_meta/          # README (the legend), RETIRED.md, migration manifests & logs
├── 10_documents/
│   ├── inbox/        #   machine-consumed drop dir (scanner / future paperless consume)
│   ├── 10.01_personal/   # ids, certificates, residence, education/diplomas
│   ├── 10.02_family/     # baby, household
│   ├── 10.03_finance/    # tax, banking, purchases & receipts
│   ├── 10.04_work/       # contracts, per-employer subdirs
│   └── 10.05_health/
├── 20_photos/
│   ├── 20.01_library/    # preserved archive, YYYY/ inside — Immich external lib, :ro
│   ├── 20.02_camera/     # triage tier: device dumps — Immich external lib, RW
│   └── 20.03_home_video/
├── 30_media/         # ONE NFS PV for the whole media stack
│   ├── 30.01_movies/     # preserved, human-curated ┐ *arrs have no root folder here;
│   ├── 30.02_tv/         #                          │ automation can never delete these
│   ├── 30.03_music/      #                          │
│   ├── 30.04_audiobooks/ #                          ┘
│   └── rotation/         # the ENTIRE machine tier under one parent (hardlinks need
│       ├── downloads/    #   one bind mount — see mount topology): transmission
│       ├── movies/       #   downloads/{complete,incomplete}; *arr root folders
│       └── shows/        #   movies/ shows/ (music/ books/ later)
├── 40_library/
│   ├── 40.01_books/      # by genre/language (Calibre/Kavita-compatible)
│   ├── 40.02_courses/    # video courses, trainings, language materials
│   └── 40.03_reference/  # manuals, standalone guides, journals
├── 50_topics/        # working-set collections only (see decision rule below)
│   ├── 50.01_dnd/
│   └── 50.02_airsoft/
├── 60_software/      # ISOs, installers, APKs, portable tools, flash-drive images
├── 70_backups/       # machine-generated, never hand-edited
│   ├── 70.01_machines/   # per-host system backups
│   ├── 70.02_apps/       # thunderbird, jetbrains, brave (archives + logs together)
│   ├── 70.03_mobile/     # phone dumps, TitaniumBackup, TWRP images
│   ├── 70.04_exports/    # aegis, keepass, bookmarks, session exports
│   └── 70.05_code/       # project-archive zips (live home is Gitea)
├── 80_vault/         # cryptomator containers — opaque, never decrypted server-side
├── 90_inbox/         # the human's inbox: unsorted incoming (parity-protected)
└── 99_tmp/           # staging/scratch — parity-excluded, restic-excluded
```

## Grammar rules (the invariants)

1. **Two-digit decade top level; `NN.MM_` second level; numbering stops at two levels.**
   Deeper directories use plain names. Two digits after the dot keep lexicographic sort
   correct up to 99 children everywhere (`ls`, NFS clients, web UIs) and match the vault's
   existing `.01` sub-level convention. The vault's three-digit top level encodes a third
   numbering level (`300/310/310.01`) which the NAS grammar deliberately does not have.
2. **At the two numbered levels: numbered = human-curated and parity-protected;
   unnumbered lowercase = machine-owned and parity-excluded.** One glance tells you who
   owns a dir and whether parity covers it. The rule applies only where numbering applies
   (direct children of the pool root and of numbered dirs) — deeper plain-named dirs
   (`10.01_personal/ids/`) simply inherit their ancestor's tier. (`90_inbox` is numbered —
   it is the *human's* inbox; `10_documents/inbox/` is unnumbered — machines feed and
   delete there.) One deliberate exception: `20.02_camera` is numbered and
   parity-protected yet machine-*fed* — camera dumps are the sole copy of those photos
   until promotion, so they must be under parity even though a service writes there.
3. **Numbers are never recycled; directories are never renamed.** Categories retire via an
   entry in `00_meta/RETIRED.md`; the number stays burned.
4. ASCII lowercase + underscores at numbered levels; leaf content keeps original names
   (release names, Cyrillic titles — fine).
5. **Service shares alias the numbers away** (`media` → `30_media`, `photos` → `20_photos`)
   so external names stay stable; a future SMB layer exports the same aliases with zero
   restructuring.
6. **Two-tier flow — machines feed, humans promote.** Machine tiers: `rotation/`
   (including its nested `downloads/`), `20.02_camera` (numbered/parity exception — see
   rule 2), Immich uploads (Ceph). Human promotion: `mv` into a numbered dir. Applies
   symmetrically to media and photos.

### The `50_topics` decision rule (working-set test)

A collection goes to `50_topics` only when splitting it by medium would destroy its value
as a *working set* — D&D (rulebooks + character sheets + tools + scenarios), airsoft
(manuals + scenario docs + photos). A file valuable on its own goes to the medium dir: a
yoga *book* → `40.01_books`, a guitar *course* → `40.02_courses`. `50.x` entries are rare
and deliberate — never "I have three files about X".

## Two-tier media & photos

**Media.** transmission writes `rotation/downloads/` → *arr imports via **hardlink** into
`rotation/movies|shows/` (both paths live under the *single* `rotation` mount in the *arr
containers → real link; seeding continues from the original name while the library copy
carries the clean name) → the owner promotes keepers with `mv` into `30.0x` (NAS-side,
same filesystem, instant). Radarr/Sonarr delete-and-replace files on quality upgrades, so
the rotation/preserved split is a **data-safety boundary**: automation physically cannot
touch `30.0x`.

Hardlinks consume storage **once** — two directory entries, one inode. The 2× case only
occurs when a hardlink silently degrades to a copy (cross-device), which the single-PV
design prevents. Monitoring signal: if `30_media` usage runs ~2× expected, hardlinking has
broken (`stat -c %h` on an imported file must be ≥2 while seeding).

Jellyfin serves both tiers (either as separate libraries or one merged library per type).
Known nuance: Jellyfin identifies items by path, so promotion (`mv`) typically resets
watch state for that item — promote what has been watched, or accept the reset.

**Photos.** Immich mounts `20.01_library` **read-only** (viewer/indexer; the filesystem
is the metadata source of truth — date/GPS repairs happen via exiftool/digiKam on the
tree, Immich picks them up on rescan) and `20.02_camera` **read-write** (triage: culling
in the Immich UI deletes rejects from disk *by intent*; metadata edits write real XMP
sidecars). Mobile uploads land in Immich-owned storage on Ceph. Keepers are promoted by
`mv` into `20.01_library`. Albums/people/favorites live only in Immich's DB in *both*
modes — the DB needs backing up regardless, so RW-everywhere would not have bought
portability, only deletion risk.

## Service integration

**Mount topology principle:** one PV per exposed subtree; any container that must
hardlink or rename across paths must see both paths under **one single volumeMount** —
not merely one PVC. The kernel's `EXDEV` check in `link(2)`/`rename(2)` compares
*vfsmounts*, not devices: every k8s volumeMount (including each `subPath`) is a distinct
bind mount, so two subPath mounts of the *same* PVC still fail with `EXDEV` even though
`st_dev` is identical (empirically verified 2026-08-22: cross-bind-mount `ln` fails,
same-parent-mount `ln` succeeds). This is why the entire machine tier nests under
`rotation/` — one subPath mount of `rotation` gives a linking container downloads and
library roots inside a single vfsmount.

- **`system/csi-driver-nfs`:** the `videos` volume entry is replaced by `media` → share
  `30_media`, PV `pv-nfs-media`. The old `pv-nfs-videos`/PVC pair is deleted, not migrated
  (the K8s NFS stack has never run; the NAS is empty). Future shares are one values entry
  each: `photos` → `20_photos`, `documents` → `10_documents`, added with their consumers.
- **Jellyfin chart (`apps/jellyfin`):** the 50Gi Ceph `data` PVC keeps *configs only* —
  media on triple-replicated NVMe is capacity-wrong (one 4K remux ≈ its size). All media
  paths become subPaths of the NFS PVC. Write matrix (one volumeMount per writer):
  - transmission → subPath `rotation/downloads` mounted at `/data/downloads` (rw; sees
    only downloads — least privilege; it never links).
  - Radarr → subPath `rotation` mounted at `/data` (rw; root folder `/data/movies`;
    downloads at `/data/downloads` — links happen inside this one mount).
  - Sonarr → subPath `rotation` mounted at `/data` (rw; root folder `/data/shows`).
  - Jellyfin → **everything `:ro`**: `/media/movies` → `30.01_movies`, `/media/shows` →
    `30.02_tv`, `/media/music` → `30.03_music`, `/media/rotation` → `rotation`
    (`30.04_audiobooks` is intentionally unmounted until the Audiobookshelf/Kavita
    decision). Jellyfin writes nothing — its metadata lives in its config volume;
    deletions flow Jellyseerr → *arr APIs. Multiple RO mounts are fine: Jellyfin never
    links or renames.
  - Path-string consistency holds: transmission reports `/data/downloads/complete/x` and
    the *arrs see the file at exactly that path — no remote-path mappings.
  - All lscr.io writers get `PUID=1000`/`PGID=1000` (see Security posture) — and no
    `runAsUser`, which would disable PUID handling in linuxserver images.
- **NAS side:** zero export changes — the single root export (`fsid=1`,
  `no_subtree_check`) already serves subpath mounts.
- **Future service requirements** (binding when they arrive; the services themselves are
  out of scope): Immich per the photos section; paperless consumes `10_documents/inbox/`;
  a documents service (Nextcloud external-storage / Copyparty / OpenCloud posixfs) mounts
  `10_documents` — services that manage a proprietary on-disk format (Seafile) are
  disqualified.

## Cluster-compat matrix

- **Cluster:** single K3s cluster (this repo's only target); no minimum-minor change —
  the feature uses only core `v1` `PersistentVolume`/`PersistentVolumeClaim` APIs, no
  deprecated API versions, no new CRDs.
- **Addons:** `csi-driver-nfs` Helm chart pinned at `4.13.0` (`system/csi-driver-nfs/Chart.yaml`);
  no version change required.
- **NAS software:** mergerfs `2.41.1`, snapraid `13.0` (pinned in
  `metal/roles/storage/vars/main.yml`) — both satisfy the verified-behavior requirements.
- **Deprecation horizon:** none — core storage APIs are stable v1.

## Resource budget

No new workloads — this feature moves mounts, it does not add containers.

- `pv-nfs-media`: capacity declaration 4Ti (NFS capacity is nominal/advisory — actual
  space is the NAS pool; the value must merely be ≥ any PVC request bound to it).
- Jellyfin `data` PVC: unchanged at 50Gi, now holding configs only (headroom grows).
- Requests/limits for the Jellyfin stack are a pre-existing gap tracked in
  `docs/info/todo.md` (NFS branch review follow-ups) — out of scope here, not silently
  dropped.
- Blast radius: a runaway download fills the NAS pool, not Ceph — mergerfs `mfs` spreads
  writes to the emptiest branch; cluster workloads (Ceph-backed) are unaffected.

## Reliability posture

No new pods → probes, PDBs, spread constraints, and rollout strategy are **N/A** (nothing
schedulable changes). What does apply:

- NFS mounts stay `soft,timeo=600,retrans=2` — I/O errors instead of unkillable pods when
  the NAS is down (rationale documented in `system/csi-driver-nfs/values.yaml`).
- Static PVs use `Retain`; PVC binding via `volumeName` + `storageClassName: ""` — a
  deleted claim never destroys NAS data.
- Rollout of the mount change: ArgoCD sync replaces the pod; rollback = git revert +
  resync (PV/PVC are declarative; the old `Videos` layout is trivially restorable while
  the NAS is empty). Observable success signal: Jellyfin pod `Running` with all mounts,
  and the hardlink verification below passes.

## Security posture

- **No RBAC changes** — no new ServiceAccounts, Roles, or controllers.
- **NFS trust model:** `root_squash` with `anonuid/anongid=1000` remaps **only uid 0** —
  non-root container UIDs pass through unchanged, and `fsGroup` is inert on NFS volumes
  (kubelet does not chown NFS; supplementary-group tricks don't survive the linuxserver
  s6 privilege drop). Therefore every writer must actually *run* as `1000:1000`: the
  lscr.io containers (transmission, radarr, sonarr, prowlarr) get explicit
  `PUID=1000`/`PGID=1000` env (their default is uid 911), and no `runAsUser` override.
  Export restricted to the homelab CIDR + workstation (UFW on the NAS, router ACLs
  upstream).
- **Read-only enforcement at mount level:** Jellyfin's media mounts and Immich's
  `20.01_library` mount declare `readOnly: true` — kernel-enforced preservation boundary,
  not service-configuration hope.
- **Blast radius per subtree:** no pod mounts the NAS root; the torrent-exposed subtree is
  exactly `30_media`. Documents/photos are unreachable from the media stack.
- Pre-existing `hostPath: /dev/dri` and PSA posture of the Jellyfin chart are tracked in
  `docs/info/todo.md` — unchanged by this feature.

## Failure-mode narrative

1. **NAS down / mergerfs restart under live NFS server.** Impact: media stack I/O errors
   (soft mounts prevent permanent hangs); possible `ESTALE` on clients until
   remount/pod restart. Detection: Jellyfin unavailable; no NFS health alerting exists yet
   (tracked in `docs/info/todo.md` → "Storage Node / NFS Optimizations"). Recovery:
   restart NFS server after mergerfs is up, restart affected pods. Owner: the operator.
2. **Disk loss during the migration window (no parity yet).** Impact: loss of the NAS
   copy only — survivable *by design*: source drives are wiped one at a time, the last
   only after the first successful snapraid sync + scrub. Worst case: re-copy from source.
   Detection: SMART/dmesg. Owner: the operator, during the runbook.
3. **Silent hardlink breakage** (e.g. a future chart refactor splits an *arr's single
   `rotation` mount into separate per-dir subPath mounts — which `EXDEV`s even on one
   PVC). Impact: imports degrade to copies — 2× storage, seeding still works but space
   bleeds. Detection: `30_media` usage ≈2× expected; `stat -c %h <imported file>` returns
   1 while the torrent still seeds. Recovery: restore the single-mount topology;
   re-import or dedupe.
4. **Accepted risks:** (a) a torrent client that mutates completed files would corrupt
   parity of a promoted file via the shared inode — Transmission does not mutate completed
   data; accepted. (b) Immich's DB is the sole holder of albums/faces — mitigated by
   cluster PVC backups, accepted. (c) mergerfs `use_ino` option is legacy at 2.41.x
   (ignored) — cleanup noted, harmless.

## Migration plan

Ordering rule: **no source drive is wiped until every later safety net exists.** During
migration the pool has no parity; source drives are the only redundancy.

1. **Skeleton via IaC** — the tree is created by the storage role (replacing the current
   `storage_dirs` list); `00_meta/README.md` is templated from the same variable, so code
   and legend cannot drift. → verify: role idempotent, dirs present.
2. **Copy** drive A → `99_tmp/driveA/` with rsync. → verify: manifest comparison (step 3).
3. **Manifest verification** — `b3sum` manifest per dataset (the NAS copy, drives B, C),
   compared as **hash-sets** ("content on B present nowhere in the copy?"), which is
   immune to path differences between backup generations. Chosen over `rsync -c` passes:
   manifests read each dataset once (vs re-reading the NAS copy per comparison) and
   persist in `00_meta/migration/` as a permanent audit artifact. Unique content found on
   B/C is copied into `99_tmp/driveB_delta/` etc.
4. **Sort** `99_tmp` → numbered homes per the [mapping table](#migration-mapping); each
   move appended to a log in `00_meta/migration/`. Same-filesystem `mv` — instant.
5. **Cruft dies during sorting** — `.@__thumb`, `.streams`, `Thumbs.db`, superseded
   archive generations; deletions recorded in the log.
6. **Exit criterion:** `99_tmp` empty ∧ every manifest entry accounted for (moved or
   consciously deleted).
7. **Release drives one at a time:** verify the parity-size precondition (each parity
   device ≥ largest data branch — snapraid requirement; all drives are 18TB Seagates,
   confirmed 2026-08-22, so this holds, but the runbook checks `lsblk -b` anyway before
   any wipe) → wipe B/C → add to `parity_drives` in the sops inventory → storage role →
   snapraid initial sync + scrub. **Drive A last, only after the first successful
   sync/scrub.**

## Parity & backup policy

- **snapraid excludes** (in `snapraid.conf.j2`): **root-anchored** — `/30_media/rotation/`
  (covers the nested `downloads/`), `/10_documents/inbox/`, `/99_tmp/`. Root-anchoring
  matters: name-anchored patterns (`downloads/`) match at *any* depth and would silently
  exclude same-named directories inside `70_backups` dumps — the tier meant to be most
  protected. The pre-existing generic `downloads/` and `appdata/` lines carry the same
  hazard and are replaced/reviewed in the same change. Everything numbered is
  parity-protected. Churn thresholds (`delete_threshold: 40`, `update_threshold: 500`)
  stay meaningful because *unattended* machine churn is excluded — with one caveat: a
  large culling session in `20.02_camera` (parity-protected by design) that deletes >40
  files trips `delete_threshold` and aborts the nightly sync; after a big cull, run a
  manual `snapraid sync` (or a one-off threshold override) deliberately.
- **restic tiers** (enabled by the tree; policy values are follow-up work): `10/20` =
  frequent + long retention; `40/50/60/70/80/90` = periodic; `30_media` preserved =
  rare/optional (large, semi-replaceable); `rotation/`, `downloads/`, `99_tmp` = never.
- Promotion (`mv rotation/… → 30.0x/…`) surfaces to snapraid as a new file at an included
  path → parity computed fresh; a leftover seeding hardlink shares the inode harmlessly.

## Assumptions

1. Transmission never mutates completed files (parity validity of shared inodes) —
   falsifiable by checksumming a seeded file over time.
2. ~~mergerfs ≥ 2.40 semantics~~ **confirmed**: pinned 2.41.1 in the storage role.
3. The app-template chart supports one PVC mounted at multiple `subPath`s across
   containers — strongly indicated by the existing `data` PVC usage; verified when
   templating Task 4. (Linking containers use exactly ONE such mount each — see mount
   topology principle.)
4. The NFS PV stack works end-to-end — it has **never run** (todo.md, NFS branch review);
   first boot is the real validation.
5. With `PUID=1000`/`PGID=1000` set, the lscr.io containers write as `1000:1000` and the
   s6 init chown is a no-op on already-`1000:1000` dirs — verified by the write/hardlink
   proofs in Task 5. (fsGroup is known-inert on NFS; do not rely on it.)
6. Immich (at deploy time) supports ≥2 external libraries with per-library mount modes —
   re-verify against Immich docs when it is actually deployed.
7. Drives B/C are readable enough to produce manifests — tested in migration step 3.
   All drives (A/B/C and data branches) are same-size 18TB Seagates (owner-confirmed
   2026-08-22), satisfying snapraid's parity ≥ largest-data-disk requirement; the runbook
   re-checks sizes before any wipe regardless.

## Not Doing

- **SMB/Samba shares** — not needed now; the alias rule keeps them painless to add later.
- **Choosing the documents service** (Nextcloud vs Copyparty vs OpenCloud) — the tree
  exposes `10_documents`; selection is its own future design. Seafile is disqualified
  (proprietary chunk store).
- **Second media service (Plex)** for the preserved tier — the tree supports it; not chosen.
- **Automated promotion tooling** — `mv` is manual *by design*; curation is the feature.
- **Vault reorganization** — explicitly decoupled; only the legend note is written.
- **ZFS migration planning** — plain-dir portability is preserved; nothing more.
- **Extracting `70.05_code` archives into Gitea** — separate work.
- **restic policy values & NFS health monitoring** — enabled/anticipated here, designed
  elsewhere (todo.md items already track the latter).

## Rejected alternatives

- **trash-guides service-first tree** — native for the *arr ecosystem but discards the
  primary persona's numbered, legend-based navigation.
- **Downloads under `90_inbox`** — forces either a NAS-root mount into the torrent pod
  (blast-radius regression) or silent copy-fallback (2× storage, broken seeding).
- **Vault-mirrored taxonomy** — knowledge categories don't map to bulk files; the vault
  itself may be reorganized, and the NAS must not depend on it.
- **Flat tree + search services** — fails findable-from-legend and shell navigation.
- **Immich RW on the preserved library** — the service could delete originals (trash
  auto-purge), while XMP sidecars still wouldn't capture albums/faces; risk without the
  portability payoff.
- **Seeding directly from library paths** — *arr renames break torrent seeding; the
  hardlink two-name flow is the mechanism, not an optimization.
- **Single-digit sub-level numbering (`10.1`)** — breaks lexicographic sort at the 10th
  child; unfixable later under the never-rename rule.

## Verified claims (evidence base)

| Claim | Verdict | Source |
|---|---|---|
| mergerfs non-path-preserving (`mfs`) supports pool-wide hardlinks; `EXDEV` is a path-preserving-policy issue | Confirmed | [mergerfs FAQ](https://trapexit.github.io/mergerfs/latest/faq/why_isnt_it_working/), [mergerfs(1)](https://manpages.debian.org/unstable/mergerfs/mergerfs.1.en.html) |
| Hardlink/rename requires both paths under ONE bind mount (vfsmount) — one PVC is NOT sufficient: separate `subPath` mounts of the same PVC still `EXDEV` (kernel compares vfsmounts, not `st_dev`) | Confirmed — **corrected during design review**; empirically reproduced 2026-08-22 (cross-bind-mount `ln` fails with identical `st_dev`; single-parent-mount `ln` succeeds) | Kernel `do_linkat` semantics; local reproduction; design-review.md finding R2-P0 |
| *arrs hardlink-or-silently-copy; upgrades delete old files | Confirmed | *arr/trash-guides community documentation |
| Immich external libs delete originals when RW; `:ro` is the enforcement; no XMP on `:ro` | Confirmed (corrected during review) | [Immich libraries docs](https://docs.immich.app/features/libraries/), [discussion #24064](https://github.com/immich-app/immich/discussions/24064), [#13771](https://github.com/immich-app/immich/discussions/13771) |
| NFS subpath mounts of a FUSE export work via `fsid` + `no_subtree_check`; mergerfs restart ⇒ `ESTALE` | Confirmed | mergerfs docs + Gemini review |
| snapraid records hardlinks; excluded/included shared inodes protected via the included path; `name/` excludes match anywhere, `/name/` at disk root | Confirmed | [SnapRAID manual](https://www.snapraid.it/manual), [exclude-syntax thread](https://sourceforge.net/p/snapraid/discussion/1677233/thread/387da6b3/) |

## Migration mapping

| Backup source (drive layout) | Destination |
|---|---|
| `Backups/bak/*.zip`, `WinBackup`, `home_milleniumfalcon_*`, `manual/`, `dell_xps_15_flashdrive_tools` | `70.01_machines/<host>/` |
| `Backups/{thunderbird,jetbrains,brave}*` (zips + logs) | `70.02_apps/<app>/` |
| `Backups/mix3/`, `Mix3_Download_New/` | `70.03_mobile/mix3/` (DCIM, GCam, Snapseed, Pictures → `20.02_camera/mix3/`) |
| `Backups/aegis*`, `keep/`, `bookmarks*`, `session_buddy*`, `noscript*` | `70.04_exports/` |
| `Backups/Projects(code)`, `bak/IdeaProjects.zip` | `70.05_code/` |
| `Books/**` (fiction, non-fiction, esoterics, психология…) | `40.01_books/<genre>/` |
| `Books/_Audiobook/**` | `30.04_audiobooks/` |
| `Books/Dungeons & Dragons 5`, `Hobbies/D&D` | `50.01_dnd/` |
| `Documents/01_personal` | `10.01_personal/` |
| `Documents/03_baby` | `10.02_family/` |
| `Documents/08_finance`, `01_personal/20_purchases` | `10.03_finance/` |
| `Documents/02_work`, `01_personal/60_work` | `10.04_work/` |
| `Documents/temp` | triage → `10.0x` |
| `Education/**` (IT, Lingos, Video, guitar, Statistics) | `40.02_courses/` (books inside → `40.01`) |
| `Education/Torrents`, `Education/Temp` | triage in `99_tmp`; keepers → `40.0x`, rest deleted |
| `Hobbies/Airsoft` | `50.02_airsoft/` |
| `Hobbies/**` (other) | working-set test → `50.0x` or medium dirs |
| `Media/1. Music`, `1.1 Music` | `30.03_music/` |
| `Media/2. Movies` | `30.01_movies/` |
| `Media/3. TV Series` | `30.02_tv/` |
| `Media/5. Images/5.1 Photos` | `20.01_library/` |
| `Media/5. Images/5.2 Images` | triage → `20.01` or delete |
| `Media/6. Misc/HomeVideo` | `20.03_home_video/` |
| `Media/7. Temp` | triage in `99_tmp` |
| `cryptomator/` | `80_vault/` |
| `.@__thumb`, `.streams`, `Thumbs.db` | **delete** (QNAP/Windows cruft) |
