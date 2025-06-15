.POSIX:
.ONESHELL:
.SHELL := $(shell which bash)
.SHELLFLAGS := -ec
.PHONY: *

.EXPORT_ALL_VARIABLES:

KUBECONFIG = $(shell pwd)/metal/kubeconfig.yaml
KUBE_CONFIG_PATH = $(KUBECONFIG)

default: help

help: ## Print this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

docs: ## Serve documentation on localhost
	@mkdocs serve

bootstrap: ## Wake up and provision the servers
	@make bootstrap -C metal

cluster: ## Create kubernetes cluster
	@make cluster -C metal

console: ## Start the Ansible console
	@make console -C metal

wake: ## Wake up the servers without re-provisioning them
	@make wake -C metal
