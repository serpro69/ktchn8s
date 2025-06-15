.POSIX:
.ONESHELL:
.SHELL := $(shell which bash)
.SHELLFLAGS := -ec
.PHONY: help requirements bootstrap cluster console wake

export KUBECONFIG = $(shell pwd)/kubeconfig.yaml

default: help

help: ## Print this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

~/.ssh/id_ed25519:
	@ssh-keygen -t ed25519 -P '' -f "$@"

_requirements:
	@ansible-galaxy install -f -r requirements.yml

bootstrap: ~/.ssh/id_ed25519 _requirements ## Wake up and provision the servers
	@ansible-playbook \
		--inventory inventory.sh \
		bootstrap.yml \
		-v

cluster: ~/.ssh/id_ed25519 _requirements ## Create kubernetes cluster
	@ansible-playbook \
		--inventory inventory.sh \
		cluster.yml \
		-v

console: ## Start the Ansible console
	@ansible-console \
		--inventory inventory.sh

wake: ~/.ssh/id_ed25519 _requirements ## Wake up the servers without re-provisioning them
	@ansible-playbook \
		--inventory inventory.sh \
		boot.yml \
		--extra-vars "pxe_state=absent" \
		-v

DISK ?= /dev/nvme0n1

wipe: SHELL:=$(shell which bash)
wipe: ~/.ssh/homelab_id_ed25519 _requirements ## Wipe the DISK disk on the SERVER
	@ansible-playbook \
		--inventory inventory.sh \
		wipe.yml \
		--extra-vars "wipe_target=$(SERVER)" \
		--extra-vars "target_disk=$(DISK)" \
		-v
