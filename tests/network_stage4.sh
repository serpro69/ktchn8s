#!/bin/bash

set -euE
# set -x
set -o pipefail

# -- colors sequences for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

pass() {
  local msg="${1:-}"
  if [ -z "$msg" ]; then
    printf "%bSUCCESS%b\n" "${GREEN}" "${NC}"
    return
  else
    printf "%bSUCCESS%b %s\n" "${GREEN}" "${NC}" "$msg"
    return
  fi
}

fail() {
  local msg="${1:-}"
  if [ -z "$msg" ]; then
    printf "%bFAILURE%b\n" "${RED}" "${NC}"
    return
  else
    printf "%bFAILURE%b %s\n" "${RED}" "${NC}" "$msg"
    return
  fi
}

# --- Configuration ---
ROUTER_HOMELAB_IP="10.10.10.1"
ROUTER_HOME_IP="192.168.1.1"
SWITCH_HOMELAB_IP="10.10.10.2"
K8S_CONTROL1_IP="10.10.10.10"
K8S_CONTROL2_IP="10.10.10.11"
K8S_CONTROL3_IP="10.10.10.12"
K8S_WORKER1_IP="10.10.10.20"
K8S_WORKER2_IP="10.10.10.21"
K8S_WORKER3_IP="10.10.10.22"
K8S_WORKER4_IP="10.10.10.22" # FIX: this should actually end with 23, but the server is used to simulate the nas
K8S_WORKER5_IP="10.10.10.24"
K8S_WORKER6_IP="10.10.10.25"
K8S_WORKER7_IP="10.10.10.26"
NAS_IP="10.10.10.30"
K8S_INGRESS_IP="10.10.10.50"
INTERNET_IP_TARGET="8.8.8.8"
INTERNET_FQDN_TARGET="google.com"
WLAN_INTERFACE="wlp0s20f3"              # Adjust if your WiFi interface is different
ETH_HOMELAB_INTERFACE="enx3ce1a1b82542" # Adjust if your Homelab-connected eth interface is different

K8S_NODES=(
  "$K8S_CONTROL1_IP"
  "$K8S_CONTROL2_IP"
  "$K8S_CONTROL3_IP"
  "$K8S_WORKER1_IP"
  "$K8S_WORKER2_IP"
  "$K8S_WORKER3_IP"
  "$K8S_WORKER4_IP"
  "$K8S_WORKER5_IP"
  "$K8S_WORKER6_IP"
  "$K8S_WORKER7_IP"
  "$NAS_IP"
)

INTERFACES=(
  "$WLAN_INTERFACE"
  "$ETH_HOMELAB_INTERFACE"
)

K8S_SSH_USER="root" # User for SSHing to K8s nodes/NAS

# --- Helper Function for Ping ---
test_ping() {
  local target_ip="$1"
  local description="$2"
  local source_interface_option="$3" # Optional: e.g., "wlan0"

  printf "Testing: %s (ping -I %s %s)... " "$description" "$source_interface_option" "$target_ip"
  if ping -c 3 -I "$source_interface_option" "$target_ip" &>/dev/null; then
    pass
  else
    fail
  fi
}

# --- Helper Function for SSH ---
test_ssh() {
  local target_ip="$1"
  local user="$2"
  local description="$3"

  printf "Testing: %s (ssh %s@%s)... " "$description" "$user" "$target_ip"
  if ssh -o ConnectTimeout=10 -o BatchMode=yes "$user@$target_ip" exit &>/dev/null; then
    pass
  else
    fail
  fi
}

test_telnet() {
  local target_ip="$1"
  local target_port="$2"
  local description="$3"

  printf "Testing: %s (telnet %s %s)... " "$description" "$target_ip" "$target_port"
  if echo -e '\x1dclose\x0d' | telnet "$target_ip" "$target_port" &>/dev/null; then
    pass
  else
    fail
  fi
}

