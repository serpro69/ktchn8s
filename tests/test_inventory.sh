#!/usr/bin/env bash
# Run inside the project dev shell: bash tests/test_inventory.sh
# Exercise the actual wrapper with synthetic SOPS output and real Ansible.
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
fixtures="$repo_root/tests/fixtures/inventory-yaml"
for tool in ansible-inventory ansible-playbook jq; do
  command -v "$tool" >/dev/null || {
    printf 'Missing test dependency: %s\n' "$tool" >&2
    exit 1
  }
done

test_root=$(mktemp -d)
trap 'rm -rf -- "$test_root"' EXIT
mkdir "$test_root/inventory" "$test_root/tmp"
cp "$repo_root/metal/inventory.sh" "$test_root/inventory.sh"
cp "$fixtures/data.yml" "$test_root/inventory/metal.yml"
export PATH="$fixtures/bin:$PATH"
export ANSIBLE_CONFIG="$fixtures/ansible.cfg" ANSIBLE_NOCOLOR=1
export ANSIBLE_HOME="$test_root/ansible-home"
export ANSIBLE_LOCAL_TEMP="$test_root/ansible-tmp"
export TMPDIR="$test_root/tmp"
test "$(command -v sops)" = "$fixtures/bin/sops"
test "$(command -v yq)" = "$fixtures/bin/yq"
cd "$test_root"

output=$(bash ./inventory.sh --list)
printf '%s\n' "$output" | jq -e '
  .nas.hosts == ["fixture-nas"] and
  ._meta.hostvars["fixture-nas"].ansible_user == "fixture-user" and
  ._meta.hostvars["fixture-nas"].data_drives[0].id == "fixture-part1" and
  ._meta.hostvars["fixture-nas"].parity_drives == []' >/dev/null
printf '%s\n' 'PASS: --list preserves host/group/drive data'

output=$(bash ./inventory.sh --host fixture-nas)
printf '%s\n' "$output" | jq -e '
  .ansible_user == "fixture-user" and .network_interface == "fixture0" and
  .data_drives[0].id == "fixture-part1" and .parity_drives == []' >/dev/null
printf '%s\n' 'PASS: --host preserves host variables'

output=$(bash ./inventory.sh --graph)
printf '%s\n' "$output" | grep -q '@nas:'
printf '%s\n' "$output" | grep -q 'fixture-nas'
printf '%s\n' 'PASS: --graph resolves NAS membership'

output=$(ansible-playbook -i ./inventory.sh "$fixtures/play.yml" \
  --limit fixture-nas --list-hosts)
printf '%s\n' "$output" | grep -q 'hosts (1):'
printf '%s\n' "$output" | grep -q 'fixture-nas'
printf '%s\n' 'PASS: script plugin selects the one fixture host'

test -z "$(find "$TMPDIR" -maxdepth 1 -type f -name 'ktchn8s_inventory*.yaml')"
printf '%s\n' 'PASS: no temporary inventory remains'
