#!/usr/bin/env bash

docker compose \
  --project-directory ./metal/roles/pxe_server/files/ \
  logs \
  --follow \
  "${@}"
