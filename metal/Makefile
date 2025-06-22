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
.SHELL 			:= $(shell which bash)
.SHELLFLAGS := -ec
.PHONY: _requirements bootstrap cluster console help inventory main wake wipe
# https://stackoverflow.com/a/63771055
__MAKE_DIR=$(dir $(realpath $(lastword $(MAKEFILE_LIST))))

export KUBECONFIG = $(shell pwd)/kubeconfig.yaml

################################################################################################
#                                             VARIABLES

### Ansible

# List of coma-separated ansible-playbook tags
ANSIBLE_TAGS      ?=
# A coma-separated list of target hosts to limit the playbook execution to
ANSIBLE_TARGETS   ?=
# Ansible verbosity level
ANSIBLE_VERBOSITY ?= 1

### Terminal

# Set to 'true' to disable some options like colors in environments where $TERM is not set
NO_TERM ?=

### Misc

# Change output
# https://www.mankier.com/5/terminfo#Description-Highlighting,_Underlining,_and_Visible_Bells
# https://www.linuxquestions.org/questions/linux-newbie-8/tput-for-bold-dim-italic-underline-blinking-reverse-invisible-4175704737/#post6308097
__RESET          = $(shell tput sgr0)
__BLINK          = $(shell tput blink)
__BOLD           = $(shell tput bold)
__DIM            = $(shell tput dim)
__SITM           = $(shell tput sitm)
__REV            = $(shell tput rev)
__SMSO           = $(shell tput smso)
__SMUL           = $(shell tput smul)
# https://www.mankier.com/5/terminfo#Description-Color_Handling
__BLACK          = $(shell tput setaf 0)
__RED            = $(shell tput setaf 1)
__GREEN          = $(shell tput setaf 2)
__YELLOW         = $(shell tput setaf 3)
__BLUE           = $(shell tput setaf 4)
__MAGENTA        = $(shell tput setaf 5)
__CYAN           = $(shell tput setaf 6)
__WHITE          = $(shell tput setaf 7)
# set to 'true' to disable colors
__NO_COLORS      = false

# https://stackoverflow.com/a/10858332
# Check that given variables are set and all have non-empty values,
# die with an error otherwise.
#
# Params:
#   1. Variable name(s) to test.
#   2. (optional) Error message to print.
check_defined = \
    $(strip $(foreach 1,$1, \
        $(call __check_defined,$1,$(strip $(value 2)))))

__check_defined = \
    $(if $(value $1),, \
      $(error Undefined $1$(if $2, ($2))))

################################################################################################
#                                             RULES

ifeq ($(NO_TERM),true)
  __NO_COLORS=true
endif

ifeq ($(origin TERM), undefined)
  __NO_COLORS=true
endif

ifeq ($(__NO_COLORS),true)
	__RESET   =
  __BLINK   =
  __BOLD    =
  __DIM     =
  __SITM    =
  __REV     =
  __SMSO    =
  __SMUL    =
  __BLACK   =
  __RED     =
  __GREEN   =
  __YELLOW  =
  __BLUE    =
  __MAGENTA =
  __CYAN    =
  __WHITE   =
endif

# Check for necessary tools
ifneq ($(filter help,$(MAKECMDGOALS)),)
  # Skip checks for help target
else
  ifeq (, $(shell which ansible-playbook))
    $(error "No ansible in '$(PATH)', go to https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html and follow the instructions")
  endif
  ifeq (, $(shell which jq))
    $(error "No jq in '$(PATH)', go to https://github.com/jqlang/jq?tab=readme-ov-file#installation and follow the instructions")
  endif
  ifeq (, $(shell which yq))
    $(error "No yq in '$(PATH)', go to https://github.com/mikefarah/yq/#install and follow the instructions")
  endif
endif

################################################################################################
#                                             FUNCTIONS

