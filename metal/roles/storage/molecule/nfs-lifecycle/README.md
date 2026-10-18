# NFS lifecycle scenario

Run from the repository root:

```bash
nix develop -c bash -c 'cd metal/roles/storage && molecule test -s nfs-lifecycle'
```

Requires Linux x86_64 with read/write access to `/dev/kvm`, about 3 GiB of guest
RAM, and network access for the first image/package downloads. QEMU 10.1.2,
Molecule 25.11.1 and Ansible Core 2.19.4 come from the existing `flake.lock`.
The Debian 12 generic image is build `20260923-2610`, verified by SHA-512;
guest packages use the Debian snapshot of 2026-09-24. Mergerfs 2.41.1 is verified
by SHA-256 against its upstream release asset. No production inventory or
kubeconfig is read. Missing KVM, kernel modules or services fails the scenario.

`create.yml` provisions three QEMU guests through `vms.py`. SSH forwards use
localhost ports 23001–23003; the NFS server uses localhost port 23049. Clients
reach that forward through QEMU's `10.0.2.2` gateway. An occupied port fails
creation; run only one copy of this scenario at a time. No host bridge, host
mount, physical disk or host NFS configuration is needed. The two data disks
are sparse 8 GiB images attached only to the server guest.

`prepare.yml` installs guest prerequisites, formats the two disposable disks,
and seeds retirement entries, legacy content and a restrictive descendant.
`converge.yml` includes the production mergerfs and NFS role tasks and handlers.
It excludes hardware discovery and keeps mutating probes in `verify.yml`.
Molecule's idempotence action requires zero changes on the second converge.

The verifier checks the active mergerfs options and export policy, all 40
layout directories, the generated legend and preservation fixtures. It then
uses the production writer probe as UID/GID 1000 with supplementary groups
cleared. Tests cover permission-denied failure, nested creation, hardlinks,
promotion, reads from both clients after 65 seconds idle, backing-device/inode
identity, read-only rejection, normal client/server unmount and recovery, and
another writer cycle through the second client. Mergerfs memory and guest
versions are recorded. NFS can cache a pre-link count; the probe allows up to
65 seconds for the count to become two, while read/stat errors fail immediately.

Task 13 extends verification with `audit-access.yml`. The guest installs Python 3
and `b3sum` from the same dated package snapshot, runs the helper's unit suite,
and copies a foreign-owned `0700` tree with an ACL denying UID 1000 into
`99_tmp/migration-audit/30_media`. Its ledger declares the required ownership,
mode and ACL changes before any repair. Actual UID/GID 1000 reads with no extra
groups must return a completed policy-failure report through an RO NFS mount.
The client unmounts before server-local repair; local reconciliation then proves
bytes, xattrs and backing hardlinks before a fresh RO mount must pass all reads.
The verifier requires the same ledger digest in both access reports and final
reconciliation. All data is synthetic and stays separate from real NAS inventory.

Audit evidence is fetched even after verification failure and retained under
`audit-evidence/{nfs-server,nfs-client-a}/` in the reported Molecule ephemeral
directory. Headers record Python/b3sum versions and the helper SHA-256. The guest
unit transcript is `vms/nfs-server/audit-unit.log`. Copy these records elsewhere
before another scenario run. NAS tool setup/version comparison remains Task 13.4;
real migrated-content acceptance remains Task 7.

To exercise audit-specific failure cleanup, set `NFS_AUDIT_FAIL_AFTER_DENIAL=1`
in the inner shell before `molecule test -s nfs-lifecycle`. This deliberately
fails after the denied-read report, while the audit client is still mounted.
Require a nonzero scenario exit, retained partial/before evidence, successful
cleanup/destroy, and a subsequent normal pass from freshly recreated guests.

To prove failure cleanup, run this command and require a **nonzero** exit at
the intentional assertion, followed by successful cleanup and destroy:

```bash
nix develop -c bash -c 'cd metal/roles/storage && NFS_TEST_FAIL_AFTER_MOUNT=1 molecule test -s nfs-lifecycle'
```

Then run the normal command to prove fresh recreation. `cleanup.yml` unmounts
clients and removes only scratch content; `destroy.yml` stops owned QEMU PIDs
and removes their scratch disks. Serial logs, the NFS journal and Molecule's
Ansible log remain available in its reported ephemeral directory. Preserve
those logs outside that directory before another run, which can overwrite them.
The driver explicitly exempts these logs and the verified base image from
Molecule's pruning; guest scratch disks and SSH keys are disposable.
For interrupted manual `create`/`verify` sessions, run `molecule cleanup` and
`molecule destroy`, each with `-s nfs-lifecycle`. If a guest is unreachable,
`destroy` can still stop its controller-owned QEMU process.

Molecule 25.11.1 logs a missing `default` scenario as `CRITICAL`, then proceeds
with this named scenario; inspect the actual action results and exit status.
The bundled mount collection also emits an Ansible deprecation warning.

Fast regressions run with `nix develop -c python3 -B -m unittest discover -s tests
-p test_nfs_readiness.py -v` from the repository root. The payload tests require
controller UID/GID 1000; VM tests always set the guest identity explicitly.

Passing here does not establish NAS capacity, live Kubernetes integration or
application acceptance. Those remain the separate gates in Task 11 and Tasks
5–8 of `docs/feat/wip/nas-storage-layout/`. The VM scenario deliberately does
not invoke `k8s_validation.yml`; that path requires a real selected kubeconfig
and successful writer/reader pods when the offline NAS returns.
