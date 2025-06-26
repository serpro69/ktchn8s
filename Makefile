.POSIX:
.ONESHELL:
.SHELL := $(shell which bash)
.SHELLFLAGS := -ec
.PHONY: *
.EXPORT_ALL_VARIABLES:

KUBECONFIG = $(shell pwd)/metal/kubeconfig.yaml
KUBE_CONFIG_PATH = $(KUBECONFIG)

default: help

# metal

console: ## Start the Ansible console
	@make -C metal console

inventory: ## List hosts from the ansible inventory
	@make -C metal inventory

metal: ## Provision baremetal servers and create a kubernetes cluster
	@make -C metal main

wake: ## Wake up the servers without re-provisioning them
	@make -C metal wake

# system

system: ## Provision system resources on the kubernetes cluster
	@make -C system main

# misc

docs: ## Serve documentation on localhost
	@mkdocs serve

help: ## Print this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

run: ## Run a CMD command on all servers via SSH
	@cmd=$(CMD); \
	if [ -z "$${cmd}" ]; then \
		echo "Set CMD variable to the command you want to run on each host"; \
		exit 1; \
	fi; \
	hosts=$$(ansible-inventory -i metal/inventory.sh --list | jq -r '._meta.hostvars | keys[]'); \
	for host in $${hosts}[@]; do \
		ssh "$${host}" "$${cmd}" || continue; \
		printf "done %s on %s\n" "$${cmd}" "$${host}"; \
	done
