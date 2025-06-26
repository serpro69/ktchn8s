---
icon: material/server
---

# :material-server: Metal Provisioning

## Pre-Requisites

### Hardware

#### Local Controller

!!! info
    The local controller is the machine used to bootstrap the cluster.
    We only need it once during initial provisioning, and you can use your laptop or desktop.

- Local controller must be a Linux machine that can run Docker (because the `host` networking driver used for PXE boot only supports Linux.
    - You can use a Linux virtual machine with bridged networking if you're on MacOS or Windows.

#### Servers

Any modern `x86_64` computer(s) should work, use whatever you have on hand.

!!! info
    Requirements for _each_ node

| Component  | Minimum | Recommended |
| ---------- | ------- | ----------- |
| CPU        | 2 cores | 4 cores     |
| RAM        | 8 GB    | 16 GB       |
| Hard drive | 128 GB  | 256/512 GB  |

Required Capabilities:

- Ability to boot from the network (PXE boot)
- Wake-on-LAN capability, used to wake the machines up automatically without physically touching the power button

### BIOS Configuration

!!! info
    You need to do it once per machine if the default config is not sufficent.
    Usually for consumer hardware this can not be automated
    (it requires something like [IPMI](https://en.wikipedia.org/wiki/Intelligent_Platform_Management_Interface) to automate).

Common settings:

- Enable Wake-on-LAN (WoL) and network boot
- Use UEFI mode and disable CSM (legacy) mode
- Disable secure boot

Boot order options (select one, each has their pros and cons):

1. Only boot from the network if no operating system found: works on most hardware but you need to manually wipe your hard drive or delete the existing boot record for the current OS
2. Prefer booting from the network if turned on via WoL: more convenience but your BIOS must support it, and you must test it throughly to ensure you don't accidentally wipe your servers
    - I use this option with some safeguards in place that prevent accidental server wipes
    - My servers will try to boot from network and if they find a PXE server, they will boot from it, otherwise they will reboot, and then boot using the Primary Boot Sequence
        - During `bootstrap`, the PXE server is started on the local controller, so the servers will boot from this PXE on WoL
        - Then I have a separate make `wake` target for just waking up the servers which ensures that the local PXE server on the controller is down before sending WoL magic packets
    - For servers that don't support it (strangely enough, my M70q gen.2 servers do not...), I've written a separate [`wipe` playbook](https://github.com/serpro69/ktchn8s/blob/master/metal/wipe.yml) that allows me to wipe a target server remotely via a single command: `make wipe SERVER=megingjord DISK=/dev/nvme0n1`

!!! example
    Below is an example of my BIOS setup on Lenovo mini PCs:

!!! tip
    I always reset the BIOS to factory defaults before making any changes, so that I don't have to worry about any custom settings, and only need to worry about modifying a subset of settings w/o worrying about everything else.

#### Leveno M70q Gen. 2/3

- Reset to factory defaults
- Devices -> Network Setup
    - Wireless LAN -> Disabled
    - PXE IPV4 Network Stack -> Enabled
    - PXE IPV6 Network Stack -> Disabled
- Devices -> Bluetooth -> Disabled
- Advanced -> CPU Setup
    - VT-d -> Enabled (should be enabled by default, along with most other CPU options)
- Power -> Automatic Power On
    - Wake on LAN -> Network (or Enabled)
    - Wake from Serial Port Ring -> Disabled
- Security -> Secure Boot
    - Secure Boot -> Disabled
- Startup
    - Boot Order:
        - M.2 Drive 1 (_NB! you won't see this option if the drive is wiped, but it should default to this sequence once an OS is installed_)
        - SATA 1 (_same as above if you use a sata drive_)
        - Network 1
    - First Boot Device -> Boot Order
    - Fast Boot -> Enabled # can cause a loop boot via WoL/PXE even after OS is installed

#### Leveno M720q

- Reset to factory defaults
- Devices -> Network Setup
    - Wireless LAN -> Disabled
    - PXE IPV4 Network Stack -> Enabled
    - PXE IPV6 Network Stack -> Disabled
- Devices -> Bluetooth -> Disabled
- Advanced -> CPU Setup
    - VT-d -> Enabled (should be enabled by default, along with most other CPU options)
- Power -> Automatic Power On
    - Wake on LAN -> Automatic
- Security -> Secure Boot
    - Secure Boot -> Disabled
- Startup
    - CSM -> Disabled
    - Primary Boot Sequence  # Used for manual power-on
        - M.2 Drive 1
        - SATA 1
        - Network 1
        - USB HDD
        - USB CDROM
        - Other Device
    - Automatic Boot Sequence # Used for Wake-on-LAN
        - Network 1
        - M.2 Drive 1
        - SATA 1

### Network

!!! info
    This section is optional and you may have your own network setup, which will still work fine.
    The only pre-requisite is that all your servers are connected to the same wired network as your [local controller](#local-controller).

- [Network Configuration](./network.md) is completed.

- All nodes are connected to switch ports on Vlan 10 (configured during network installation [stage 2](network.md#stage-2) and [stage 3](network.md#stage-3)).

- Local controller must be on the same Vlan 10 (i.e. physically connected to one of the switch ports on this Vlan, e.g. `g0/0/10` on `bifrost`, which was configured as an additional Vlan 10 port in [stage 3](network.md#stage-3) network configuration).

## Installation

!!! warning
    This will erase all data on the nodes.
    Ensure you have backups of any important data before you proceed.

Launch the [dev shell](../../concepts/development_shell.md):

```sh
nix develop
```

Bootstrap the nodes:

```sh
make metal
```
