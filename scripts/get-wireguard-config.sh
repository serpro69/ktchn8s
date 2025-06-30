#!/usr/bin/env bash

set -eu
set -o pipefail

PEER="${1}"

export KUBECONFIG=./metal/kubeconfig.yaml

kubectl -n wireguard exec -it deployment/wireguard -- /app/show-peer "${PEER}"
kubectl -n wireguard exec -it deployment/wireguard -- cat "/config/peer_${PEER}/peer_${PEER}.conf"
