{
  description = "ktchn8s Lab Shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
           inherit system;
           config.allowUnfree = true;

           overlays = [
               (import (
                 fetchTarball {
                   url = "https://github.com/oxalica/rust-overlay/archive/master.tar.gz";
                   # TODO: better way to ensure sha matches master branch, especially if it's updated quite frequently
                   sha256 = "sha256:05di19x4h0w4gdd47qbmi9zch5l60h550447msdm72yc910kly40";
                 })
               )
             ];
           };

           rustPlatform = pkgs.makeRustPlatform {
             cargo = pkgs.rust-bin.stable.latest.minimal;
             rustc = pkgs.rust-bin.stable.latest.minimal;
           };

           kanidmFromSource = rustPlatform.buildRustPackage rec {
             pname = "kanidm";
             version = "1.6.4";

             src = pkgs.fetchzip {
               url = "https://github.com/kanidm/kanidm/archive/refs/tags/v${version}.tar.gz";
               hash = "sha256-zI+IPwpkkF67/JSl3Uu+Q1giUN49r/hjvY+/QLqB5eM=";
             };

             nativeBuildInputs = [ pkgs.openssl pkgs.pam ];

             cargoHash = "sha256-l4UNdVvPteqs46Fm7yVgkgplANvkAmb4fooLigXRqZM=";

             cargoRoot = "tools/cli";
             cargoLock = {
               lockFile = "${src}/Cargo.lock";
             };

             cargoBuildFlags = [ "--bin" "kanidm" ];

             postPatch = ''
               ln -s ${src}/Cargo.lock tools/cli/Cargo.lock
             '';

             meta = {
               description = "A simple, secure, and fast identity management platform";
               homepage = "https://github.com/kanidm/kanidm";
               license = pkgs.lib.licenses.mpl20;
               maintainers = [ ];
             };
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
            kanidm
            kube3d
            kubectl
            kubernetes-helm
            kustomize
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
            kanidmFromSource
          ] ++ lib.optionals pkgs.stdenv.isLinux [
            # NOTE: Linux-only packages for cross-platform compatibility
            # networking tools
            iproute2
            # k8s tools
            helm
            kanidm
          ];

          shellHook = ''
            # configure python virtual environment with dependencies
            python -m venv .venv
            source .venv/bin/activate
            pip install -r requirements.txt >/dev/null
          '';
        };
      }
    );
}
