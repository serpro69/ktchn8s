.POSIX:
.PHONY: bootstrap

export KUBECONFIG = $(shell pwd)/../metal/kubeconfig.yaml

bootstrap:
	@ansible-playbook \
		main.yml \
		-v
