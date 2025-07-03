{
  description = "ktchn8s Lab Shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # kanidm 1.2.3, lowest I find and build with nix that's <= kanidm server version (1.3.3)
        # using client version > 1.3.3 results in incompatibilities and errors
        # e.g. I couldn't reset a person's token because it throws an error about missing input for expiration time
        kanidm-overlay = final: prev: {
          kanidm_1_2 = (import (builtins.fetchTarball {
            # https://lazamar.co.uk/nix-versions/?channel=nixos-25.05&package=kanidm
            url = "https://github.com/NixOS/nixpkgs/archive/f27b62e789ceae5531852d8a015bae05ada145de.tar.gz";
            # sha256 can be computed with:
            # nix-prefetch-url --unpack <URL>
            sha256 = "0h5wj3bi3z01wdk62j6li5lhpac141l6sgjspszfv59nxrpan28z";
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
            kanidm_1_2
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
          ];

          shellHook = ''
            # configure python virtual environment with dependencies
            python -m venv .venv
            source .venv/bin/activate
            pip install -r requirements.txt >/dev/null

            # kubernetes plugins
            krew install rook-ceph &>/dev/null
          '';
        };
      }
    );
}
