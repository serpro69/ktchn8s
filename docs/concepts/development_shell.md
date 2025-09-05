---
icon: material/console
title: Development Shell
---

# :material-console: Development shell concepts

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
ktchn8s on  docs [!+] using 󰅟 default/wlcm-tfstate-ffcb87 via 󱔎 default via ❄ impure (nix-shell-env)
➜ which mkdocs
/nix/store/86p3knkm02c1ix9rfd3y1b53daybl9ag-python3-3.12.10-env/bin/mkdocs
```

!!! warning
    If you have a python virtual environment activated, you should deactivate it before entering the nix shell.
    The nix shell environment in this project will create (if not exists) and activate it's own python venv, which may create conflicts.
    You can also create a custom `nix` bash function that would deactivate any possibly-active virtualenv, and then run the `nix develop` itself.

### Entering the nix-shell automatically

If you have [`direnv`](https://direnv.net) installed, you can run `direnv allow` once and it will automatically enter the nix shell every time you `cd` into the project.

### Using your shell environment within nix-shell

One of my outstanding pain points with Nix is that any time I'm in a nix shell, none of my stuff works the way I want it to... I have lots of aliases, [fzf-based autocomplete thingy](https://github.com/Aloxaf/fzf-tab), tmux integrations, ..., and most importantly - strong feelings about how my shell should look like and behave.

So how do I get my shell environment within a `nix-shell`? So far I've simply added the following aliases (which I found in this [post](https://discourse.nixos.org/t/nix-shell-does-not-use-my-users-shell-zsh/5588/13)) to my default (zsh) shell environment:

```bash
alias nix-shell='nix-shell --run $SHELL'

nix() {
  if [[ $1 == "develop" ]]; then
    shift
    # deactivate any possibly-active virtualenv
    command -v deactivate &> /dev/null && deactivate
    command nix develop -c $SHELL "$@"
  else
    command nix "$@"
  fi
}
```

Having just started playing around with nix I don't know if this is an ideal solution, but I like to keep things simple and it does seem to work just fine.

And now, instead of a default PS1 and no configs of my own:

```bash
➜ nix develop
razorback:ktchn8s sergio$ ela

bash: ela: command not found
```

I have all of my configs within the nix shell environment:

```bash
➜ nix develop

ktchn8s on  docs [!+] using 󰅟 default/wlcm-tfstate-ffcb87 via 󱔎 default via ❄ impure (nix-shell-env)
➜ ela

Permissions Size User   Date Modified Name
drwxr-xr-x@    - sergio 28 May 16:53  .git/
.rw-r--r--@  456 sergio 28 May 09:16  .yamlfmt.yaml
.rw-r--r--@  291 sergio 28 May 09:16  .yamllint.yml
drwxr-xr-x@    - sergio 28 May 09:16  docs/
.rw-r--r--@ 1.5k sergio 28 May 14:53  flake.lock
.rw-r--r--@  772 sergio 28 May 16:32  flake.nix
.rw-r--r--@ 1.1k sergio 28 May 09:16  LICENSE.md
.rw-r--r--@ 1.3k sergio 28 May 14:43  mkdocs.yml
.rw-r--r--@  117 sergio 28 May 09:15  README.md
```

### Searching for particular commands in nix packages

Sometimes you may find yourself asking: "What nix package provides the `foobar` command?"

Instead of going directly to [search.nixos.org](https://search.nixos.org), you may want to try the [`nix-search`](https://github.com/peterldowns/nix-search-cli) tool, which lets you ask exactly the above question.
It's also available as a flake `github:peterldowns/nix-search-cli`.

Let's say we need the `ifconfig` command:

```bash
➜ nix-search -p ifconfig
unixtools.nettools @ 1003.1-2008 : ifconfig arp hostname netstat route
unixtools.ifconfig @ 2.10 : ifconfig
toybox @ 0.8.12 : ifconfig [ acpi arch ascii ...
nettools @ 2.10 : ifconfig arp dnsdomainname ...
inetutils @ 2.6 : ifconfig dnsdomainname ftp ...
busybox @ 1.36.1 : ifconfig [ [[ acpid add-shell ...
```

!!! info
    You may wonder why you're seeing `/nix/store/.../bin/bash` when running `echo $SHELL` within the nix development environment, even though we've set the default shell to use `zsh`.
    ```bash
    ➜ which $SHELL
    /nix/store/xy4jjgw87sbgwylm5kn047d9gkbhsr9x-bash-5.2p37/bin/bash
    ```
    In nix, `SHELL` variable seems to point to the shell that the package derivation uses as its shell (which usually is `bash`).
    There's some more details about this behavior in this [comment](https://github.com/NixOS/nix/pull/8043#issuecomment-1814009237)


