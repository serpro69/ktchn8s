#!/usr/bin/env bash
# Read-only. Print only "blank" or "ext4" after checking the transition.
set -euo pipefail
export LC_ALL=C
stop() { echo "$*" >&2; exit 1; }

joint=false
if [[ ${1:-} == --fresh-two-level ]]; then joint=true; shift; fi
candidate=$1
target=$2
shift 2
[[ $target == /mnt/parity1 || $target == /mnt/parity2 ]] || stop "Unexpected parity mount $target"
[[ $# -ge 2 && $(( $# % 2 )) == 0 ]] || stop "Expected inventory device and mount pairs"

# systemd 252 returns an error for an empty filtered list-unit-files result.
# Read the system lists successfully before selecting our (possibly absent) units.
unit_files=$(systemctl list-unit-files --no-legend)
while read -r unit state _; do
    case "$unit" in
        snapraid-runner.timer|snapraid-scrub.timer)
            [[ $state == disabled || $state == masked ]] ||
                stop "Disable $unit before configuring parity (state $state)" ;;
    esac
done <<< "$unit_files"
units=$(systemctl list-units --all --plain --no-legend)
while read -r unit _ active substate _; do
    case "$unit" in
        snapraid-initial-sync.service) [[ $active:$substate != active:exited ]] || continue ;;
        snapraid-runner.timer|snapraid-scrub.timer|snapraid-runner.service|snapraid-scrub.service) ;;
        *) continue ;;
    esac
    [[ $active == inactive || $active == failed ]] || stop "Wait for $unit ($active/$substate)"
done <<< "$units"

[[ $(lsblk -dnro TYPE "$candidate") == part ]] || stop "Released device must be a partition"
parent=$(lsblk -dnro PKNAME "$candidate")
[[ -n $parent ]] || stop "Cannot identify the parent disk"
topology=$(lsblk -nr -o TYPE "/dev/$parent")
[[ $topology == $'disk\npart' ]] || stop "Expected one partition on a dedicated parity disk"
capacity=$(blockdev --getsize64 "$candidate")
[[ $capacity =~ ^[1-9][0-9]*$ ]] || stop "Cannot determine parity capacity"

declare -A expected_mounts=() existing_devices=()
content_dirs=(/var)
mounts=$(findmnt -rn -o MAJ:MIN,TARGET,FSTYPE,FSROOT)
while (( $# )); do
    device=$1 mount_path=$2
    shift 2
    expected=$(lsblk -dnro MAJ:MIN "$device")
    [[ -n $expected && $mount_path != "$target" ]] || stop "Invalid peer at $mount_path"
    [[ ! -v existing_devices[$expected] ]] || stop "Repeated backing device at $mount_path"
    existing_devices[$expected]=$mount_path
    expected_mounts[$mount_path]=1
    if [[ $joint == true && $target == /mnt/parity1 && $mount_path == /mnt/parity2 ]]; then
        # On a retry both may already be mounted. On the first pass C is still blank.
        peer=$(awk -v dev="$expected" -v path="$mount_path" '$1 == dev || $2 == path' <<< "$mounts")
        [[ -n $peer ]] || continue
        [[ $peer == "$expected $mount_path ext4 /" ]] || stop 'Conflicting mount for second parity'
    fi
    actual=$(findmnt -rn --mountpoint "$mount_path" -o MAJ:MIN,FSTYPE,FSROOT)
    [[ $actual == "$expected ext4 /" ]] || stop "Incorrect backing mount at $mount_path"
    if [[ $mount_path == /mnt/data* ]]; then
        bytes=$(blockdev --getsize64 "$device")
        [[ $bytes =~ ^[1-9][0-9]*$ && $capacity -ge $bytes ]] || stop "Candidate too small for $mount_path"
        case $mount_path in /mnt/data[123]) content_dirs+=("$mount_path");; esac
    else
        if [[ $joint == true ]]; then
            [[ $mount_path == /mnt/parity1 || $mount_path == /mnt/parity2 ]] || stop "Unexpected parity mount $mount_path"
            entry=$(find "$mount_path" -mindepth 1 -maxdepth 1 ! \( -name lost+found -type d \) -print -quit)
            [[ -z $entry ]] || stop "Fresh parity filesystem already contains $entry"
        else
            [[ $mount_path == /mnt/parity1 ]] || stop "Unexpected existing parity mount: $mount_path"
            first_parity=$(find "$mount_path/snapraid.parity" -maxdepth 0 -type f -size +0c -printf 1)
            [[ $first_parity == 1 ]] || stop "Missing regular, nonempty first parity file at $mount_path"
        fi
    fi
done
if [[ $joint == true ]]; then
    peer=/mnt/parity1
    if [[ $target == /mnt/parity1 ]]; then peer=/mnt/parity2; fi
    [[ -v expected_mounts[$peer] ]] || stop 'Missing peer parity inventory mount'
    # snapraid.conf.j2 stores content on the first three data mounts and /var.
    for dir in "${content_dirs[@]}"; do
        entry=$(find "$dir" -maxdepth 1 -mindepth 1 \( -name snapraid.content -o -name snapraid.content.tmp \) -print -quit)
        [[ -z $entry ]] || stop "Existing SnapRAID state at $entry; inspect before bootstrap"
    done
fi

[[ ! -L $target ]] || stop "Unexpected symlink at $target"
candidate_devno=$(lsblk -dnro MAJ:MIN "$candidate")
[[ -n $candidate_devno && ! -v existing_devices[$candidate_devno] ]] || stop "Candidate overlaps an existing branch"
while read -r devno mount_path kind fsroot; do
    if [[ $mount_path =~ ^/mnt/(data|parity)[0-9]+$ && $mount_path != "$target" && ! -v expected_mounts[$mount_path] ]]; then
        stop "Mounted storage branch missing from the transition inventory: $mount_path"
    fi
    if [[ $devno == "$candidate_devno" || $mount_path == "$target" ]]; then
        [[ $devno == "$candidate_devno" && $mount_path == "$target" && $kind == ext4 && $fsroot == / ]] ||
            stop "Conflicting mount for the released partition or $target"
    fi
done <<< "$mounts"
if [[ -e $target ]] && ! mountpoint -q "$target"; then
    [[ -d $target ]] || stop "Expected a mount directory at $target"
    entry=$(find "$target" -mindepth 1 -maxdepth 1 -print -quit)
    [[ -z $entry ]] || stop "Refusing to cover existing contents of $target"
fi

# An unformatted GPT partition still has PART_ENTRY_* identity. A missing
# device, failed/ambiguous probe or completely empty result cannot authorize mkfs.
signature=$(blkid --probe --output export "$candidate")
if grep -q '^PTTYPE=' <<< "$signature"; then
    stop "Nested partition table on the released partition"
fi
if grep -qx 'TYPE=ext4' <<< "$signature"; then
    grep -Fxq "LABEL=${target##*/}" <<< "$signature" || stop "Ext4 label does not match $target"
    printf 'ext4\n'
else
    grep -qx 'PART_ENTRY_SCHEME=gpt' <<< "$signature" || stop "Missing GPT partition evidence"
    while IFS= read -r field; do
        case $field in DEVNAME=*|PART_ENTRY_*=*) ;; *) stop "Unexpected signature on the released partition: $field" ;; esac
    done <<< "$signature"
    printf 'blank\n'
fi
