# Development Shell

A development shell makes it easy to get all of the dependencies needed to interact with your homelab. [Nix](https://nixos.org/) with [Flakes](https://nixos.wiki/wiki/Flakes) provides a convenient way to define and manage these dependencies in a reproducible manner.

## Installation

!!! info

    NixOS users can skip this step.

Install Nix using one of the following methods:

- [Official Nix installer](https://nixos.org/download)
- [Determinate Nix Installer](https://docs.determinate.systems/getting-started/#installer)

If you're using the official installer, add the following to your `~/.config/nix/nix.conf` to enable [Flakes](https://nixos.wiki/wiki/Flakes):

```conf
experimental-features = nix-command flakes
```

## Usage

Run the following command:

```sh
nix develop
```

It will open a shell and install all the dependencies defined in `flake.nix` file at the root of the project:

```
sergio@serenity:~/Projects/personal/Ktchn8S$ which kubectl
/nix/store/1478zvihnhxn27d6mgbkay7bahfcbx86-kubectl-1.30.1/bin/kubectl
```

!!! tip

    If you have [`direnv`](https://direnv.net) installed, you can run `direnv
    allow` once and it will automatically enter the Nix shell every time you
    `cd` into the project.
