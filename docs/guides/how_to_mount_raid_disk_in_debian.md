---
icon: material/crosshairs-question
title: Mount RAID Disk in Debian
---

# :material-crosshairs-question: HowTo mount RAID disks in Debian

When I migrated from a QNAP NAS to a custom-built NAS which now serves as nfs storage for my cluster, I needed to copy over the data from my QNAP disks before I could re-purpose them in the new NAS. Transferring the data over network was going to take a lot of time... so I tried to mount the disks directly inside the freshly installed Debian OS. All in all this was a bit harder than anticipated, so I documented my steps.

!!! note
    This guide may not work for every RAID setup, but can still provide a reference for similar use-cases.

## Steps

### Dependencies 

First we need to install `mdadm` and `lvm2` packages. On debian you can do this by running:

```bash
sudo apt install -y mdadm lvm2
```

### Activate and mount the Volume Group

!!! info
    NB! All the following commands need `sudo`

Then run the following command to assemble the array:

```bash
mdadm --assemble --scan
```

Now we can scan the logical volumes with:

```bash
lvscan
```

```text
  WARNING: PV /dev/md2 in VG vg288 is using an old PV header, modify the VG to update.
  inactive            '/dev/vg288/lv545' [144.12 GiB] inherit
  inactive            '/dev/vg288/lv2' [16.22 TiB] inherit
```

!!! tip
    Can also run `vgdisplay` to show things in a more human-readable format.

The volume group is `vg288`, so now we might need to activate it, if it's inactive, with:

```bash
vgchange -ay vg288
```

Re-run `vgscan` to see that volume group is now active:

```text
  WARNING: PV /dev/md2 in VG vg288 is using an old PV header, modify the VG to update.
  ACTIVE            '/dev/vg288/lv545' [144.12 GiB] inherit
  ACTIVE            '/dev/vg288/lv2' [16.22 TiB] inherit
```

Now create the mount point and mount the volume group:

```bash
mkdir /mnt/qnapvolume
mount /dev/vg288/lv2 /mnt/qnapvolume
```

The data will now be available under `/mnt/qnapvolume`

### Unmount and deactivate the volume group

First unmount the mount-point:

```bash
umount /mnt/qnapvolume
```

To deactivate the volume group run:

```bash
vgchange -an vg288
```

Then stop the array:

```bash
mdadm --stop --scan
```

After this one can power-off the drive with:

!!! note
    This command does not need `sudo`

```bash
udisksctl power-off -b /dev/sdX
```

where `X` is the device number

## References

- https://forum.qnap.com/viewtopic.php?t=160406
- https://forum.qnap.com/viewtopic.php?t=93862
- https://superuser.com/a/666034
- https://unix.stackexchange.com/questions/34702/how-to-properly-unplug-plug-removable-lvm2-device
- https://www.digitalocean.com/community/tutorials/how-to-manage-raid-arrays-with-mdadm-on-ubuntu-22-04
