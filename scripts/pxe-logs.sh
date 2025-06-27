#!/usr/bin/env bash

set -eu
set -o pipefail

docker compose \
  --project-directory ./metal/roles/pxe_server/files/ \
  logs \
  --follow \
  "${@}"
