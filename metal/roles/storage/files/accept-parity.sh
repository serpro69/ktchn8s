#!/usr/bin/env bash
# Explicit operator action for a frozen dataset. Leave pending state on any failure.
set -euo pipefail
export LC_ALL=C
umask 077
exec 9>/run/snapraid-accept.lock
flock -n 9 || { echo 'Another parity acceptance is running' >&2; exit 1; }

pending=/var/lib/snapraid-layout.pending
bin=/usr/local/bin/snapraid
unit=snapraid-initial-sync.service
evidence=$(mktemp -d /var/log/snapraid/accept-XXXXXXXX)
echo "Parity acceptance evidence: $evidence"
sha256sum "$pending" /etc/snapraid.conf > "$evidence/inputs"
verify_layout() {
    sha256sum --check "$evidence/inputs"
    /usr/local/libexec/storage-parity-idle --idle
    python3 - "$pending" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
record = json.loads(Path(sys.argv[1]).read_text())
if not record or not record["branches"]:
    sys.exit("Run ordinary storage provisioning with maintenance paused before acceptance")
if hashlib.sha256(Path("/etc/snapraid.conf").read_bytes()).hexdigest() != record["config_sha256"]:
    sys.exit("Deployed SnapRAID configuration differs from the pending layout")
for device, partition_id, target in record["branches"]:
    def read(*cmd):
        return subprocess.check_output(cmd, text=True).strip()
    number = read("lsblk", "-dnro", "MAJ:MIN", device)
    if (not number or read("findmnt", "-rn", "-M", target, "-o", "MAJ:MIN,FSTYPE,FSROOT") != number + " ext4 /"
            or read("blkid", "-p", "-s", "PART_ENTRY_UUID", "-o", "value", device) != partition_id):
        sys.exit(f"{target}: backing identity changed")
PY
}

verify_layout
previous=$(systemctl show "$unit" -p InvocationID --value)
systemctl restart "$unit"
current=$(systemctl show "$unit" -p InvocationID --value)
systemctl show "$unit" -p InvocationID -p SubState -p Result -p ExecMainStatus > "$evidence/sync"
[[ $current =~ ^[[:xdigit:]]{32}$ && $current != "$previous" ]]
grep -Fxq SubState=exited "$evidence/sync"
grep -Fxq Result=success "$evidence/sync"
grep -Fxq ExecMainStatus=0 "$evidence/sync"
verify_layout
"$bin" -c /etc/snapraid.conf diff > "$evidence/diff-before"
"$bin" -c /etc/snapraid.conf -l "$evidence/scrub.log" scrub -p full | tee "$evidence/scrub.out"
grep -Eq '(^|[[:space:]])100% completed,' "$evidence/scrub.out"
for check in error_file:0 error_io:0 error_data:0 exit:ok; do
    grep -Fxq "summary:$check" "$evidence/scrub.log"
done
verify_layout
"$bin" -c /etc/snapraid.conf diff > "$evidence/diff-after"
"$bin" -c /etc/snapraid.conf -l "$evidence/status.log" status
for check in has_unsynced:0 has_unscrubbed:0; do
    grep -Fxq "summary:$check" "$evidence/status.log"
done
grep -Eq '^summary:has_bad:0:' "$evidence/status.log"
grep -Eq '^summary:parity_block_count:[1-9][0-9]*$' "$evidence/status.log"
verify_layout
mv -T "$pending" /var/lib/snapraid-layout.accepted
echo 'Parity accepted. Apply the chosen maintenance policy.'
