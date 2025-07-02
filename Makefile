.POSIX:
.ONESHELL:
.SHELL := $(shell which bash)
.SHELLFLAGS := -ec
.PHONY: *
# .EXPORT_ALL_VARIABLES: this causes issues with tput, dunno why...

export KUBECONFIG       = $(shell pwd)/../metal/kubeconfig.yaml
export KUBE_CONFIG_PATH = $(KUBECONFIG)

################################################################################################
#                                             VARIABLES

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

################################################################################################
#                                             TARGETS

default: help

### main

ktchn8s: metal system external finalize ## Provision ktchn8s homelab cluster

destroy: ## Destroy the ktchn8s homelab cluster and all associated resources
	@printf "$(__BOLD)$(__RED)WARNING! You are about to wipe your cluster! This can not be reverted!$(__RESET)\n"; \
	printf "$(__BOLD)$(__RED)Do you want to proceed?$(__RESET)\n"; \
	read -p "$(__BOLD)$(__RED)Only 'YES' will be accepted: $(__RESET)" ANSWER && \
	if [ "$${ANSWER}" = "YES" ]; then \
		for hst in $$(make inventory | xargs); do \
			make -C metal wipe SERVER=$$hst; \
		done; \
		make -C external destroy; \
		make clean; \
		printf "$(__GREEN)All resources have been destroyed!$(__RESET)\n"; \
		printf "$(__GREEN)  - Commit the terraform state with deleted resources: $(__DIM)git add external/terraform/terraform.tfstate.d && git commit -m 'Delete external resources'$(__RESET)\n"; \
		printf "$(__GREEN)  - Clean up DNS records created by the cluster in your cloudflare zone $(__DIM)(yes, this is manual for now 😔)$(__RESET)\n"; \
		printf "$(__GREEN)  - Make a new cluster: $(__DIM)make ktchn8s$(__RESET) 🚀\n"; \
	fi

### metal

console: ## Start the Ansible console
	@make -C metal console

inventory: ## List metal hosts from the ansible inventory
	@make -C metal inventory

metal: ## Provision baremetal servers and create a kubernetes cluster
	@make -C metal main; \
	./tests/metal.sh

wake: ## Wake up the metal servers without re-provisioning them
	@make -C metal wake

clean: ## Shutdown ephemeral PXE server resources
	@docker compose --project-directory ./metal/roles/pxe_server/files down

### system

system: ## Provision system resources on the kubernetes cluster
	@make -C system main

### external

external: ## Provision external resources
	@make -C external main

### misc

finalize: clean ## Finalize the ktchn8s homelab cluster setup
	@make -C tests filter=Smoke; \
	./scripts/post-install.py

docs: ## Serve documentation on localhost
	@mkdocs serve

help: ## Print this help message
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

run: ## Run a CMD command on all servers via SSH
	@cmd=$(CMD); \
	if [ -z "$${cmd}" ]; then \
		echo "Set CMD variable to the command you want to run on each host"; \
		exit 1; \
	fi; \
	hosts=$$(ansible-inventory -i metal/inventory.sh --list | jq -r '._meta.hostvars | keys[]'); \
	for host in $${hosts}; do \
		ssh "$${host}" "$${cmd}" || continue; \
		printf "done %s on %s\n" "$${cmd}" "$${host}"; \
	done
