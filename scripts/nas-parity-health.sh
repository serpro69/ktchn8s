#!/usr/bin/env bash
# Stream read-only observations to the controller. Arguments are whole-disk WWNs.
set -euo pipefail

(( $# > 0 )) || { echo "Supply the WWNs from the private baseline." >&2; exit 2; }
export LC_ALL=C
seachest_dir=${SEACHEST_DIR:-/root/utils/SeaChestUtilities/Linux/Non-RAID/x86_64}
power_control=$seachest_dir/SeaChest_PowerControl_linux_x86_64
failed=0
observe() {
    local status=0
    "$@" || status=$?
    printf 'Query exit %d: %s\n' "$status" "$*"
    if (( status )); then failed=1; fi
}
date --iso-8601=seconds
hostname
for branch in /mnt/data[0-9]*; do
    findmnt --mountpoint "$branch" --output TARGET,SOURCE,MAJ:MIN,FSTYPE,UUID
done

for wwn in "$@"; do
    [[ $wwn =~ ^0x[[:xdigit:]]{16}$ ]] || { echo "Invalid WWN: $wwn" >&2; exit 2; }
    printf '\nDrive %s\n' "$wwn"
    disk=$(readlink -e "/dev/disk/by-id/wwn-$wwn") || { echo "Missing recorded WWN: $wwn" >&2; exit 1; }
    if [[ ! -b $disk || $(lsblk -dnro TYPE "$disk") != disk || $(lsblk -dnro WWN "$disk") != "$wwn" ]]; then
        echo "Cannot bind $wwn to the expected whole disk." >&2
        exit 1
    fi
    lsblk --bytes --paths --output NAME,MAJ:MIN,TYPE,SIZE,MODEL,SERIAL,WWN,REV,FSTYPE,UUID,MOUNTPOINTS "$disk"
    sg_entries=(/sys/class/block/"${disk##*/}"/device/scsi_generic/sg*)
    if (( ${#sg_entries[@]} != 1 )) || [[ ! -c /dev/${sg_entries[0]##*/} ]]; then
        echo "Missing or ambiguous SCSI generic device for $disk" >&2
        exit 1
    fi
    sg=/dev/${sg_entries[0]##*/}
    observe smartctl -i -H "$disk"
    observe "$seachest_dir/SeaChest_SMART_linux_x86_64" -d "$sg" --smartAttributes hybrid
    observe "$power_control" -d "$sg" --deviceInfo
    observe "$power_control" -d "$sg" --powerBalanceFeature info
    observe "$power_control" -d "$sg" --showEPCSettings
done
if (( failed )); then echo "Incomplete or adverse drive observations. Review the query statuses." >&2; exit 1; fi
echo "Snapshot complete. Compare each drive with the private baseline."
