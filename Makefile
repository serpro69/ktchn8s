.POSIX:
.ONESHELL:
.SHELL := $(shell which bash)
.SHELLFLAGS := -ec
.PHONY: *

export KUBECONFIG = $(shell pwd)/metal/kubeconfig.yaml
export KUBE_CONFIG_PATH = $(KUBECONFIG)

default: help

help: ## Print this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

docs: ## Serve documentation on localhost
	@mkdocs serve

bootstrap: ## Wake up and provision the servers
	@make -C metal bootstrap

cluster: ## Create kubernetes cluster
	@make -C metal cluster

console: ## Start the Ansible console
	@make -C metal console

inventory: ## List hosts from the ansible inventory
	@make -C metal inventory

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

wake: ## Wake up the servers without re-provisioning them
	@make -C metal wake
