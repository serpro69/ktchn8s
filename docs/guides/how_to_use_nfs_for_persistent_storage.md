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
requires assessment of its active consumers. The inherited formatting path has an
[open probe-error safeguard](../feat/wip/nas-storage-layout/implementation.md#deferred-follow-ups-explicit);
review disk identity and formatting intent before applying it to unmounted volumes.

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
