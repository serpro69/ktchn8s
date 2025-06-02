{
  description = "Ktchn8s Lab Shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
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
            xorriso
            # networking tools
            netcat
            nettools
            openssh
            # lang support
            python3 # ansible dependency

            # extra python packages
            (python3.withPackages (p: with p; [
              pip
            ]))
          ] ++ lib.optionals pkgs.stdenv.isDarwin [
            # NOTE: Darwin-only packages for cross-platform compatibility
          ] ++ lib.optionals pkgs.stdenv.isLinux [
            # NOTE: Linux-only packages for cross-platform compatibility
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
