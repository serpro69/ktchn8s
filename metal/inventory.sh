#!/usr/bin/env bash

set -eE
set -o pipefail

script_dir=$(dirname "$(readlink -f "$0")")

INVENTORY=$(mktemp -t ktchn8s_inventoryXXXXXX.yaml)
trap 'rm -f -- "$INVENTORY"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

sops decrypt --output-type yaml "${script_dir}/inventory/metal.yml" >"${INVENTORY}"

if [ "$1" == "--list" ]; then
  ansible-inventory -i "${INVENTORY}" --list
elif [ "$1" == "--host" ]; then
  ansible-inventory -i "${INVENTORY}" --host "$2"
elif [ "$1" == "--graph" ]; then
  ansible-inventory -i "${INVENTORY}" --graph
else
  printf "Invalid option: use --list, --graph or --host <hostname>\n\n"
  exit 1
fi
