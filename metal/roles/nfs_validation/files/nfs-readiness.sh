#!/bin/sh
# Run as the real writer identity through one NFS mount of the scratch subtree.
set -eu
export LC_ALL=C
test "$(id -u)" = 1000
test "$(id -g)" = 1000
cd "$2"
case "$1" in
  create)
    mkdir -p downloads/nested library
    printf 'nfs-readiness payload\n' > downloads/nested/payload
    ln downloads/nested/payload library/imported
    ;;
  promote)
    mv library/imported library/promoted
    ;;
  read)
    printf 'nfs-readiness payload\n' | cmp - downloads/nested/payload
    printf 'nfs-readiness payload\n' | cmp - library/promoted
    # NFS can cache the pre-link attributes (even for the newly linked name).
    # Require the count after normal cache expiry, without dropping caches or
    # changing production mount options. Stat/read errors still fail immediately.
    attempt=0
    links=$(stat -c %h downloads/nested/payload)
    while test "$links" != 2; do
      attempt=$((attempt + 1))
      if test "$attempt" -gt 65; then
        echo "Expected two links after cache expiry; found $links" >&2
        exit 1
      fi
      sleep 1
      links=$(stat -c %h downloads/nested/payload)
    done
    ;;
  delete)
    rm library/promoted downloads/nested/payload
    rmdir downloads/nested downloads library
    ;;
  readonly)
    if result=$(touch readonly-probe 2>&1); then
      rm readonly-probe
      echo 'Read-only mount allowed a write' >&2
      exit 1
    fi
    printf '%s\n' "$result" | grep -q 'Read-only file system'
    ;;
  *) echo 'Unknown probe action' >&2; exit 2 ;;
esac
printf 'NFS readiness %s passed\n' "$1"
