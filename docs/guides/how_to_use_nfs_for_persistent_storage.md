---
icon: material/crosshairs-question
title: Use NFS for Persistent Storage
---

# :material-crosshairs-question: HowTo use NFS for Persistent Storage

The storage role provisions the NAS's mergerfs pool and NFSv4 export. Kubernetes
nodes receive their NFS client packages during node provisioning. The
[csi-driver-nfs chart](https://github.com/serpro69/ktchn8s/tree/master/system/csi-driver-nfs) then supplies static
volumes for applications. Validation is a separate, operator-run step after the
NAS and cluster exist.

!!! warning "Media integration is still pending on this branch"
    The NAS layout and live NFS acceptance are complete, and the system chart
    prepares `pv-nfs-media` for `30_media`. The Jellyfin chart still claims
    `pv-nfs-videos`. These charts are not yet a working media deployment together.
    [Task 5](../feat/wip/nas-storage-layout/tasks.md#task-5-jellyfin-stack-remount-end-to-end)
    owns their joint release after migration/parity acceptance (Tasks 6–8).
    An empty new NAS does not need migration-tool verification to serve NFS;
    it still needs a matching PV, PVC and application configuration before use.

## Provision from scratch

1. Install the NAS base OS first. It is not installed by the compute-node PXE
   workflow. General NAS provisioning supports Debian and Fedora; the full live
   lifecycle and audit tools below have narrower supported environments.
2. Add the host to the `nas` group in `metal/inventory/metal.yml`, with its address,
   network interface and pre-partitioned `data_drives`/`parity_drives`. Use stable
   disk-by-id names. An empty `parity_drives` list skips parity configuration.
   See the [metal installation guide](../installation/production/metal.md).
3. Use the established development environment and run `make metal` as the
   operator. Its sequence is NAS storage provisioning during bootstrap, followed
   by K3s node prerequisites and cluster creation. Keep `validate_nfs: false`
   (the default): the cluster does not exist yet when storage is provisioned.
   `make -C metal storage ANSIBLE_TARGETS=nas-host` converges only the selected NAS
   when that is the intended operation.
4. Complete system installation and select the intended controller kubeconfig.
   Run the optional basic validation below once the cluster can schedule Pods.
5. Configure matching static PVs, application PVCs and mounts, then release them
   through GitOps. The branch's pending media release is described above.

Provisioning creates the numbered layout, fixed-owner share directories, legend,
exports and service configuration. It does not migrate existing data, remove
legacy directories, run lifecycle acceptance, or start parity bootstrap. Normal
configuration changes can restart NFS; reapplying storage to an existing server
requires assessment of its active consumers.

### Inventory and installation prerequisites

Give each data or parity branch its own physical disk and identify its partition by ID. Keep
the inventory order stable. The role checks partition by-id, parent disk,
partition signature and current mounts across the complete list before creating
any filesystem. It reuses existing ext4. On a new, empty GPT partition, set
`format_blank: true` on that specific drive for initial installation. Remove
that permission after the first install. A probe error stops provisioning.

This synthetic inventory uses documentation-only addresses. Substitute your
own SSH user, addresses, CIDRs and partition IDs. Add a controller CIDR visible
from the NAS, including any NAT or jump host, before enabling its firewall.

```yaml
nas:
  hosts:
    nas-example:
      ansible_user: storage-admin
      ansible_host: 192.0.2.30
      homelab_net_cidr: 192.0.2.0/24
      firewall_allowed_networks: [192.0.2.0/24, 198.51.100.18/32]
      data_drives:
        - {id: ata-EXAMPLE_DATA_ONE-part1, format_blank: true}
        - {id: ata-EXAMPLE_DATA_TWO-part1, format_blank: true}
      parity_drives: []
      configure_network: false
      # To manage a static address, enable configure_network and supply:
      storage_network:
        interface: enp2s0
        address: 192.0.2.30
        netmask: 255.255.255.0
        gateway: 192.0.2.1
        dns_nameservers: [192.0.2.53]
```

With `configure_network: true`, Debian uses ifupdown on an interface it
already manages, or the active Netplan Ethernet definition on a networkd
host. The Netplan definition must identify this interface individually.
The role checks the merged address, default route and DNS settings before
installing its overlay. After applying networking and firewall policy, it
opens a fresh SSH connection using the inventory address and key.

For the project's inventory wrapper, configure `.sops.yaml` in your checkout
with your own age public recipient and give the controller access to the
corresponding private identity. Create/edit the encrypted
`metal/inventory/metal.yml` with SOPS. On a fresh checkout with another
operator's ciphertext, create a new inventory encrypted to your recipient.
For example, set the inventory creation rule to your public age recipient:

```yaml
creation_rules:
  - path_regex: 'metal/inventory/metal\.yml$'
    age: age1_REPLACE_WITH_YOUR_PUBLIC_RECIPIENT
```

From the repository root, encrypt a prepared plaintext inventory outside the
checkout with `sops encrypt --filename-override metal/inventory/metal.yml /path/to/nas.yml`.
Save its encrypted output as the inventory for your installation.
Keep plaintext and the age private key outside Git. A standalone synthetic
YAML inventory can also be passed directly with `ansible-playbook -i`.

The documented VM base is Debian 12 amd64. Both data-only and parity installs
need distro repositories, a matching mergerfs 2.41.1 release asset, and access
to the upstream SnapRAID v13.0 source archive on first install. Fedora RPMs use
the distribution major version and package release `-1`. The role pins the
asset SHA-256, builds SnapRAID from checksummed source when needed, and verifies
`/usr/local/bin/snapraid --version`. Build packages remain installed. Debian
keeps `xz-utils` for local DEB installs and checks the installed owner of
`/usr/bin/b3sum`. The NAS requires kernel support for NFS, FUSE and drivetemp.
See the [mergerfs release assets](https://github.com/trapexit/mergerfs/releases/tag/2.41.1)
and [Debian b3sum package](https://packages.debian.org/bookworm/b3sum).

### Initial parity or expansion

For a legacy array with a previously recorded successful full sync and scrub
(such as Task 8), a one-time ordinary apply with
`-e storage_adopt_accepted_parity=true` records its existing mounted layout.
Use this when adopting a paused array or before changing its legacy timer
policy. Already enabled, running legacy timers can continue on an unchanged
layout. The adoption option requires matching mounted filesystems, configuration
and nonempty parity/content files. A pending transition still requires explicit
acceptance. Omit the option for later applies.

1. Freeze writes to included data and serialize provisioning and parity
   operations. For an expansion, stop and disable the runner and scrub timers
   on the existing layout and wait for running services and manual jobs to
   finish. Set both `sync_enabled` and `scrub_enabled` to false. When supplying
   `snapraid_maintenance` in inventory, copy the complete role-default mapping
   and edit it. Retain the chosen policy for restoration.
2. Append each intended parity partition by ID, preserving existing branch
   order. Verify capacities and independent recovery of any previously used
   drive before releasing it. Converge the ordinary storage play. It checks
   timer and service state, queued jobs and manual processes, records the
   pending layout, and installs the explicit acceptance command. An existing
   installation configured through `storage-parity.yml` also needs this
   paused ordinary apply before using the acceptance command.
3. With the included dataset frozen, run `sudo /usr/local/sbin/storage-accept-parity`
   on the NAS in a persistent operator session. It verifies backing mounts,
   restarts the explicit full-sync service and requires a new successful
   invocation. It runs a clean diff, a full scrub, another clean diff and status
   checks for complete coverage and zero errors. Evidence stays in the printed
   directory under `/var/log/snapraid`. A failure leaves the layout pending.
   Resolve the cause and repeat the same explicit command. Retain parity
   and content files across retries.
4. Restore the chosen maintenance flags only after acceptance and apply the
   same inventory again. Inspect both `systemctl is-enabled` and
   `systemctl is-active` for the runner, scrub and content-backup timers.
   Reapplying an accepted layout preserves its parity files.
5. Content backups keep the configured number of complete generations under
   `/var/backups/snapraid`. Each generation retains each source's path
   (for example `mnt/data1/snapraid.content` and `var/snapraid.content`).
   The service verifies each copy before publishing or pruning a generation.
   Choose a complete generation when restoring content metadata.

The disposable Molecule scenario in `metal/roles/storage/molecule/provision/`
exercises the public play in data-only and parity configurations.

## Choose the check for the question

All commands in this guide are for the operator. Check playbooks use the installed
Ansible collections; prepare those with the repository's normal tooling setup.
They do not fetch credentials or install controller tooling. Replace `nas-host`
with exactly one inventory NAS name. `ANSIBLE_TARGETS` supplies Ansible's `--limit`.

| Operation | Entry point from the repository root | What it establishes |
| --- | --- | --- |
| Provisioning | `make -C metal storage ANSIBLE_TARGETS=nas-host` | Configures disks, pool, NFS and applicable parity settings; not acceptance. |
| Optional basic validation | `make -C metal storage-validate ANSIBLE_TARGETS=nas-host KUBECONFIG=/absolute/path/cluster.yaml` | NAS self-client writes/links/renames/reads, RO rejection and successful Kubernetes writer/reader Pods; no server stop or pool remount. |
| Disruptive acceptance | `make -C metal storage-acceptance …` with the variables below | Two independent client kernels, idle/reopen, backing hardlinks, normal server recovery, Pods and observed teardown. |
| Migration-tool verification | `make -C metal storage-audit-acceptance ANSIBLE_TARGETS=nas-host` | Synthetic unit/access/repair checks on the NAS's actual Python/b3sum stack; no real migration. |
| Existing-client repair | `make -C metal storage-client-setup …` with two client names | Targeted Fedora NFS package/helper preparation; not validation or normal NAS provisioning. |

The corresponding public playbooks are `metal/storage.yml`,
`metal/storage-validate.yml`, `metal/storage-acceptance.yml`,
`metal/storage-audit-acceptance.yml` and `metal/storage-client-setup.yml`.
Direct Ansible invocation uses the same inventory and variables from `metal/`.
Check mode is not acceptance: all four explicit check/repair plays reject it.
The Make check/repair targets reject `ANSIBLE_TAGS`. Run each check to completion
without other task filters (including filters in `ANSIBLE_ARGS` or Ansible
environment settings); a skipped or partial run is
not a passing result. Serialize these checks because basic and lifecycle
validation share the exclusive `99_tmp/nfs-readiness` fixture.

### Basic validation after cluster creation

The NAS must already have its pool and every configured branch mounted. The check
verifies active export/mergerfs settings, installs `attr` if needed, creates a
scoped scratch fixture, mounts it RW and RO on the NAS, and runs temporary Pods
in a new namespace. The controller needs cluster access and permission to create,
observe and delete those Pods and their namespace. `KUBECONFIG` must name an
absolute existing file; Make defaults to `metal/kubeconfig.yaml`; select another file explicitly with
a Make command-line `KUBECONFIG=/absolute/path/cluster.yaml` assignment. An
unrelated exported shell value does not change that default. Controller
prerequisites are checked before creating the NAS scratch fixture.

This is nondisruptive to the server, but it writes synthetic data and creates
mounts and Pods. Both Pods must succeed. Missing tools, cluster access or failed
probes are failures, not optional skips. Cleanup normally removes its mounts,
namespace, workspace and fixture; failed client teardown preserves the fixture
for assessment. Do not blindly delete a leftover fixture or rerun over it.

A [single-node cluster](how_to_run_cluster_with_a_single_node.md) can run this
check: writer and reader Pods run sequentially under normal scheduling. An
optional `nfs_readiness_client_nodes: [node-name, node-name]` pins both to that
node. Two Pods on one node do not establish two independent NFS clients.
The probes mount NFS directly, so success does not prove CSI PV/PVC binding or
application credentials and playback; those require application acceptance.

For existing callers, `validate_nfs=true` still runs these same basic checks at
the end of storage convergence. It requires an already running cluster and also
reapplies NAS configuration. Select exactly one NAS for this route too. Prefer `storage-validate` for an existing installation.
Neither route performs the disruptive lifecycle test or migration-tool checks.

### Full lifecycle acceptance in a maintenance window

This explicit tool supports the repository's Debian NAS layout and exactly two
distinct inventory-backed Kubernetes nodes with working NFS helpers. Their
inventory names must equal their Kubernetes node names. Boot IDs must match and
must identify different kernels; aliases of one machine cannot satisfy the gate.
A single-node deployment cannot complete this acceptance contract.

Keep all unrelated NFS clients, local writers and maintenance jobs stopped for
the entire run. `--limit nas-host` selects the NAS, but the play also delegates
mounts, reads and cleanup to the two clients and Kubernetes operations to the
controller. It normally stops NFS, releases exports, unmounts/remounts the pool
from its existing fstab entry, and restores NFS. It uses no force/lazy fallback.
A failed recovery stops for assessment; NFS or the pool may remain stopped.

Create a local variables file, for example `/absolute/path/nfs-lifecycle.yml`:

```yaml
nfs_lifecycle_clients: [worker-a, worker-b]
# Set true only after arranging the maintenance window described above.
nfs_lifecycle_maintenance: true
```

Then, as the operator:

```bash
make -C metal storage-acceptance ANSIBLE_TARGETS=nas-host \
  KUBECONFIG=/absolute/path/cluster.yaml \
  ANSIBLE_ARGS='-e @/absolute/path/nfs-lifecycle.yml'
```

Fresh K3s provisioning already installs `nfs-utils`. If selected existing Fedora
nodes lack runnable `mount.nfs`/`mount.nfs4`, use `storage-client-setup` with the same
client-list file before acceptance. That play selects one NAS but installs only
on the two clients; it does not need Kubernetes or the maintenance flag. The
repair policy uses dnf5 with module auto-install, weak dependencies, erasing and
downgrades disabled. Required package dependencies/scriptlets may still change
clients; missing libdnf5 or repository failures require assessment. The broader
node prerequisites role owns fresh installation and normal package updates.

The [recorded Task 11 acceptance](../feat/wip/nas-storage-layout/tasks.md#task-11-nfs-export-lifecycle-acceptance)
includes the completed live two-client run and teardown. This workflow cleanup
is not a reason to repeat that run. Revalidation after a relevant configuration
change produces new evidence; basic validation never substitutes for that gate.

### Migration tools are a separate workflow

`storage-audit-acceptance` needs the repository's Debian/ext4 `/mnt/dataN` layout,
active NFS, NAS Python 3 and `b3sum` already prepared, and UID/GID 1000 access. It
ensures `acl` is installed, runs all audit unit tests without skips, and exercises
synthetic denied-read → declared-repair → successful-read checks through RO NFS.
It requires no Kubernetes clients or pool remount. Its protected fixture harness
and private `.nas-audit-evidence/run-*` reports are separate from NFS readiness.

Use it when accepting migration tools or a changed NAS tool stack. A new empty
NAS can omit it. It neither accepts real migrated content nor authorizes copying,
parity jobs or drive release. Follow the [audit-tool guide](nas_migration_audit.md)
and the [pending migration gates](../feat/wip/nas-storage-layout/tasks.md#task-6-migration-copy-cross-drive-verification-manual-ops)
when that separate work is authorized.

## Static volumes and application permissions

Declare each scoped share in `system/csi-driver-nfs/values.yaml` under
`nfs.volumes`. PVs are cluster-scoped and belong to the system chart. Bind an
application PVC using the matching `volumeName` and `storageClassName: ""`;
use a capacity no larger than the PV's declared capacity. Mount only the required
subtree and enforce read-only consumers with `readOnly: true`.

The export uses `root_squash`, with anonymous UID/GID 1000 by default. Root
requests are mapped to that identity; non-root identities pass through. This
does not grant arbitrary ownership changes, and `fsGroup` alone does not make a
process UID 1000 or repair an NFS tree's ownership. The tested contract requires
actual writer credentials of 1000:1000 and NAS-side directory preparation.
Linuxserver images need `PUID=1000`/`PGID=1000`; verify the running service identity
rather than relying on a root exec session. Other identities require their own
permission policy and validation; the supplied probes intentionally test 1000.

Containers that link or rename across paths need both paths within one
`volumeMount`. Separate `subPath` mounts of the same PVC are distinct mounts and
can fail with `EXDEV`. Existing data permissions need their own access audit;
successful synthetic writes do not prove that copied media can be read.
See the [storage design](../feat/wip/nas-storage-layout/design.md#service-integration)
for the planned media mount and identity contract.
