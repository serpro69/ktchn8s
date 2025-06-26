.POSIX:
.ONESHELL:
.PHONY: main

.SHELL 			:= $(shell which bash)
.SHELLFLAGS := -ec

################################################################################################
#                                             VARIABLES

export KUBECONFIG 		  = $(shell pwd)/../metal/kubeconfig.yaml
export KUBE_CONFIG_PATH = $(shell pwd)/../metal/kubeconfig.yaml

################################################################################################
#                                             TARGETS

default: help

### Helpers

help: ## Print this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

_requirements:
	@ansible-galaxy install -r requirements.yml

### Main

main: SHELL:=$(shell which bash)
main: ## Provision external resources
	@make -C ansible main
	@make -C terraform apply
