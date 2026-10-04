# Parity lifecycle scenario

Run from the repository root:

```bash
nix develop -c bash -c 'cd metal/roles/storage && molecule test -s parity-lifecycle'
```

Requires Linux x86_64, read/write access to `/dev/kvm`, 1 GiB of guest RAM,
and network access for the image, source and package downloads. QEMU 10.1.2,
Molecule 25.11.1 and Ansible Core 2.19.4 come from `flake.lock`. The Debian 12
generic image is build `20260923-2610`, verified by SHA-512; guest build tools
come from the 2026-09-24 Debian snapshot. SnapRAID is built from the SHA-256
pinned upstream v13.0 source archive, with its version checked before testing.
The production snapraid-runner revision and checksum come from role variables.

The scenario owns one QEMU guest, four sparse 2 GiB scratch disks and its SSH
key. SSH binds only to localhost port 23101; an occupied port fails creation.
No host mounts, physical disks, production inventory or kubeconfig are used.
The two data filesystems, two parity filesystems and root filesystem (third
content copy) must have distinct device IDs. Missing KVM/systemd/filesystem
capabilities fails the scenario. It can run independently of `nfs-lifecycle`.

`converge.yml` calls the actual `snapraid.yml` role tasks and handlers with
maintenance disabled. Molecule requires zero changes on its second converge.
Verification then checks:

- Original payload SHA-256 hashes before and after every invocation, against
  a baseline captured before the first sync and stored outside the data disks.
- Configuration alone creates no parity/content files and starts no jobs.
- Explicit first sync succeeds, with a distinct invocation result and journal.
- Adding second parity and changing timer templates preserves the first parity
  and content files byte-for-byte without running jobs or reactivating timers.
- Explicit expansion initializes both levels while retaining first parity;
  an actual full scrub verifies the result.
- A real full sync is throttled using a guest-only runtime CPU quota, killed
  after it writes to disk, and recorded as failed. Configuration remains
  runnable and an explicit retry succeeds without removing parity/content.
- A temporary executable that exits 42 produces `Result=exit-code` and
  `ExecMainStatus=42`. The real executable is restored in an `always` block;
  another explicit sync, unchanged-data check and full scrub must succeed.

The production unit has no start timeout. The small-fixture verifier imposes
its own 120-second limit per invocation so a broken test fails promptly.
The unit retains successful `active (exited)` status with `RemainAfterExit=yes`;
every test/operator invocation uses `systemctl restart` to execute a fresh job.
Plain `start` on a completed active unit would not run again. This preserves
completion metadata that systemd otherwise garbage-collects for inactive units.
Fast evidence-error regressions run from the repository root with
`nix develop -c python3 -B -m unittest discover -s tests -p test_parity_lifecycle.py -v`.
Neither an existing parity file nor an older successful invocation satisfies
the verifier. Interruption tests a process crash; it does not simulate power
loss or establish NAS-scale performance.

Prove cleanup after an intentionally failed scenario:

```bash
nix develop -c bash -c 'cd metal/roles/storage && PARITY_TEST_FAIL_AFTER_SYNC=1 molecule test -s parity-lifecycle'
```

Require nonzero exit at the intentional assertion and successful cleanup and
destroy. Then run the normal command again to prove fresh recreation. Guest
invocation JSON, journals, scrub output, versions, serial logs and Ansible logs
remain in Molecule's reported ephemeral directory. Set
`MOLECULE_EPHEMERAL_DIRECTORY=/tmp/ktchn8s-parity-lifecycle` in the inner shell
to choose a controller workspace. Copy evidence elsewhere before a subsequent
run: it can overwrite the same filenames. Cleanup fetches evidence, stops
guest jobs, and destroys owned QEMU processes/disks even if guest cleanup fails.
`destroy` alone also works when SSH is unavailable; it retains controller logs.
After interrupting a manual session, run `molecule cleanup -s parity-lifecycle`
and `molecule destroy -s parity-lifecycle` inside the same environment.

Molecule 25.11.1 reports a missing `default` scenario as `CRITICAL` before
proceeding with this named scenario. Judge results by action outcomes and the
final process exit. The bundled mount collection emits a deprecation warning.

Passing this disposable fixture does not authorize NAS drive release. Real NAS
configuration, syncs, full scrubs and recovery evidence remain Task 8 in
`docs/feat/wip/nas-storage-layout/`; the NAS is offline during Task 12 work.
