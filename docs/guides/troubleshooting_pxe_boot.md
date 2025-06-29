---
icon: material/crosshairs-question
title: PXE Boot
---

# :material-crosshairs-question: Troubleshooting PXE Boot

## PXE server logs

To view PXE server (includes DHCP, TFTP and HTTP server) logs:

```sh
./scripts/pxe-logs.sh
```

!!! tip
    You can view the logs of one or more containers selectively, for example:
    ```sh
    ./scripts/pxe-logs dnsmasq
    ./scripts/pxe-logs http
    ```

## Nodes not booting from the network

First things to try:

- Remove the generated pxe boot files: `rm -rf metal && git checkout metal`; then re-run the ansible playbook
- Connect a monitor and a keyboard to one of the nodes and run `bootstrap` playbook targeting only that node: `cd metal && make bootstrap ANSIBLE_TARGETS=localhost,megingjord`
    - Troubleshooting one node at a time is easier
- Check if the controller (PXE server) is on the same subnet with bare metal nodes (sometimes Wifi will not work or conflict with wired Ethernet, try to turn it off)
    - This should usually be handled by the playbooks, but still good to check
- Check if bare metal nodes are configured to boot from the network
- Check if Wake-on-LAN is enabled
- Check if the operating system ISO file is mounted
- Check the controller's firewall config to make sure that the following ports are open:
    - DHCP (67/68)
    - TFTP (69)
    - HTTP (80)
- Check [PXE server Docker logs](#pxe-server-logs)
- Check if the servers are booting to the correct OS (Fedora Server installer instead of the previously installed OS)
    - If not, try to select it manually or remove the previous OS boot entry
- Examine the network boot process with [Wireshark](https://www.wireshark.org) or [Termshark](https://termshark.io)

## Nodes not booting after OS installation

- Check if the node gets stuck in GRUB after OS has been installed
    - Some systems expect a connected keyboard or screen (or both) for GRUB to start the countdown before automatically selecting the first entry. 
        - A few of my machines (Lenovo M70q gen.2 particularly) refuse to go beyond GRUB w/o a connected keyboard
        - Because of this, I have modified GRUB to disable countdown and hide the screen
        - NB! If you need to access GRUB, try holding <key>Shift</key> key during boot (See also [Grub menu at boot time... "holding shift" not working](https://askubuntu.com/questions/668049/grub-menu-at-boot-time-holding-shift-not-working) for troubleshooting.)
