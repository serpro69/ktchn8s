#!/usr/bin/env bash
# Local synthetic hardlinks only: no mounts, inventory, host or Kubernetes calls.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
probe="$repo/metal/roles/storage/files/nfs-readiness-backing.sh"
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
branches=("$scratch/branch one" "$scratch/branch two")
for branch in "${branches[@]}"; do
  mkdir -p "$branch/99_tmp/nfs-readiness/"{downloads/nested,library}
done
original="${branches[0]}/99_tmp/nfs-readiness/downloads/nested/payload"
promoted="${branches[0]}/99_tmp/nfs-readiness/library/promoted"
expect_failure() {
  if sh "$probe" "${branches[@]}" > "$scratch/result"; then
    printf 'Unexpected backing-check success: %s\n' "$1" >&2
    exit 1
  fi
}
expect_failure 'missing fixture'
printf 'synthetic bytes\n' > "$original"
cp "$original" "$promoted"
expect_failure 'equal bytes but separate inodes'
rm "$promoted"
ln "$original" "$promoted"
sh "$probe" "${branches[@]}" > "$scratch/result"
test "$(wc -l < "$scratch/result")" -eq 1
ln "$original" "$scratch/third-link"
expect_failure 'unexpected third hardlink'
rm "$scratch/third-link"
other="${branches[1]}/99_tmp/nfs-readiness/library/promoted"
printf 'orphaned promoted entry\n' > "$other"
expect_failure 'orphaned counterpart on another branch'
rm "$other"
cp "$original" "${branches[1]}/99_tmp/nfs-readiness/downloads/nested/payload"
ln "${branches[1]}/99_tmp/nfs-readiness/downloads/nested/payload" "$other"
expect_failure 'duplicate backing pair'
rm "$other" "${branches[1]}/99_tmp/nfs-readiness/downloads/nested/payload"
rm "$promoted"
ln -s "$original" "$promoted"
expect_failure 'symlink substituted for a hardlink'
printf 'Backing identity regression: seven cases passed\n'
