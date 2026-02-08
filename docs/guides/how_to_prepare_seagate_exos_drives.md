---
icon: material/crosshairs-question
title: Prepare Seagate EXOS Drives
---

# :material-crosshairs-question: HowTo prepare Seagate EXOS drives

After completing [Debian Installation](/docs/guides/how_to_install_debian_on_storage_node.md) on the Storage Node, and installing the drives, you may want to perform some or all of the below steps before using them for storing your data.

!!! warning
    This guide is for Seagate EXOS drives only and supports the following models:<br/>
    - ST18000NM000J 2TV103
    - ST16000NM000J 2TW103
    - ST14000NM000J 2TX103
    - ST12000NM000J 2TY103
    - ST10000NM018G 3CD103
    NB! I personally only tested this on `ST18000NM000J` models.<br/>
    Feel free to create a PR with documentation for your specific drives, if you think it might be helpful to others.

!!! tip
    You can download necessary binaries and firmware files from [ktchn8s-files](https://github.com/serpro69/ktchn8s-files) repo.

## Updating Firmware

First we need to download and copy firmware file to the box.

!!! info
    The easiest way to get the correct firmware build and seachest firmware flash tool: [https://apps1.seagate.com/downloads/request.html](https://apps1.seagate.com/downloads/request.html)<br/>
    Enter the serial number of your drive. Download the firmware and seachest utility provided in a zip file.

Use `scp` to copy the firmware archive to the node:

```bash
scp ExosX18-EvansBP-STD-SATA-512E-SN06.zip yggdrasil:/root/.
ssh yggdrasil
```

Then inside the box update the firmware:

```bash
#root@yggdrasil:~#
cd $(mktemp -d)
mv ~/ExosX18-EvansBP-STD-SATA-512E-SN06.zip .
unzip ExosX18-EvansBP-STD-SATA-512E-SN06.zip

# copy the seachest-firmware to current directory and make sure it works
cp command\ line\ tools/SeaChest/x86_64/SeaChest_Firmware_linux_x86_64 firmware/.
cd firmware/
chmod +x SeaChest_Firmware_linux_x86_64
./SeaChest_Firmware_linux_x86_64 --help

# scan devices
./SeaChest_Firmware_x86_64-alpine-linux-musl_static --scan

# update firmware
./SeaChest_Firmware_x86_64-alpine-linux-musl_static -d /dev/sg0 --fwdlConfig ENBP-SN06.CFS
./SeaChest_Firmware_x86_64-alpine-linux-musl_static -d /dev/sg1 --fwdlConfig ENBP-SN06.CFS
./SeaChest_Firmware_x86_64-alpine-linux-musl_static -d /dev/sg2 --fwdlConfig ENBP-SN06.CFS
./SeaChest_Firmware_x86_64-alpine-linux-musl_static -d /dev/sg3 --fwdlConfig ENBP-SN06.CFS
./SeaChest_Firmware_x86_64-alpine-linux-musl_static -d /dev/sg4 --fwdlConfig ENBP-SN06.CFS
./SeaChest_Firmware_x86_64-alpine-linux-musl_static -d /dev/sg5 --fwdlConfig ENBP-SN06.CFS

# scan and check fw was updated
./SeaChest_Firmware_x86_64-alpine-linux-musl_static --scan
```

!!! warning
    The `SeaChest_Firmware_linux_x86_64` distributed with the `SN06` firmware might return `File in "File" key in config file cannot be opened.` or `Couldn't open file EvansBPExosX18SATA-STD-512E-SN06.LOD` error (depending on the command you use to update the firmware)<br/>
    If you're encountering the same errors, try the `SeaChest_Firmware_linux_x86_64` from the [SeaChestUtilities](https://www.seagate.com/support/software/seachest/) distribution.

## Disable PowerBalance and EPC features

After updating the firmware we should consider disabling the powerBalance and EPC features on the drives because the OS might be waking up drives constantly, which increases the head cycle count and might reduce longevity of the drives.

Get the [SeaChestUtilities](https://www.seagate.com/support/software/seachest/), copy it to the box and unzip somewhere.

### Disable PowerBalance and EPC

```bash
chmod +x SeaChest_PowerControl_linux_x86_64

# Disable PowerBalance

./SeaChest_PowerControl_linux_x86_64 -d /dev/sg0 --powerBalanceFeature disable
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg1 --powerBalanceFeature disable
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg2 --powerBalanceFeature disable
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg3 --powerBalanceFeature disable
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg4 --powerBalanceFeature disable
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg5 --powerBalanceFeature disable

# Disable EPC

./SeaChest_PowerControl_linux_x86_64 -d /dev/sg0 --EPCfeature disable
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg1 --EPCfeature disable
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg2 --EPCfeature disable
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg3 --EPCfeature disable
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg4 --EPCfeature disable
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg5 --EPCfeature disable
```

### Check the Power Mode and EPC Settings:

```bash
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg0 --checkPowerMode
```

```
==========================================================================================
 SeaChest_PowerControl - Seagate drive utilities - NVMe Enabled
 Copyright (c) 2014-2025 Seagate Technology LLC and/or its Affiliates, All Rights Reserved
 SeaChest_PowerControl Version: 3.7.1 X86_64
 Build Date: Jul 30 2025
 Today: 20250921T151219 User: root
==========================================================================================

/dev/sg0 - ST18000NM000J-2TV103 - ZR53Z7Z4 - SN06 - ATA
Device is in the PM0: Active state or PM1: Idle State
```

```bash
./SeaChest_PowerControl_linux_x86_64 -d /dev/sg0 --showEPCSettings
```

```
==========================================================================================
 SeaChest_PowerControl - Seagate drive utilities - NVMe Enabled
 Copyright (c) 2014-2025 Seagate Technology LLC and/or its Affiliates, All Rights Reserved
 SeaChest_PowerControl Version: 3.7.1 X86_64
 Build Date: Jul 30 2025
 Today: 20250921T151244 User: root
==========================================================================================

/dev/sg0 - ST18000NM000J-2TV103 - ZR53Z7Z4 - SN06 - ATA

===EPC Settings===
        * = timer is enabled
        C column = Changeable
        S column = Savable
        All times are in 100 milliseconds

Name       Current Timer Default Timer Saved Timer   Recovery Time C S
Idle A      0            *1            *1            1             Y Y
Idle B      0            *1200         *1200         4             Y Y
Idle C      0             6000          6000         20            Y Y
Standby Z   0             9000          9000         110           Y Y
```

### Check SMART Attributes

```bash
./SeaChest_SMART_linux_x86_64 -d /dev/sg0 --smartAttributes hybrid
```

```
==========================================================================================
 SeaChest_SMART - Seagate drive utilities - NVMe Enabled
 Copyright (c) 2014-2025 Seagate Technology LLC and/or its Affiliates, All Rights Reserved
 SeaChest_SMART Version: 2.6.1 X86_64
 Build Date: Jul 30 2025
 Today: 20250921T151438 User: root
==========================================================================================

/dev/sg0 - ST18000NM000J-2TV103 - ZR53Z7Z4 - SN06 - ATA
=======Key======
        Flags:
          P - pre-fail/warranty indicator
          O - online collection of data while device is running
          S - Performance degrades as current value decreases
          R - Error Rate - indicates tracking of an error rate
          C - Event Count - attribute represents a counter of events
          K - Self Preservation (saved across power-cycles)
        Thresholds/Current/Worst:
          N/A - thresholds not available for this attribute/device
          AP  - threshold is always passing (value of zero)
          AF  - threshold is always failing (value of 255)
          INV - threshold is set to an invalid value (value of 254)
        Other indicators:
          ? - See analyzed output for more information on raw data
          ! - attribute is currently failing
          ^ - attribute has previously failed
          % - attribute is currently issuing a warning
          ~ - attribute has previously warned about its condition
        Temperature: (Celcius unless specified)
          m = minimum
          M = maximum
        Columns:
          CV - current value (Also called nominal value in specifications)
          WV - worst ever value
          TV - threshold value (requires support of thresholds data)
          Raw - raw data associated with attribute. Vendor specific definition.
SMART Version: 10
     # Attribute Name:                     Flags:   CV: WV: TV: Raw:
--------------------------------------------------------------------------------
?    1 Read Error Rate                     POSR--   81  64  44  0
     3 Spin Up Time                        PO----   93  90  AP  00000000000000h
     4 Start/Stop Count                    -O--CK   100 100 20  91
     5 Retired Sectors Count               PO--CK   100 100 10  0
?    7 Seek Error Rate                     POSR--   79  60  45  0
     9 Power On Hours                      -O--CK   87  87  AP  11902
    10 Spin Retry Count                    PO--C-   100 100 97  00000000000000h
    12 Drive Power Cycle Count             -O--CK   100 100 20  88
    18 Head Health Self Assessment         PO-R--   100 100 50  00000000000000h
   187 Reported Un-correctable             -O--CK   100 100 AP  0
   188 Command Timeout                     -O--CK   100 100 AP  0
?  190 Airflow Temperature                 -O---K   67  42  AP  33 (m/M 33/34)
   192 Emergency Retract Count             -O--CK   100 100 AP  57
   193 Load-Unload Count                   -O--CK   99  99  AP  2060
?  194 Temperature                         -O---K   33  58  AP  33 (m/M 18/58)
   197 Pending-Sparing Count               -O--C-   100 100 AP  0
   198 Offline Uncorrectable Sector Count  ----C-   100 100 AP  0
   199 Ultra DMA CRC Error                 -OSRCK   200 200 AP  0
   200 Pressure Measurement Limit          PO---K   100 100 1   00000000000000h
   240 Head Flight Hours                   ------   100 100 AP  11705
   241 Lifetime Writes From Host           ------   100 253 AP  77987243360
   242 Lifetime Reads From Host            ------   100 253 AP  63321318959
```

!!! info
    More details on why this can be a smart thing to do can be found in the following thread:<br/>
    https://www.truenas.com/community/threads/exos-x16-high-head-cycle-count-due-to-toggle-between-epc-idle_a-and-idle_b-power-states.90751/
