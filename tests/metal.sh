#!/usr/bin/env bash

# Stage 5 Verification Script
# Ensure KUBECONFIG is set: export KUBECONFIG=$(pwd)/kubeconfig.yaml

KUBECONFIG=$(pwd)/metal/kubeconfig.yaml
export KUBECONFIG

# Variables (Customize if needed)
VIP_CONTROL_PLANE_ENDPOINT="10.10.10.100" # Your K8s API VIP
NGINX_DEPLOYMENT_NAME="nginx-deployment"
NGINX_CLUSTERIP_SERVICE_NAME="nginx-clusterip-service"
NGINX_LOADBALANCER_SERVICE_NAME="nginx-loadbalancer"
EXPECTED_NGINX_LB_IP="10.10.10.40" # The IP you saw assigned
#PIHOLE_DNS_LB_IP="10.10.10.41"     # For later, if Pi-hole is up

#TEST_DOMAIN_FOR_DNS_FROM_HOME="google.com"     # External domain to test DNS resolution
HOME_NETWORK_SOURCE_IP_FOR_CURL="192.168.1.15" # Your laptop's IP on Home network

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# --- Helper Functions ---
print_step() {
  echo -e "\n${YELLOW}===== $1 =====${NC}"
}

print_sub_step() {
  echo -e "\n--- $1 ---"
}

check_success() {
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}SUCCESS${NC}"
    return 0
  else
    echo -e "${RED}FAILURE${NC}"
    return 1
  fi
}

check_output_contains() {
  local output="$1"
  local pattern="$2"
  local success_msg="$3"
  local failure_msg="$4"

  if echo "$output" | grep -q -i "$pattern"; then
    echo -e "${GREEN}${success_msg}${NC}"
    return 0
  else
    echo -e "${RED}${failure_msg}${NC}"
    echo "Output was:"
    echo "$output"
    return 1
  fi
}

# --- Main Script ---
if [ -z "$KUBECONFIG" ] || [ ! -f "$KUBECONFIG" ]; then
  echo -e "${RED}ERROR: KUBECONFIG environment variable not set or kubeconfig file not found.${NC}"
  echo "Please run: export KUBECONFIG=\$(pwd)/metal/kubeconfig.yaml"
  exit 1
fi
echo "Using KUBECONFIG: $KUBECONFIG"

# --- A. Verify Kubernetes Cluster Health & Basic Functionality ---
print_step "A. Verify Kubernetes Cluster Health & Basic Functionality"

print_sub_step "A0: Wait for Nodes to be Ready"
kubectl wait --for=condition=Ready nodes --all --timeout=300s

print_sub_step "A1: Check Node Details"
kubectl get nodes -o wide
# Manual verification: Check all nodes are Ready, roles, IPs, versions.

print_sub_step "A2: Verify Kube-VIP Functionality (Control Plane Endpoint)"
echo "Pinging VIP $VIP_CONTROL_PLANE_ENDPOINT..."
ping -c 4 "$VIP_CONTROL_PLANE_ENDPOINT"
check_success || echo -e "${RED}VIP Ping failed. Kube-VIP might not be working.${NC}"

echo "Extracting client certs from KUBECONFIG for authenticated curl..."
CLIENT_CERT_FILE=$(mktemp client.XXXXXX.crt)
CLIENT_KEY_FILE=$(mktemp client.XXXXXX.key)
CA_CERT_FILE=$(mktemp ca.XXXXXX.crt)

if ! kubectl config view --raw -o jsonpath='{.users[?(@.name=="default")].user.client-certificate-data}' | base64 --decode >"$CLIENT_CERT_FILE"; then
  echo -e "${RED}Failed to extract client certificate.${NC}"
  exit 1
fi
if ! kubectl config view --raw -o jsonpath='{.users[?(@.name=="default")].user.client-key-data}' | base64 --decode >"$CLIENT_KEY_FILE"; then
  echo -e "${RED}Failed to extract client key.${NC}"
  exit 1
fi
if ! kubectl config view --raw -o jsonpath='{.clusters[?(@.name=="default")].cluster.certificate-authority-data}' | base64 --decode >"$CA_CERT_FILE"; then
  echo -e "${RED}Failed to extract CA certificate.${NC}"
  exit 1
fi

echo "Testing /readyz endpoint on VIP $VIP_CONTROL_PLANE_ENDPOINT with authentication..."
CURL_READYZ_OUTPUT=$(curl --silent --cacert "$CA_CERT_FILE" --cert "$CLIENT_CERT_FILE" --key "$CLIENT_KEY_FILE" "https://$VIP_CONTROL_PLANE_ENDPOINT:6443/readyz")
check_output_contains "$CURL_READYZ_OUTPUT" "ok" "/readyz responded 'ok'" "/readyz did NOT respond 'ok'"

