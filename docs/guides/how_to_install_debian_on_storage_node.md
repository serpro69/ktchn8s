---
icon: material/crosshairs-question
title: Install Debian on Storage Node
---

# :material-crosshairs-question: HowTo install Debian on the Storage Node

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
