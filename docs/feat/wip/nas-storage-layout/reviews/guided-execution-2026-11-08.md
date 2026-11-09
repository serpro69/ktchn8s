# Guided NAS storage acceptance: 8–9 November 2026

This summary records the completed live acceptance for Tasks 1, 11 and 13.
Tasks 1–4, 9 and 11–13 are complete; migration, parity release, application rollout
and final feature verification remain pending. See the [task list](../tasks.md)
for the unchanged acceptance criteria and dependencies.

The owner executed every homelab command. Code/command reviews preceded each
operator batch; assistant execution was limited to local inspection, edits and
isolated checks. Raw host output, disk identities, inventory details and transient
review artifacts are kept privately under the ignored `.nas-audit-evidence/`
directory. They are deliberately excluded from this repository summary.

## Task 1 live acceptance complete: 2026-11-09

The operator completed a populated check/diff preview, coordinated client/NFS
shutdown and normal pool unmount, then two real storage-role applications.
All configured data filesystems remained mounted and formatting was skipped.
The role created all 40 directories with UID/GID 1000 and mode 0775, plus the
legend and retirement file. The second application changed none of those tasks;
only the existing sensors-detect task reported a change.

Legacy cleanup removed only entries first confirmed empty through a branch-aware
scan. Removal was checked on the merged pool and every backing branch, rather
than accepting a successful rmdir exit alone. The final top level contained the
11 designed directories. The routine role still never deletes arbitrary legacy
content. This live result is separate from the earlier local and VM preservation
and idempotence checks.

Three prerequisite fixes were verified during preparation:

- Inventory requests YAML directly from SOPS, without yq conversion, and removes
  temporary plaintext on normal exits and handled signals. The committed synthetic
  test uses real Ansible parsing and host selection without production keys.
- Check-mode mount validation does not parse output from a skipped command.
  Skipped discovery remains unverified; a successful preview is not disk acceptance.
- An exact installed SnapRAID version skips archive installation and dependency
  cleanup. A missing/different version still requires the archive, and a failed
  version probe aborts. Version presence is not binary provenance verification.

The remaining installation/probe risks are tracked in
[the implementation follow-ups](../implementation.md#deferred-follow-ups-explicit).

## Task 11: live NFS acceptance

The full live run passed with mergerfs 2.41.1 and the required active node-retention,
path-hash inode and normal-unmount settings. The fixed-owner root-squash policy
was retained. The focused workflow proved:

- Two independent client kernels matched their selected Kubernetes nodes.
- Real UID/GID 1000 operations with cleared supplementary groups included denied
  writes, nested creation, hardlinks, promotion, deletion and exact-byte reads.
- Both clients passed 65-second idle/reopen and read-only filesystem rejection.
- Exactly one backing hardlink pair retained its device/inode identity through
  a normal client-unmount, NFS stop, pool unmount/mount and NFS recovery cycle.
- Both clients recovered reads and RO enforcement, and the second client repeated
  the writer lifecycle. Mergerfs memory was observed during the test; this is not
  a working-set capacity guarantee.
- Writer and reader Pods reached Succeeded and returned their final acceptance
  markers. Their resolved image IDs were recorded; the source tag remains mutable.
- The namespace, controller/client workspaces and fixture were removed. Client
  and selected-node fixture mounts were observed absent, followed by fixture
  absence on the pool and every branch.

An initial attempt failed at client mount creation because the NFS helpers were
missing. Its cleanup completed. Narrow client package preparation installed the
helpers and required dependencies, including dependency upgrades; helper versions
were then verified before the successful retry. That first failure did not reach
server recovery or Pod creation and was never counted as acceptance.

The final run reported 106 ok, 27 changed, zero failed/unreachable tasks and rc 0.
No repeat is required for that completed run. The existing `validate_nfs=true`
role path covers basic self-client/Pod probes; the full live lifecycle uses the
[focused acceptance entry point](../implementation.md#guided-live-acceptance-entry-point).
An empty consumer snapshot alone does not establish quiescence, and failed server
transitions still require operator assessment without force/lazy fallback.

## Task 13: audit tooling acceptance

The NAS stack differed from both earlier fixture stacks, so it received its own
unit and real RO-NFS access verification:

| Environment | Python | b3sum | Verified scope |
| --- | --- | --- | --- |
| Earlier local fixture | 3.12.10 | 1.8.2 | Audit unit suite |
| Earlier disposable VM | 3.11.2 | 1.2.0 | Unit suite and RO-NFS denial/repair/read fixture |
| Live NAS | 3.13.5 | 1.8.1 | All 31 unit tests without skips, actual RO-NFS fixture and teardown |

The live synthetic fixture produced three expected EACCES failures before its
recorded permission/ACL repair and zero afterward, with both payload files read.
Reconciliation likewise went from three declared metadata differences to zero,
while preserving bytes, xattrs and backing hardlinks. Unit, access and verification
records agreed on their ledger digest and tool/helper identities. The tested core
helper SHA256 was
`2ab80625954ce51e68551b224917cb7390d0e4fed39b44937c69b2189164243a`.

The run reported 52 ok, 26 changed, zero failed/unreachable tasks and rc 0. Evidence
transfer, normal client unmount, pool/all-branch fixture absence and NAS workspace
removal all passed. The retained files were also checked locally: all eight
protected records were present, and all six completed JSONL generation digests
were valid. Protected `evidence/` reports are authoritative; separately retained
raw reader copies are diagnostic material.

The core helper and original Molecule fixture remain unchanged. The separate
live harness protects the source and ledger, uses native object claims for root
metadata operations and nonrecursive cleanup, and preserves report namespaces.
Its 15 local regression tests passed, including substitution during cleanup and
real ACL effects. An actual localhost Ansible transfer test reproduced the initial
basename collision and verified the corrected relative-path transfer. Local tests
and source reviews were not substituted for the successful NAS execution above.
See [the live audit workflow](../implementation.md#guided-live-audit-acceptance).

## Review scope and remaining work

Independent internal and external reviews covered the scoped increments and
operator batches. Review corrections addressed path-following root operations,
reader-writable evidence, recursive deletion of substituted content and report
collisions before live audit execution. External source-coverage limits were
retained in the private records; source approvals did not certify live execution.
The actual operator results above establish the completed live gates.

A fresh VM run was unavailable in the assistant environment because KVM was
absent. The previously completed VM fixture was left unchanged; no new VM pass
is claimed. Interrupted or unreachable runs can still leave protected state for
assessment, and the runtime export assertions remain scoped to the known single
root export. These limits are not permission to skip required teardown or accept
partial output.

No real source was mounted, inventoried or copied, and no sorting, parity job,
source release or media deployment started. The owner stopped guided homelab work
after closing the completed tasks. On resumption, source labels and independent
recovery relationships must be reconciled before Task 6. The remaining sequence
is Tasks 6 → 7 → 8 → 5, then Task 10; the overall feature is still in progress.