rm -f "$CLIENT_CERT_FILE" "$CLIENT_KEY_FILE" "$CA_CERT_FILE"

# --- B. Verify Cilium CNI Installation and Functionality ---
print_step "B. Verify Cilium CNI Installation and Functionality"

print_sub_step "B1: Check Cilium Agent Pods"
kubectl get pods -n kube-system -l k8s-app=cilium -o wide
# Manual verification: All pods Running 1/1.

print_sub_step "B2: Check Cilium Operator Pods"
kubectl get pods -n kube-system -l io.cilium/app=operator -o wide
# Manual verification: Operator pod(s) Running and Ready.

print_sub_step "B3: Run Cilium Status Check"
CILIUM_POD_NAME=$(kubectl get pods -n kube-system -l k8s-app=cilium -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$CILIUM_POD_NAME" ]; then
  echo -e "${RED}Could not find a Cilium agent pod to exec into.${NC}"
else
  echo "Using Cilium pod: $CILIUM_POD_NAME for status check..."
  kubectl exec -it -n kube-system "$CILIUM_POD_NAME" -- cilium status --verbose
  # Manual verification: Check for "Ok" status, KubeProxyReplacement: True, no major errors.
fi

print_sub_step "B4: Verify Pod Network Connectivity (Nginx Test)"
echo "Applying Nginx test deployment and ClusterIP service..."
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $NGINX_DEPLOYMENT_NAME
  labels:
    app: nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: $NGINX_CLUSTERIP_SERVICE_NAME
spec:
  selector:
    app: nginx
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
EOF
check_success || echo -e "${RED}Failed to apply Nginx test manifests.${NC}"

echo "Waiting for Nginx pods to be ready (max 2 minutes)..."
if ! kubectl wait --for=condition=ready pod -l app=nginx --timeout=120s &>/dev/null; then
  echo -e "${RED}Nginx pods did not become ready in time.${NC}"
  kubectl get pods -l app=nginx -o wide
else
  echo -e "${GREEN}Nginx pods are ready.${NC}"
  kubectl get pods -l app=nginx -o wide
  NGINX_POD1_NAME_TEST=$(kubectl get pods -l app=nginx -o jsonpath='{.items[0].metadata.name}')
  NGINX_POD2_IP_TEST=$(kubectl get pods -l app=nginx -o jsonpath='{.items[1].status.podIP}')
  NGINX_SVC_IP_TEST=$(kubectl get svc $NGINX_CLUSTERIP_SERVICE_NAME -o jsonpath='{.spec.clusterIP}')

  echo "Nginx Pod 1 ($NGINX_POD1_NAME_TEST)"
  echo "Nginx Pod 2 IP: $NGINX_POD2_IP_TEST"
  echo "Nginx Service ClusterIP: $NGINX_SVC_IP_TEST"

  echo "Testing connection from $NGINX_POD1_NAME_TEST to Pod 2 ($NGINX_POD2_IP_TEST)..."
  CURL_POD_TO_POD_OUT=$(kubectl exec -it "$NGINX_POD1_NAME_TEST" -- curl -s --connect-timeout 5 "http://$NGINX_POD2_IP_TEST")
  check_output_contains "$CURL_POD_TO_POD_OUT" "Welcome to nginx" "Pod-to-Pod IP: SUCCESS" "Pod-to-Pod IP: FAILURE"

  echo "Testing connection from $NGINX_POD1_NAME_TEST to Nginx ClusterIP ($NGINX_SVC_IP_TEST)..."
  CURL_POD_TO_SVC_IP_OUT=$(kubectl exec -it "$NGINX_POD1_NAME_TEST" -- curl -s --connect-timeout 5 "http://$NGINX_SVC_IP_TEST")
  check_output_contains "$CURL_POD_TO_SVC_IP_OUT" "Welcome to nginx" "Pod-to-Service IP: SUCCESS" "Pod-to-Service IP: FAILURE"

  echo "Testing connection from $NGINX_POD1_NAME_TEST to Nginx Service Name ($NGINX_CLUSTERIP_SERVICE_NAME)..."
  CURL_POD_TO_SVC_NAME_OUT=$(kubectl exec -it "$NGINX_POD1_NAME_TEST" -- curl -s --connect-timeout 5 "http://$NGINX_CLUSTERIP_SERVICE_NAME")
  check_output_contains "$CURL_POD_TO_SVC_NAME_OUT" "Welcome to nginx" "Pod-to-Service Name (DNS): SUCCESS" "Pod-to-Service Name (DNS): FAILURE"
fi

print_sub_step "B5: Verify Kube-Proxy Replacement"
echo "Checking for kube-proxy pods (should be none)..."
KUBE_PROXY_PODS=$(kubectl get pods -n kube-system -l k8s-app=kube-proxy --no-headers 2>/dev/null | wc -l)
if [ "$KUBE_PROXY_PODS" -eq 0 ]; then
  echo -e "${GREEN}SUCCESS: No kube-proxy pods found as expected.${NC}"
else
  echo -e "${RED}FAILURE: Found $KUBE_PROXY_PODS kube-proxy pod(s). Check K3s and Cilium config.${NC}"
  kubectl get pods -n kube-system -l k8s-app=kube-proxy
fi

# --- C. Verify Cilium LoadBalancer Functionality ---
print_step "C. Verify Cilium LoadBalancer Functionality"

print_sub_step "C1: Check CiliumLoadBalancerIPPool"
kubectl get ciliumloadbalancerippools.cilium.io
kubectl get ciliumloadbalancerippools.cilium.io default -o yaml # Assuming pool name is 'default'
# Manual verification: Pool exists, covers desired IPs, no conflicts.

print_sub_step "C2 & C3: Deploy Nginx LoadBalancer service and check External IP"
echo "Applying Nginx LoadBalancer service..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: $NGINX_LOADBALANCER_SERVICE_NAME
spec:
  type: LoadBalancer
  ports:
  - port: 80
    protocol: TCP
    targetPort: 80
  selector:
    app: nginx
EOF
check_success || echo -e "${RED}Failed to apply Nginx LoadBalancer service manifest.${NC}"

echo "Waiting for Nginx LoadBalancer service to get an External IP (max 1 minute)..."
NGINX_LB_EXTERNAL_IP=""
for _ in {1..12}; do
  NGINX_LB_EXTERNAL_IP=$(kubectl get svc $NGINX_LOADBALANCER_SERVICE_NAME -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
  if [ -n "$NGINX_LB_EXTERNAL_IP" ] && [ "$NGINX_LB_EXTERNAL_IP" != "<pending>" ]; then
    echo -e "${GREEN}Nginx LoadBalancer External IP: $NGINX_LB_EXTERNAL_IP${NC}"
    break
  fi
  sleep 5
done

if [ -z "$NGINX_LB_EXTERNAL_IP" ] || [ "$NGINX_LB_EXTERNAL_IP" == "<pending>" ]; then
  echo -e "${RED}FAILURE: Nginx LoadBalancer service did not get an External IP.${NC}"
  kubectl get svc $NGINX_LOADBALANCER_SERVICE_NAME
else
  # Compare with the IP you noted earlier
  if [ "$NGINX_LB_EXTERNAL_IP" == "$EXPECTED_NGINX_LB_IP" ]; then
    echo -e "${GREEN}SUCCESS: External IP matches expected $EXPECTED_NGINX_LB_IP.${NC}"
  else
    echo -e "${YELLOW}WARNING: External IP is $NGINX_LB_EXTERNAL_IP, expected $EXPECTED_NGINX_LB_IP. Still proceeding with test.${NC}"
    # Update EXPECTED_NGINX_LB_IP for subsequent tests if the assigned one is different but valid
    EXPECTED_NGINX_LB_IP="$NGINX_LB_EXTERNAL_IP"
  fi

  print_sub_step "C4: Test access to Nginx LoadBalancer IP ($EXPECTED_NGINX_LB_IP) from Home Network"
  echo "Attempting curl to http://$EXPECTED_NGINX_LB_IP from source IP $HOME_NETWORK_SOURCE_IP_FOR_CURL (or default route)..."
  # Note: Forcing source IP with curl is complex and often not needed if routing is correct.
  # This test relies on the machine running the script being on the Home Network OR having a route.
  CURL_LB_OUTPUT=$(curl -s --connect-timeout 10 "http://$EXPECTED_NGINX_LB_IP")
  check_output_contains "$CURL_LB_OUTPUT" "Welcome to nginx" "Access to Nginx LoadBalancer: SUCCESS" "Access to Nginx LoadBalancer: FAILURE"
fi

# --- Cleanup Nginx Test Resources ---
print_step "Cleaning up Nginx test resources"
kubectl delete service $NGINX_CLUSTERIP_SERVICE_NAME --ignore-not-found=true
kubectl delete service $NGINX_LOADBALANCER_SERVICE_NAME --ignore-not-found=true
kubectl delete deployment $NGINX_DEPLOYMENT_NAME --ignore-not-found=true

echo -e "\n${YELLOW}===== Stage 5 Verification (Pre-Pi-hole) Script Complete =====${NC}"
echo "Manual checks for detailed output and ACL logs/counters are still recommended."
