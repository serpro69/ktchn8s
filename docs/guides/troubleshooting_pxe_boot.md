---
icon: material/crosshairs-question
---

# :material-crosshairs-question: Troubleshooting PXE Boot

First things to try:

- Remove the generated pxe boot files: `rm -rf metal && git checkout metal`; then re-run the ansible playbook
- Connect a monitor to one of the devices and run `bootstrap` playbook targeting only that device: `cd metal && make bootstrap ANSIBLE_TARGETS=localhost,megingjord`
    - Troubleshooting one device at a time is easier
- Check if the node gets stuck in GRUB after OS has been installed
    - Some systems expect a connected keyboard or screen (or both) for GRUB to start the countdown before automatically selecting the first entry. 
        - A few of my machines (Lenovo M70q gen.2 particularly) refuse to go beyond GRUB w/o a connected keyboard
        - Because of this, I have modified GRUB to disable countdown and hide the screen
        - NB! If you need to access GRUB, try holding <key>Shift</key> key during boot (See also [Grub menu at boot time... "holding shift" not working](https://askubuntu.com/questions/668049/grub-menu-at-boot-time-holding-shift-not-working) for troubleshooting.)

