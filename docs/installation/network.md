---
icon: material/lan
---

# :material-lan: Network Configuration

!!! warning
    The following describes my current network components and configurations. Don't blindly copy-paste, but instead use this as a learning point and adjust to your needs, especially if you're using different hardware components.

!!! info
    For an overview of the network setup refer to [Network Architecture](../reference/architecture/network.md) page.

## Hardware Requirements

- Cisco C1111-8P Router
- Cisco C3560-GS-8P Switch
- Serial Console Cable
- "Controller" PC 
    - Any OS can be used, but since I work on Linux I won't provide serial console connectivity specifics for other OSes (which can also easily be found online). PRs with docs improvements are always welcome!

## Serial Console Connection

### Software

(In order of preference based on own brief experience)

- [minicom](https://help.ubuntu.com/community/Minicom)
    - easy to get started/configure with self-explanatory built-in help menu
    - seems to have some extra useful functionality
    - _NB! default `Ctrl-A` shortcut conflicts with my current `tmux` modifier key, hence I usually use `minicom` outside of `tmux`_
- [screen](https://www.gnu.org/software/screen/manual/screen.html)
- [gtkterm](https://github.com/wvdakker/gtkterm)
    - standalone terminal with easy UI/configurations, but doesn't seem to bring much more value compared to `minicom`
    - only tried it briefly

### Steps

- Install `minicom` (alternatively install `screen` or `gtkterm`, whichever you like best)
    - On ubuntu: `sudo apt install minicom`
- Connect the serial cable to the switch/router and PC
- Determine the port of the serial cable: `sudo dmesg | grep -i tty`
    - Let's assume the device port was `ttyUSB0`
- Follow the [minicom configuration guide](../guides/how_to_configure_minicom.md) to configure it
- Start minicom: `sudo minicom`
    - Alternatively, using screen: `sudo screen /dev/ttyUSB0 9600`

### References

- [Troubleshoot and Apply Correct Terminal Emulator Settings for Console Connections](https://www.cisco.com/c/en/us/support/docs/storage-networking/management/217970-troubleshoot-and-apply-correct-terminal.html)

### Troubleshooting

#### `[screen is terminating]` error

**tldr;** either add your user to `dialout` group, or run `screen` with `sudo`

Long version based on this [unix.stackexchange answer](https://unix.stackexchange.com/a/529120):

Does the user account have the permission to use `/dev/ttyUSB0`? To find out, please run `ls -l /dev/ttyUSB0`. The output might look like this:

```
$ ls -l /dev/ttyUSB0 
crw-rw----+ 1 root dialout 166, 0 Jul  9 08:55 /dev/ttyUSB0
```

The characters at the left-most column are the file type and permissions information:

- The first character is `c`, indicating a character-based device.
- The last character is `+`, indicating that there is an Access Control List (ACL for short) on this device node, specifying further access rules. This is important, because it changes how the other permissions are interpreted.
- The characters 2-4 are a three-letter group `rw-` indicating permissions for the file owner, which is `root` as indicated in the third column.
- The second group of three letters (`rw-` again) would classically indicate permissions applicable to the _group_ of users the file is assigned to. In this case, the group is `dialout` as indicated in the fourth column. **But because this file has an ACL, the meaning is different:** with an ACL in effect, it just indicates the highest permissions granted to a specific user or group that is not the file owner - but you cannot know which user or group it is.
- The third group of three letters (`---`) indicate access permissions for everyone else - if it's all dashes, it means no access is allowed.
- The last character is `+`, indicating that there is an Access Control List (ACL for short) on this device node, specifying further access rules.

Lastly, the ACL can be viewed with `getfacl /dev/ttyUSB0`. The output might look something like this:

```bash
getfacl /dev/ttyUSB0 
```

```
getfacl: Removing leading '/' from absolute path names
# file: dev/ttyUSB0
# owner: root
# group: dialout
user::rw-
user:sddm:rw-
group::rw-
mask::rw-
other::---
```

Basically, it repeats the traditional non-ACL file permissions and allows specifying extra permissions for any number of users and groups. In this case, there is an extra line `user:sddm:rw-` indicating both read and write access to user `sddm`, which is the user account the GUI login manager process `sddm` is currently running as. And there's also the `group::rw-` line that confirms that the classic `dialout` group has full read/write access to this file - this information was hidden from the classic `ls -l` output when an ACL was applied to this device node.

The fact that an ACL grants permissions to `sddm` indicates that this OS is probably configured to automatically grant access to local serial ports if you log in locally using the GUI login dialog. The ACL would be automatically changed to match the logged-in user, and back to `sddm` when the user logs out. If such an ACL is not present, then your distribution might not use such an automatic permissions mechanism.

The group name `dialout` is historical, because serial ports used to be used with modems. But if a device is assigned to a special group like this, it indicates the distribution is probably configured to manage access to serial ports using the `dialout` group. So in this example, you might want to add your user account to the `dialout` group. You'll need root/superuser access to do that:

```bash
sudo usermod -a -G dialout eric
```

New group memberships take effect at next login, so you'll need to log out and back again. Alternatively run:

```bash
newgrp dialout
```

Because the `/dev` filesystem is a virtual, RAM-based filesystem, all the device nodes are created from scratch every time the system boots. Because of this, trying to change the permissions of the actual device nodes would be futile; your changes would be forgotten when you shut down the system. Instead, the default permissions for the devices use specific groups, for the express purpose of allowing the administrators to use group memberships to grant specific users access to specific types of devices: using those groups as intended is probably the easiest way to solve your problem.

#### No (slow) console output

!!! tip
    Usually console output problems are related to faulty or poor-quality cables.

- Check the cable connection and ensure that the serial console cable is properly connected to both the switch/router and the PC.
- Try to reset the cable.

References:

- <https://www.reddit.com/r/homelab/comments/nyacjw/no_console_output_on_cisco_switch/>
- <https://community.cisco.com/t5/switching/blank-screen-and-no-console-access-on-cisco-switch/td-p/2964716>

