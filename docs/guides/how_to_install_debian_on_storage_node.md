---
icon: material/crosshairs-question
title: Install Debian on Storage Node
---

# :material-crosshairs-question: HowTo install Debian on the Storage Node

## Installation

Install Debian using the standard (non-minimal) ISO image. During installation:

- Select the target boot disk (e.g. the NVMe drive, not the data drives)
- When prompted, create a temporary user (Debian requires this; it can be removed later)
- Choose "automated network configuration" (will be changed to static IP post-install)

!!! warning "Minimal images"
    If you are using a Debian minimal/netinst image, you will need to install additional packages manually before proceeding with Ansible provisioning:

    ```bash
    apt install python3 openssh-server sudo
    ```

    The standard ISO includes these by default.

## Post-Install

### Configure Network

If you have selected "automated network configuration" during installation process, you will need to update the network interface(s) to your desired settings to configure static IPs. To do so, modify the file located at `/etc/network/interfaces` with the following changes:

```diff
-allow-hotplug enp2s0
-iface enp2s0 inet dhcp
+auto enp2s0
+iface enp2s0 inet static
+  address 10.10.10.30/24
+  gateway 10.10.10.1
```

Repeat the same for all interfaces you want to use.

After that, restart the network interface(s) with `ifdown enp2s0` followed by `ifup enp2s0`.

!!! info
    See more details in the official [Network Configuration](https://wiki.debian.org/NetworkConfiguration#Configuring_the_interface_manually) documentation.

### APT Sources

If you didn't configure additional apt sources during installation, you may want to configure those now.

Add `debian.sources` file under `/etc/apt/sources.list.d` directory with the following contents:

```
Types: deb
URIs: http://deb.debian.org/debian
Suites: trixie trixie-updates
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb
URIs: http://deb.debian.org/debian-security
Suites: trixie-security
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
```

!!! info
    See more details in the official [SourcesList](https://wiki.debian.org/SourcesList) documentation, or use `man sources.list`

### SSH Access

- Add your ssh public key to `/root/.ssh/authorized_keys`
- Make sure you have the following line `AuthorizedKeysFile      .ssh/authorized_keys` in `/etc/ssh/ssh_config` file
- Then restart ssh service with `systemctl restart ssh` and check that it has "active (running)" status with `systemctl status ssh`

!!! tip
    The Ansible inventory expects to connect as `root` using the `~/.ssh/homelab_id_ed25519` key. Copy the public key from your controller machine:

    ```bash
    ssh-copy-id -i ~/.ssh/homelab_id_ed25519.pub root@10.10.10.30
    ```

    If `ssh-copy-id` is not available, copy the key manually:

    ```bash
    # On the controller
    cat ~/.ssh/homelab_id_ed25519.pub | ssh root@10.10.10.30 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
    ```

### Enable Root SSH Login

Debian disables root login via password by default, but allows key-based authentication. Verify that `/etc/ssh/sshd_config` contains:

```
PermitRootLogin prohibit-password
```

If it is set to `no`, change it to `prohibit-password` and restart SSH:

```bash
systemctl restart ssh
```

### Remove the temporary user

Debian does not allow to skip user creation step during installation process. If you don't plan to use that user, or just made a temporary user to "skip" that installation step, remember to remove the user with `deluser 'temp' --remove-all-files`, where `temp` is the username you specified during installation process.

## Ansible Pre-requisites Checklist

Before running the storage playbook (`ansible-playbook -i inventory.sh storage.yml`), verify the following on the storage node:

- [ ] Static IP configured (`10.10.10.30` on `enp2s0`)
- [ ] Node is reachable from the controller: `ping 10.10.10.30`
- [ ] SSH key-based root login works: `ssh -i ~/.ssh/homelab_id_ed25519 root@10.10.10.30`
- [ ] APT sources configured (for package installation)
- [ ] Data drives are physically installed and visible: `lsblk` shows the expected disks
- [ ] Data drives are partitioned (partition IDs match the inventory in `metal/inventory/metal.yml`)
