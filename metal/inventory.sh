#!/usr/bin/env bash

set -eE
set -o pipefail

script_dir=$(dirname "$(readlink -f "$0")")

INVENTORY=$(mktemp -t ktchn8s_inventoryXXXXXX.yaml)

sops decrypt "${script_dir}/inventory/metal.yml" | yq -y >"${INVENTORY}"

if [ "$1" == "--list" ]; then
  ansible-inventory -i "${INVENTORY}" --list
elif [ "$1" == "--host" ]; then
  ansible-inventory -i "${INVENTORY}" --host "$2"
elif [ "$1" == "--graph" ]; then
  ansible-inventory -i "${INVENTORY}" --graph
else
  printf "Invalid option: use --list, --graph or --host <hostname>\n\n"
  rm -f "${INVENTORY}"
  exit 1
fi

rm -f "${INVENTORY}"
