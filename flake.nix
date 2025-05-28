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
            diffutils
            git
            jq
            fzf
            tmux
            neovim
            openssh
            python3
            mise

            (python3.withPackages (p: with p; [
              pip
              mkdocs
              mkdocs-material
            ]))
          ];

          shellHook = ''
            # can run stuff here
          '';
        };
      }
    );
}
