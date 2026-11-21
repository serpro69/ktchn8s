# Full storage provisioning

Use a clean checkout containing the candidate changes, on a Linux x86_64
controller with read/write KVM access and outbound access for the pinned Debian
12 image, distro packages and release downloads. The shared parity VM driver
creates a loopback-only guest on port 23101 with sparse 8 GiB branches, above
mergerfs 2.41.1’s default 4 GiB minimum free space. Each command destroys its own
previous scratch disks and creates a fresh guest. Run the commands serially.
From the repository root, enter `nix develop`, then run:

```bash
cd metal/roles/storage
set -o pipefail
NAS_PROVISION_CASE=data molecule test -s provision 2>&1 | tee /tmp/nas-provision-data.log
NAS_PROVISION_CASE=parity molecule test -s provision 2>&1 | tee /tmp/nas-provision-parity.log
```

Require a successful exit from each command. Retain the first converge recap,
the idempotence recap with `changed=0`, and verify output for each case. The
data case checks that the merged Netplan configuration and any existing
ifupdown interfaces file survive both applies, and that the primary interface
still has a dynamic IPv4 address. The parity case starts with the same DHCP
lease, applies static networking and reconnects over SSH after Netplan and UFW
take effect. It checks the active interface's merged Netplan settings, permanent
IPv4 address and default gateway. Both cases exercise UFW under Debian's default shell.

Preparation creates GPT partitions on serial-identified virtual disks and
clears the image's APT indexes. The public play installs all NAS packages,
formats and mounts the partitions and configures the export. The side-effect
step writes a sentinel and tests module recovery before idempotence. Verify
checks the sentinel, branch device numbers and filesystem roots, the pool,
active export, package ownership and timers. In the parity case it also runs
the explicit sync and full scrub, enables routine timers for a future date,
disables the backup timer and reapplies the public play. It checks that the
original parity bytes and full-sync invocation survive, requires the backup unit
to fail on a missing source, and exercises a one-to-two parity expansion.
The SMART fixture checks the same failing and unreadable disk identities in
warning and strict modes.

If a command is interrupted, run `molecule destroy -s provision` in the same
environment before using the port for another scenario. Keep private live
inventory and NAS devices outside this fixture.

## Fedora package acceptance

Run the Fedora check from `metal/roles/storage` inside the dev shell.

```bash
set -o pipefail
molecule test -s fedora-packages 2>&1 | tee /tmp/nas-fedora-packages.log
```

Molecule downloads the checksum-pinned Fedora 42 x86_64 cloud image and boots
a fresh headless KVM guest on loopback port 23102. It waits for SSH and
cloud-init, runs the production package play twice on the same boot, checks
the installed mergerfs RPM and SnapRAID executable, and destroys the guest.
Retain the first recap, the idempotence recap with `changed=0`, and the
versions from verify. The serial log is in the scenario's ephemeral directory
under `vms/fedora-packages/serial.log`. After an interruption, use
`molecule destroy -s fedora-packages` to clean up this scenario.

## Package checks on other guest releases

The full-role cases above run on Debian 12 amd64. To use the package play
independently on another release, boot a fresh disposable Debian or Fedora
guest matching a pinned mergerfs asset and give it working distribution repositories. Put only
those guests in the `nas_package_guests` group of a synthetic SSH inventory.
From `metal/`, run the following command twice, retaining the distribution,
version, architecture and both install recaps:

```bash
ANSIBLE_ROLES_PATH="$PWD/roles" ansible-playbook -i /path/to/package-guests.yml \
  roles/storage/molecule/provision/packages.yml
```

The second run should report zero changes. This play installs the actual distro
packages and exact SnapRAID release. It needs no disks or network reconfiguration.
