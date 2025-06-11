#!/bin/bash

echo "===== Stage 4 Verification - From Home Network (Management Machine) ====="

# --- Configuration ---
ROUTER_HOMELAB_IP="10.10.10.1"
ROUTER_HOME_IP="192.168.1.1"
SWITCH_HOMELAB_IP="10.10.10.2"
K8S_CONTROL1_IP="10.10.10.10"
K8S_CONTROL2_IP="10.10.10.11"
K8S_CONTROL3_IP="10.10.10.12"
K8S_WORKER1_IP="10.10.10.20" # Example denied target
K8S_WORKER2_IP="10.10.10.21" # Example denied target
K8S_WORKER3_IP="10.10.10.22" # Example denied target
# K8S_WORKER4_IP="10.10.10.23" # Example denied target
NAS_IP="10.10.10.30"
K8S_INGRESS_IP="10.10.10.50"
INTERNET_IP_TARGET="8.8.8.8"
INTERNET_FQDN_TARGET="google.com"
WLAN_INTERFACE="wlp0s20f3" # Adjust if your WiFi interface is different
ETH_HOMELAB_INTERFACE="enx3ce1a1b82542" # Adjust if your Homelab-connected eth interface is different

SSH_USER="cisco" # User for SSHing to router/switch
K8S_SSH_USER="root" # User for SSHing to K8s nodes/NAS

# --- Helper Function for Ping ---
test_ping() {
    local target_ip="$1"
    local description="$2"
    local source_interface_option="$3" # Optional: e.g., "-I wlan0"

    echo -n "Testing: $description (ping $target_ip $source_interface_option)... "
    if ping -c 3 $source_interface_option "$target_ip" &> /dev/null; then
        echo "SUCCESS"
    else
        echo "FAILURE"
    fi
}

# --- Helper Function for SSH ---
test_ssh() {
    local target_ip="$1"
    local user="$2"
    local description="$3"
    local source_interface_option="$4" # Not directly usable with ssh, assumes routing handles it

    echo -n "Testing: $description (ssh $user@$target_ip)... "
    if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no "$user@$target_ip" exit &> /dev/null; then
        echo "SUCCESS"
    else
        echo "FAILURE"
    fi
}

# --- Helper Function for HTTP/S ---
test_curl() {
    local url="$1"
    local description="$2"

    echo -n "Testing: $description (curl $url)... "
    if curl --head --silent --fail --connect-timeout 5 "$url" &> /dev/null; then
        echo "SUCCESS (connected)"
    else
        echo "FAILURE (or no service listening)"
    fi
}


echo -e "\n--- A1. Router Management & Connectivity (from Home Network via WLAN_INTERFACE: $WLAN_INTERFACE) ---"
test_ping "$ROUTER_HOMELAB_IP" "SSH Target Router Homelab SVI" "-I $WLAN_INTERFACE"
test_ssh "$ROUTER_HOMELAB_IP" "$SSH_USER" "SSH to Router Homelab SVI"
test_ping "$ROUTER_HOME_IP" "SSH Target Router Home SVI" "-I $WLAN_INTERFACE"
test_ssh "$ROUTER_HOME_IP" "$SSH_USER" "SSH to Router Home SVI"
test_ping "$INTERNET_IP_TARGET" "Internet IP" "-I $WLAN_INTERFACE"
test_ping "$INTERNET_FQDN_TARGET" "Internet FQDN (DNS)" "-I $WLAN_INTERFACE"


echo -e "\n--- A2. Access to Homelab (Permitted Traffic from Home Network via WLAN_INTERFACE: $WLAN_INTERFACE) ---"
test_ping "$K8S_CONTROL1_IP" "K8s Control 1" "-I $WLAN_INTERFACE"
test_ping "$NAS_IP" "NAS" "-I $WLAN_INTERFACE"
test_ssh "$K8S_CONTROL1_IP" "$K8S_SSH_USER" "SSH to K8s Control 1"
test_ssh "$K8S_CONTROL2_IP" "$K8S_SSH_USER" "SSH to K8s Control 2"
test_ssh "$K8S_CONTROL3_IP" "$K8S_SSH_USER" "SSH to K8s Control 3"
test_ssh "$NAS_IP" "$K8S_SSH_USER" "SSH to NAS"
test_curl "http://$K8S_INGRESS_IP" "HTTP to K8s Ingress"
test_curl "https://$K8S_INGRESS_IP" "HTTPS to K8s Ingress (may show cert error)"


echo -e "\n--- A3. Access to Homelab (Denied Traffic from Home Network via WLAN_INTERFACE: $WLAN_INTERFACE) ---"
echo -n "Testing: SSH to K8s Worker 1 (SHOULD FAIL)... "
if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no "$K8S_SSH_USER@$K8S_WORKER1_IP" exit &> /dev/null; then
    echo "FAILURE (UNEXPECTEDLY ALLOWED)"
else
    echo "SUCCESS (DENIED AS EXPECTED)"
fi
# Add more denied tests if needed

echo -e "\n===== Verification Complete ====="
echo "NOTE: Check router logs ('show logging') for ACL deny messages for failed expected connections."
echo "NOTE: Check 'show access-lists <ACL_NAME>' on router for hit counts."
# SMB test is harder to automate in a simple script, manual check recommended
echo "NOTE: Run a manual test to verify access to NAS SMB share (\\\\$NAS_IP\\ or smb://$NAS_IP)"
