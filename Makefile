.POSIX:
.ONESHELL:
.SHELL := $(shell which bash)
.SHELLFLAGS := -ec
.PHONY: *

export KUBECONFIG = $(shell pwd)/metal/kubeconfig.yaml
export KUBE_CONFIG_PATH = $(KUBECONFIG)

### Ansible

# List of coma-separated ansible-playbook tags
ANSIBLE_TAGS      ?=
# Ansible verbosity level
ANSIBLE_VERBOSITY ?= 1

### Terminal

# Set to 'true' to disable some options like colors in environments where $TERM is not set
NO_TERM ?=

default: help

help: ## Print this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

docs: ## Serve documentation on localhost
	@mkdocs serve

bootstrap: ## Wake up and provision the servers
	@make bootstrap -C metal \
		ANSIBLE_TAGS="$(ANSIBLE_TAGS)" \
		ANSIBLE_VERBOSITY=$(ANSIBLE_VERBOSITY) \
		NO_TERM=$(NO_TERM)

cluster: ## Create kubernetes cluster
	@make cluster -C metal \
		ANSIBLE_TAGS="$(ANSIBLE_TAGS)" \
		ANSIBLE_VERBOSITY=$(ANSIBLE_VERBOSITY) \
		NO_TERM=$(NO_TERM)

console: ## Start the Ansible console
	@make console -C metal

run: ## Run a CMD command on all servers via SSH
	@cmd=$(CMD); \
	if [ -z "$${cmd}" ]; then \
		echo "Please set CMD variable to the command you want to run"; \
		exit 1; \
	fi; \
	ansible-inventory -i metal/inventory.sh --list | jq -r '._meta.hostvars | keys[]' | while IFS= read -r host; do \
		ssh "$${host}" "$${cmd}" || printf "failed to connect to %s" "${host}"; \
		printf "\ndone %s on %s\n" "$${cmd}" "$${host}"; \
	done

wake: ## Wake up the servers without re-provisioning them
	@make wake -C metal \
		ANSIBLE_TAGS="$(ANSIBLE_TAGS)" \
		ANSIBLE_VERBOSITY=$(ANSIBLE_VERBOSITY) \
		NO_TERM=$(NO_TERM)
