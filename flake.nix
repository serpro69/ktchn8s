{
  description = "ktchn8s Lab Shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        kanidm-overlay = final: prev: {
          kanidm_1_6_4 = (import (builtins.fetchTarball {
            # https://lazamar.co.uk/nix-versions/?channel=nixos-25.05&package=kanidm
            url = "https://github.com/NixOS/nixpkgs/archive/1c1c9b3f5ec0421eaa0f22746295466ee6a8d48f.tar.gz";
            # sha256 can be computed with:
            # nix-prefetch-url --unpack <URL>
            sha256 = "0szvq1swpzyjmyyw929ngxy1khdnd9ba96qds2bm6l6kg4iq3cq0";
          }) { inherit system; }).kanidm;
        };

        pkgs = import nixpkgs {
           inherit system;
           config.allowUnfree = true;
           overlays = [ kanidm-overlay ];
        };
      in
      with pkgs;
      {
        devShells.default = mkShell {
          packages = [
            # dev tools
            bat
            delta
            diffutils
            eza
            fzf
            git
            gnumake
            jq
            mise
            neovim
            nix-search-cli
            sops
            tmux
            yq
            zsh
            # provisioning/configuration tools
            ansible
            ansible-lint
            opentofu
            minicom
            tflint
            trivy
            xorriso
            # networking tools
            netcat
            nettools
            openssh
            wireguard-tools
            # k8s tools
            dyff
            k9s
            kube3d
            kubectl
            kubernetes-helm
            kustomize
            krew
            # lang support
            go
            gotestsum
            python3 # ansible dependency

            # extra python packages
            (python3.withPackages (p: with p; [
              pip
              # ansible dependencies
              jinja2
              jmespath
              kubernetes
              netaddr
              # post-install
              pexpect
              rich
            ]))
          ] ++ lib.optionals pkgs.stdenv.isDarwin [
            # NOTE: Darwin-only packages for cross-platform compatibility
            # k8s tools
          ] ++ lib.optionals pkgs.stdenv.isLinux [
            # NOTE: Linux-only packages for cross-platform compatibility
            # networking tools
            iproute2
            # k8s tools
            helm
            kanidm_1_6_4
          ];

          shellHook = ''
            # configure python virtual environment with dependencies
            python -m venv .venv
            source .venv/bin/activate
            # use 'git rev-parse' instead of '${self}' to get the root project dir,
            # because while the latter seems promising, 
            # it actually refers to the path in '/nix/store/' where the flake is copied to
            ROOT_PATH=$(git rev-parse --show-toplevel)
            pip install -r "$ROOT_PATH/requirements.txt" >/dev/null

            # kubernetes plugins
            krew install rook-ceph &>/dev/null
          '';
        };
      }
    );
}
