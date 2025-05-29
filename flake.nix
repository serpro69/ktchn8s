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
            jq
            minicom
            mise
            neovim
            nix-search-cli
            tmux
            # networking tools
            netcat
            nettools
            openssh
            # lang support
            python3

            # extra python packages
            (python3.withPackages (p: with p; [
              pip
            ]))
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
