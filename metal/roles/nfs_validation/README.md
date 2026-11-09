# NFS validation

This role checks an already provisioned NAS. `tasks/main.yml` runs the basic
self-client and Kubernetes probes. `tasks/live_acceptance.yml` runs the explicit
two-client maintenance lifecycle. Neither includes storage convergence. Public
entry points and operator prerequisites are in the
[NFS guide](../../../docs/guides/how_to_use_nfs_for_persistent_storage.md).

The small mount/read/unmount tasks are reused before recovery, after recovery
and during teardown. Server runtime checks are shared with the disposable
storage-role Molecule scenario. The shell payloads and Pod template have one
home here so live and isolated checks exercise the same operations.

Node provisioning owns NFS package installation. Existing-client repair and
nonmutating helper checks live under `prerequisites/tasks/nfs_client_*.yml`;
including those task entry points does not run the broad prerequisites role.
Migration-tool acceptance remains the independent `storage-audit-acceptance.yml`
play and confined `scripts/nas-audit-fixture.py` harness.

Basic validation supports one schedulable Kubernetes node. Full acceptance
requires two distinct kernels bound to Kubernetes node names, a Debian NAS,
explicit maintenance consent, and quiescence maintained by the operator. Its
UID1000, backing-link, idle/reopen, recovery, Pod-completion and observed-teardown
guarantees are not weakened for a single-node deployment.

Local routing/guard tests: `python3 -B -m unittest discover -s tests -p test_nfs_workflow.py -v` from the repository root, with Ansible and PyYAML in the
established toolchain. They use synthetic inventories, extracted assertion tasks
and recording executables, never a homelab connection. The existing probe tests
and `storage/molecule/nfs-lifecycle` retain their separate scopes.
