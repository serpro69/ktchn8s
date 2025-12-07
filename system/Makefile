# Copyright 2025- Serhii Prodanov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

################################################################################################
#                                      NOTE TO DEVELOPERS
#
# While editing this file, please respect the following:
#
# 1. Various variables, rules, functions, etc should be defined in their corresponding section,
#    with variables also separated into relevant subsections
# 2. "Hidden" make variables should start with two underscores `__`
# 3. All shell variables defined in a given target should start with a single underscore `_`
#    to avoid name conflicts with any other variables
# 4. Every new target should be defined in the Targets section
#
# ----------------------------------------------------------------------------------------------
# Use below for reference on how to use variables in a Makefile:
# - https://www.gnu.org/software/make/manual/html_node/Using-Variables.html
# - https://www.gnu.org/software/make/manual/html_node/Flavors.html
# - https://www.gnu.org/software/make/manual/html_node/Setting.html
# - https://www.gnu.org/software/make/manual/html_node/Shell-Function.html
#
################################################################################################

.POSIX:
.ONESHELL:
.PHONY: main

.SHELL 			:= $(shell which bash)
.SHELLFLAGS := -ec

################################################################################################
#                                             VARIABLES

export KUBECONFIG = $(shell pwd)/../metal/kubeconfig.yaml

### Ansible

# Ansible verbosity level
ANSIBLE_VERBOSITY ?= 1

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
main: _requirements ## Provision resources on the kubernetes cluster
	@ansible_verbosity="$(ANSIBLE_VERBOSITY)"; \
	case "$${ansible_verbosity}" in \
		''|*[!0-9]*) \
			printf "Warning: ANSIBLE_VERBOSITY ('$${ansible_verbosity}') is not a valid non-negative integer. Defaulting to verbosity level 1.\n" >&2; \
			verbosity="1"; \
			;; \
		*) \
			verbosity="$${ansible_verbosity}"; \
			;; \
	esac; \
	cmd=("ansible-playbook" "main.yml"); \
	if [ "$${verbosity}" -gt 0 ]; then \
		v_opts="-"; \
		for i in $$(seq 1 "$${verbosity}"); do v_opts+="v"; done; \
		cmd+=("$${v_opts}"); \
	fi; \
	"$${cmd[@]}"
