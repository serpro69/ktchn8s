---
icon: material/crosshairs-question
title: Update Device Firmware
---

# :material-crosshairs-question: HowTo update device firmware

On each node, run `fwupdmgr refresh` to update the firmware metadata, then `fwupdmgr update` to check for and apply available firmware updates:

```bash
[root@megingjord ~]# fwupdmgr refresh
```

```
WARNING: UEFI capsule updates not available or enabled in firmware setup
See https://github.com/fwupd/fwupd/wiki/PluginFlag:capsules-unsupported for more information.
Updating lvfs
Downloading…             [************************************** ]
Successfully downloaded new metadata: 2 local devices supported
```

```bash
[root@megingjord ~]# fwupdmgr update
```

```
WARNING: UEFI capsule updates not available or enabled in firmware setup
See https://github.com/fwupd/fwupd/wiki/PluginFlag:capsules-unsupported for more information.
╔══════════════════════════════════════════════════════════════════════════════╗
║ Upgrade XXXXXXNV256G LA KIOXIA from 1104ANLA to 1109ANLA?                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ [Support devices and Firmware version] XXXXXXNV256G 1109ANLA, XXXXXXNT256G   ║
║ 1109ANLA, XXXXXXNV512G 1109ANLA, XXXXXXNT512G 1109ANLA, XXXXXXNV1T02         ║
║ 1109ANLA, XXXXXXNT1T02 1109ANLA                                              ║
║                                                                              ║
║ [Problem Fixes] 1.To fix firmware issue of TCG Opal on reset function./2.To  ║
║ fix the firmware issues that SSD hang up due to conflict system operation    ║
║ with SSD.                                                                    ║
║                                                                              ║
║ [Support Product Scope] Lenovo ThinkPad, ThinkCentre, ThinkStation,          ║
║ IdeaCentre                                                                   ║
║                                                                              ║
║ 11MY002VMX must remain plugged into a power source for the duration of the   ║
║ update to avoid damage.                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
Perform operation? [Y|n]: y
Downloading…                  [*                                      ] 
Less than one minuteWaiting…  [***************************************]
Successfully installed firmware
╔══════════════════════════════════════════════════════════════════════════════╗
║ Upgrade UEFI dbx from 83 to 20241101?                                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ This updates the list of forbidden signatures (the "dbx") to the latest      ║
║ release from Microsoft.                                                      ║
║                                                                              ║
║ An insecure version of Howyar's SysReturn software was added, due to a       ║
║ security vulnerability that allowed an attacker to bypass UEFI Secure Boot.  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
Perform operation? [Y|n]: y
Updating UEFI dbx…       [ -                                     ]
Waiting…                 [***************************************]
Successfully installed firmware
An update requires a reboot to complete. Restart now? [y|N]: y
```

!!! info
    See also [How to update device firmware using fwupd on RHEL system?](https://access.redhat.com/solutions/5436071)