# --- Helper Function for HTTP/S ---
test_curl() {
  local url="$1"
  local description="$2"

  printf "Testing: %s (curl %s)... " "$description" "$url"
  if curl --head --silent --fail --connect-timeout 5 "$url" &>/dev/null; then
    pass " (connected)"
  else
    fail " (or no service listening)"
  fi
}

printf "\n%b===== Stage 4 Verification - From Management Machine =====%b\n" "$YELLOW" "$NC"

printf "\n%b=== Check pre-requisites ===%b\n" "$CYAN" "$NC"
WLAN_IP=$(ifconfig "${WLAN_INTERFACE}" | grep inet | grep -v inet6 | xargs | awk '$1 == "inet" {print $2}')
ETH_IP=$(ifconfig "${ETH_HOMELAB_INTERFACE}" | grep inet | grep -v inet6 | xargs | awk '$1 == "inet" {print $2}')
if [ -z "$WLAN_IP" ]; then
  fail "ERROR: WLAN interface $WLAN_INTERFACE not found or no IPv4 assigned."
  exit 1
elif [ -z "$ETH_IP" ]; then
  fail "ERROR: Ethernet interface $ETH_HOMELAB_INTERFACE not found or no IPv4 assigned."
  exit 1
else
  pass
fi

run_tests() {
  local interface="$1"
  printf "\n%b=== Running tests on interface: $interface ===%b\n" "$CYAN" "$NC"

  printf "\n%b--- A1. Router/Switch Management & Connectivity (via interface: $interface) ---%b\n" "$BLUE" "$NC"
  test_ping "$ROUTER_HOMELAB_IP" "SSH Target Router Homelab SVI" "$interface"
  test_telnet "$ROUTER_HOMELAB_IP" "22" "Telnet to Router Homelab SVI"
  test_ping "$ROUTER_HOME_IP" "SSH Target Router Home SVI" "$interface"
  test_telnet "$ROUTER_HOME_IP" "22" "Telnet to Router Home SVI"
  test_ping "$SWITCH_HOMELAB_IP" "SSH Target Switch Homelab SVI" "$interface"
  test_telnet "$SWITCH_HOMELAB_IP" "22" "Telnet to Switch Homelab SVI"
  test_ping "$INTERNET_IP_TARGET" "Internet IP" "$interface"
  test_ping "$INTERNET_FQDN_TARGET" "Internet FQDN (DNS)" "$interface"

  printf "\n%b--- A2. Access to Homelab (Permitted Traffic via interface: $interface) ---%b\n" "$BLUE" "$NC"
  for node in "${K8S_NODES[@]}"; do
    test_ping "$node" "K8s Node $node" "$interface"
    test_ssh "$node" "$K8S_SSH_USER" "SSH to K8s Node $node"
  done

  test_curl "http://$K8S_INGRESS_IP" "HTTP to K8s Ingress"
  test_curl "https://$K8S_INGRESS_IP" "HTTPS to K8s Ingress (may show cert error)"

  printf "\n%b--- A3. Access to Homelab (Denied Traffic via interface: $interface) ---%b\n" "$BLUE" "$NC"
  # TODO: Add some denied tests if needed
}

for iface in "${INTERFACES[@]}"; do
  if ! ifconfig "$iface" &>/dev/null; then
    fail "ERROR: Interface $iface not found."
    exit 1
  fi
  run_tests "$iface"
done

printf "\n===== Verification Complete =====\n"
printf "NOTE: Check router logs ('show logging') for ACL deny messages for failed expected connections.\n"
printf "NOTE: Check 'show access-lists <ACL_NAME>' on router for hit counts.\n"
# SMB test is harder to automate in a simple script, manual check recommended
# shellcheck disable=SC2028
printf 'NOTE: Run a manual test to verify access to NAS SMB share (\\\\%s\\ or smb://%s)\n' "$NAS_IP" "$NAS_IP"