define play
	$(eval $@_PLAY_FILE = $(1))
	$(eval $@_TAGS_ARG = $(strip $(2)))
	$(eval $@_TARGETS_ARG = $(strip $(3)))
	$(eval $@_EXTRA_ARGS_ARG = $(strip $(4)))

	@ansible_verbosity="$(ANSIBLE_VERBOSITY)"; \
	play_file_val="$($@_PLAY_FILE)"; \
	tags_val="$($@_TAGS_ARG)"; \
	targets_val="$($@_TARGETS_ARG)"; \
	extra_args_val="$($@_EXTRA_ARGS_ARG)"; \
	\
	verbosity="1"; \
	case "$${ansible_verbosity}" in \
		''|*[!0-9]*) \
			echo "Warning: ANSIBLE_VERBOSITY ('$${ansible_verbosity}') is not a valid non-negative integer. Defaulting to verbosity level 1." >&2; \
			verbosity="1"; \
			;; \
		*) \
			verbosity="$${ansible_verbosity}"; \
			;; \
	esac; \
	\
	cmd=("ansible-playbook" "-i" "inventory.sh"); \
	\
	if [ "$${verbosity}" -gt 0 ]; then \
		v_opts="-"; \
		for i in $$(seq 1 "$${verbosity}"); do v_opts+="v"; done; \
		cmd+=("$${v_opts}"); \
	fi; \
	\
	if [ ! "$${tags_val}" = "" ]; then \
		cmd+=("--tags" "'$${tags_val}'"); \
	fi; \
	if [ ! "$${targets_val}" = "" ]; then \
		cmd+=("--limit" "$${targets_val}"); \
	fi; \
	\
	if [ ! "$${extra_args_val}" = "" ]; then \
		cmd+=($${extra_args_val}); \
	fi; \
	\
	cmd+=("$${play_file_val}"); \
	echo "Running: $${cmd[@]}"; \
	"$${cmd[@]}"
endef

################################################################################################
#                                             TARGETS

default: help

### Helpers

help: ## Print this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

~/.ssh/homelab_id_ed25519:
	@ssh-keygen -t ed25519 -P '' -f "$@"

_requirements:
	@ansible-galaxy install -r requirements.yml

### Main

bootstrap: SHELL:=$(shell which bash)
bootstrap: ~/.ssh/homelab_id_ed25519 _requirements ## Wake up and provision the servers
	@$(call play,bootstrap.yml,$(ANSIBLE_TAGS),$(ANSIBLE_TARGETS),)

cluster: SHELL:=$(shell which bash)
cluster: ~/.ssh/homelab_id_ed25519 _requirements ## Create kubernetes cluster on provisioned servers
	@$(call play,cluster.yml,$(ANSIBLE_TAGS),$(ANSIBLE_TARGETS),)

console: SHELL:=$(shell which bash)
console: ## Start the Ansible console
	@ansible-console \
		--inventory inventory.sh

inventory: SHELL:=$(shell which bash)
inventory: ## List hosts from the ansible inventory
	@ansible-inventory -i inventory.sh --list | jq -r '._meta.hostvars | keys[]'

main: SHELL:=$(shell which bash)
main: ~/.ssh/homelab_id_ed25519 _requirements ## Provision kubernetes cluster
	@$(call play,main.yml,$(ANSIBLE_TAGS),$(ANSIBLE_TARGETS),)

wake: SHELL:=$(shell which bash)
wake: ~/.ssh/homelab_id_ed25519 _requirements ## Wake up the servers without re-provisioning them
	@$(call play,bootstrap.yml,$(ANSIBLE_TAGS),$(ANSIBLE_TARGETS),--extra-vars "pxe_state=absent")

DISK ?= /dev/nvme0n1

wipe: SHELL:=$(shell which bash)
wipe: ~/.ssh/homelab_id_ed25519 _requirements ## Wipe the DISK disk on the SERVER
	@$(call check_defined, SERVER, missing or empty variable; run 'make inventory' for a list of hosts)
	@$(call check_defined, DISK, missing or empty variable; run 'make inventory' for a list of hosts)
	@$(call play,wipe.yml,$(ANSIBLE_TAGS),,-e "wipe_target=$(SERVER)" -e "target_disk=$(DISK)")
