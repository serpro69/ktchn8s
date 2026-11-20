#!/usr/bin/env bash
# Exercise the production admission checks without Ansible, devices or systemd.
set -euo pipefail
preflight=$(dirname -- "$0")/../metal/roles/storage/files/parity-preflight.sh

systemctl() {
    case "$*" in
        'list-unit-files --no-legend')
            echo 'systemd-journald.service static -'
            case "$scenario" in
                enabled) echo 'snapraid-scrub.timer enabled enabled' ;;
                runtime-mask) echo 'snapraid-scrub.timer masked-runtime enabled' ;;
            esac ;;
        'list-units --all --plain --no-legend')
            case "$scenario" in
                busy) echo 'snapraid-runner.service loaded activating start Sync' ;;
                syncing) echo 'snapraid-initial-sync.service loaded activating start Full sync' ;;
                retry|expand|expand-retry) echo 'snapraid-initial-sync.service loaded active exited Full sync' ;;
            esac ;;
        *) return 1 ;;
    esac
}
lsblk() {
    case "$*" in
        '-dnro TYPE /fixture/candidate') echo part ;;
        '-dnro PKNAME /fixture/candidate') echo mockdisk ;;
        '-nr -o TYPE /dev/mockdisk') printf 'disk\npart\n' ;;
        '-dnro MAJ:MIN /fixture/data') echo 8:1 ;;
        '-dnro MAJ:MIN /fixture/first') echo 8:33 ;;
        '-dnro MAJ:MIN /fixture/second') echo 8:49 ;;
        '-dnro MAJ:MIN /fixture/candidate') echo 8:17 ;;
        *) return 2 ;;
    esac
}
blockdev() {
    if [[ $2 == /fixture/candidate && $scenario == undersized ]]; then
        echo 999
    else
        echo 1000
    fi
}
findmnt() {
    if [[ $* == *--mountpoint* ]]; then
        if [[ $scenario == missing ]]; then return 1; fi
        case "$*" in
            *'/mnt/parity1 '*) echo '8:33 ext4 /' ;;
            *'/mnt/parity2 '*) echo '8:49 ext4 /' ;;
            *) echo '8:1 ext4 /' ;;
        esac
    else
        echo '8:1 /mnt/data1 ext4 /'
        case "$scenario" in
            mounted) echo '8:17 /mnt/parity1 ext4 /' ;;
            fresh-first) ;;
            fresh-first-retry) printf '8:17 /mnt/parity1 ext4 /\n8:49 /mnt/parity2 ext4 /\n' ;;
            fresh-first-foreign) echo '8:49 /mnt/elsewhere ext4 /' ;;
            expand|expand-retry|first-parity-missing|fresh-*) echo '8:33 /mnt/parity1 ext4 /' ;;
            other-mount) echo '8:17 /mnt/sourceB ext4 /' ;;
            omitted) echo '8:33 /mnt/data2 ext4 /' ;;
        esac
    fi
}
blkid() {
    case "$scenario" in
        error) return 2 ;;
        ambiguous) return 8 ;;
        empty) return 0 ;;
        old-label) printf 'TYPE=ext4\nLABEL=source\n' ;;
        other-fs) echo 'TYPE=xfs' ;;
        nested) printf 'PTTYPE=dos\nTYPE=ext4\nLABEL=parity1\n' ;;
        retry|mounted|fresh-first-retry) printf 'TYPE=ext4\nLABEL=parity1\n' ;;
        expand-retry|fresh-retry) printf 'TYPE=ext4\nLABEL=parity2\n' ;;
        *) printf 'PART_ENTRY_SCHEME=gpt\nPART_ENTRY_NUMBER=1\n' ;;
    esac
}
find() {
    if [[ $scenario == fresh-* ]]; then
        case "$scenario:$1" in
            fresh-stale-parity:/mnt/parity1) echo '/mnt/parity1/snapraid.parity' ;;
            fresh-content:/mnt/data1) echo '/mnt/data1/snapraid.content' ;;
            fresh-tmp:/var) echo '/var/snapraid.content.tmp' ;;
            fresh-probe-error:/mnt/parity1) return 1 ;;
        esac
    elif [[ $1 == /mnt/parity1/snapraid.parity ]]; then
        if [[ $scenario != first-parity-missing ]]; then echo 1; fi
    else
        command find "$@"
    fi
}
export -f systemctl lsblk blockdev findmnt blkid find
export scenario
scenarios=(blank retry mounted expand expand-retry first-parity-missing error ambiguous empty old-label other-fs nested
          other-mount omitted busy enabled runtime-mask syncing missing undersized fresh-blank fresh-retry fresh-stale-parity
          fresh-content fresh-tmp fresh-probe-error fresh-wrong-target fresh-no-first fresh-first fresh-first-retry fresh-first-foreign)
for scenario in "${scenarios[@]}"; do
    options=()
    mounts=(/mnt/parity1 /fixture/data /mnt/data1)
    case "$scenario" in
        expand|expand-retry|first-parity-missing|fresh-*) mounts=(/mnt/parity2 /fixture/data /mnt/data1 /fixture/first /mnt/parity1) ;;
    esac
    if [[ $scenario == fresh-* ]]; then options=(--fresh-two-level); fi
    if [[ $scenario == fresh-wrong-target ]]; then mounts[0]=/mnt/parity1; fi
    if [[ $scenario == fresh-no-first ]]; then mounts=(/mnt/parity2 /fixture/data /mnt/data1); fi
    if [[ $scenario == fresh-first* ]]; then mounts=(/mnt/parity1 /fixture/data /mnt/data1 /fixture/second /mnt/parity2); fi
    if result=$(bash "$preflight" "${options[@]}" /fixture/candidate "${mounts[@]}" 2>&1); then
        case "$scenario:$result" in
            blank:blank|retry:ext4|mounted:ext4|expand:blank|expand-retry:ext4|fresh-blank:blank|fresh-retry:ext4|fresh-first:blank|fresh-first-retry:ext4) ;;
            *) echo "Unexpected acceptance: $scenario ($result)" >&2; exit 1 ;;
        esac
    else
        case "$scenario" in
            blank|retry|mounted|expand|expand-retry|fresh-blank|fresh-retry|fresh-first|fresh-first-retry) echo "Unexpected rejection: $scenario ($result)" >&2; exit 1 ;;
        esac
    fi
done
echo "${#scenarios[@]} parity admission cases passed"
