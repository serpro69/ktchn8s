#!/bin/sh
# Called only for the owned synthetic fixture, with the configured data branches.
set -eu
export LC_ALL=C
found=0
for branch do
  original="$branch/99_tmp/nfs-readiness/downloads/nested/payload"
  promoted="$branch/99_tmp/nfs-readiness/library/promoted"
  if test -e "$original" || test -L "$original" || test -e "$promoted" || test -L "$promoted"; then
    test ! -L "$original"
    test ! -L "$promoted"
    test -f "$original"
    test -f "$promoted"
    original_inode=$(stat -c %d:%i "$original")
    promoted_inode=$(stat -c %d:%i "$promoted")
    test "$original_inode" = "$promoted_inode"
    test "$(stat -c %h "$original")" = 2
    printf '%s %s\n' "$branch" "$original_inode"
    found=$((found + 1))
  fi
done
test "$found" = 1
