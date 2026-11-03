---
icon: material/crosshairs-question
title: SSH into the Workstation from Android
---

# :material-crosshairs-question: HowTo SSH into the workstation from an Android phone

This guide makes the workstation (the Ansible/PXE controller) reachable over SSH from an Android phone on the home network, without weakening the rest of the setup.

The security model:

- **LAN only.** SSH is accepted from the home network (VLAN 2, `192.168.1.0/24`) and nothing else — enforced by `ufw` on Linux and by sshd's `AllowUsers` on macOS (which also admits the tailnet if you [use Tailscale](#option-b-tailscale-magicdns)). No port forwarding on the router, ever. For access from outside the house, use Tailscale instead of exposing port 22.
- **Key only.** Password and keyboard-interactive auth are disabled, root login is disabled, and only one user is allowed.
- **The private key never leaves the phone.** It's generated on the phone; only the public key is copied to the workstation.

The workstation-side steps come in two flavours, in tabs:

- **Linux** — a Debian-family workstation (Pop!_OS 22.04 at the time of writing), Wi-Fi interface `wlp0s20f3`.
- **macOS** — a MacBook (macOS 26 on Apple Silicon at the time of writing), Wi-Fi interface `en0`. Also read [macOS-specific caveats](#macos-specific-caveats): sleep, file access and the Keychain behave differently over SSH.

Both assume user `sergio`. The Linux workstation is reached at its reserved IP `192.168.1.100`; the Mac (`razorback`) is reached by name — `razorback.local` or its Tailscale name — so it doesn't need a DHCP reservation (see [step 6](#6-give-the-workstation-a-stable-address)). Wherever the phone-side commands below say `192.168.1.100`, use the Mac's name instead. Adjust names and addresses as needed. The phone-side steps are otherwise the same for both.

!!! warning "A Mac can't be the PXE controller"
    `make metal` runs the PXE containers with `network_mode: host` (`metal/roles/pxe_server/files/docker-compose.yml`). On macOS, Docker runs inside a Linux VM, so "host" is the VM's network, not the Mac's — the nodes never see the proxyDHCP/TFTP replies. A Mac works as a workstation for SSH, `kubectl`, Ansible and the rest, but provisioning bare metal needs a Linux machine. That's why the PXE firewall rules below exist only on the Linux side.

## 1. Enable the firewall

=== "Linux"

    Check the state first — the `ufw` *service* can be `active` while the firewall itself is disabled:

    ```bash
    sudo ufw status verbose
    ```

    If it reports `Status: inactive`, enable it with a default-deny policy, allowing SSH from the home LAN and the PXE ports used during provisioning:

    ```bash
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp comment 'SSH from home LAN'
    sudo ufw allow 67/udp comment 'PXE proxyDHCP'
    sudo ufw allow from 10.10.10.0/24 to any port 4011 proto udp comment 'PXE proxyDHCP'
    sudo ufw allow from 10.10.10.0/24 to any port 69 proto udp comment 'PXE TFTP'
    sudo ufw allow from 10.10.10.0/24 to any port 80 proto tcp comment 'PXE HTTP'
    sudo ufw enable
    sudo ufw status verbose
    ```

    Expect `Status: active`, `Default: deny (incoming), allow (outgoing), deny (routed)`, and the rules above. Rules restricted to an IPv4 subnet get no `(v6)` twin; only `67/udp` does.

    !!! question "Does deny incoming break responses?"
        No. `ufw` is stateful: replies to connections the workstation starts are allowed back in. Everything outbound keeps working — `kubectl`, `ssh`/Ansible to the nodes, Wake-on-LAN (`make wake`), `git`, `terraform`, Docker pulls, Tailscale.

        Only *new inbound* connections are filtered. Ubuntu's default `ufw` rules also allow mDNS (`5353/udp` multicast), so `.local` discovery keeps working.

    !!! warning "Don't forget the PXE ports"
        `make metal` runs the PXE server on the workstation itself (`metal/bootstrap.yml` targets `localhost`), and both containers in `metal/roles/pxe_server/files/docker-compose.yml` use `network_mode: host`. The nodes open connections *to* the workstation, so without the rules above `ufw` drops them silently and nodes fail to PXE boot or hang fetching the kickstart:

        | Port | Service |
        | ---- | ------- |
        | `67/udp` | dnsmasq proxyDHCP (`dhcp_proxy: true`) |
        | `4011/udp` | proxyDHCP follow-up from UEFI PXE clients |
        | `69/udp` | TFTP (grub, kernel, initrd) |
        | `80/tcp` | nginx (OS repo and kickstart files) |

        `67/udp` is allowed from anywhere on purpose: a PXE client's first DHCP broadcast comes from `0.0.0.0`, which a `from 10.10.10.0/24` rule never matches. Keeping these rules permanently is fine — nothing listens on those ports outside of provisioning (`make clean` removes the containers). `10.10.10.0/24` comes from `homelab_net_cidr` in `metal/group_vars/all.yml`.

    !!! warning "Docker bypasses ufw"
        Ports published with `docker run -p` skip `ufw` entirely, because Docker inserts its own iptables rules ahead of it. For containers that should only be reachable locally, bind to loopback: `-p 127.0.0.1:8080:80`.

=== "macOS"

    The macOS application firewall filters **per app, not per port or source address** — it can't express "port 22 from `192.168.1.0/24` only". Turn it on anyway, so unsigned apps can't accept incoming connections without approval:

    ```bash
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode on
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
    ```

    Or: System Settings → Network → Firewall. Apple's `sshd` is signed, so it's allowed through automatically once Remote Login is on.

    The **LAN-only** restriction moves into sshd itself: `AllowUsers sergio@192.168.1.0/24` in [step 2](#2-write-the-sshd-hardening-config-before-the-server-starts) rejects every connection that doesn't come from the home network, whatever the firewall says.

    !!! note "Why not pf?"
        `pf` can filter by source address, but macOS upgrades overwrite `/etc/pf.conf` and it needs a launchd job to load rules at boot. That's a lot of fragile machinery to duplicate what `AllowUsers` already does, behind a router that doesn't forward any ports.

## 2. Write the sshd hardening config *before* the server starts

=== "Linux"

    The `openssh-server` package starts `sshd` as soon as it's installed, with stock defaults that allow password logins. Writing the drop-in first means the server never runs unhardened:

    ```bash
    sudo mkdir -p /etc/ssh/sshd_config.d
    sudo tee /etc/ssh/sshd_config.d/10-hardening.conf >/dev/null <<'EOF'
    # Key-only SSH, LAN access enforced by ufw
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PermitRootLogin no
    PubkeyAuthentication yes
    AllowUsers sergio
    EOF
    ```

    On Ubuntu, `sshd_config` includes `sshd_config.d/*.conf` at the top and the **first** value for a setting wins. The `10-` prefix sorts ahead of files like `50-cloud-init.conf` (which ships `PasswordAuthentication yes` on some installs).

    !!! note "Why no `ListenAddress`"
        Pinning `ListenAddress 192.168.1.100` would keep sshd off the Docker bridge and Tailscale, but if the DHCP address ever changes, sshd fails to start. The firewall already restricts who can connect, so this setup doesn't pin it.

=== "macOS"

    `sshd` ships with macOS but doesn't run until Remote Login is turned on (step 3). Writing the drop-in first means it never runs unhardened:

    ```bash
    sudo tee /etc/ssh/sshd_config.d/10-hardening.conf >/dev/null <<'EOF'
    # Key-only SSH, LAN access enforced here (the macOS firewall can't filter by source)
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PermitRootLogin no
    PubkeyAuthentication yes
    AllowUsers sergio@192.168.1.0/24
    EOF
    ```

    `/etc/ssh/sshd_config` includes `sshd_config.d/*` at the top and the **first** value for a setting wins. `10-hardening.conf` sorts ahead of the stock `100-macos.conf` (which sets `UsePAM yes` — PAM is how passwords would get in, hence disabling `KbdInteractiveAuthentication` as well).

    The `@192.168.1.0/24` part matches the client's IP address, so the same key from any other network is refused. If you [connect over Tailscale](#option-b-tailscale-magicdns), add its range: `AllowUsers sergio@192.168.1.0/24 sergio@100.64.0.0/10`.

    !!! tip "No restart needed"
        launchd starts a fresh `sshd` for every incoming connection, so config changes apply to the next connection. Keep a session open while you edit anyway, in case you lock yourself out.

## 3. Install and verify the server

=== "Linux"

    ```bash
    sudo apt update && sudo apt install -y openssh-server
    ```

    Check the *effective* configuration (not just what the file says):

    ```bash
    sudo sshd -T | grep -Ei '^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin|pubkeyauthentication|allowusers|port) '
    ls /etc/ssh/sshd_config.d/
    ```

    Expected:

    ```console
    port 22
    permitrootlogin no
    pubkeyauthentication yes
    passwordauthentication no
    kbdinteractiveauthentication no
    allowusers sergio
    ```

    …and `10-hardening.conf` should be the only file in the directory (otherwise check what the others set).

    Confirm the service is running, enabled at boot, and that the server refuses anything but keys:

    ```bash
    systemctl is-active ssh; systemctl is-enabled ssh
    ss -tlnH 'sport = :22'
    ssh -o BatchMode=yes -o PubkeyAuthentication=no \
        -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
        sergio@192.168.1.100 true
    ```

    The last command must fail with `Permission denied (publickey).` — `publickey` being the only method offered means password auth is off.

    `sshd` listens on IPv6 (`[::]:22`) too; there is no IPv6 rule for port 22, so `ufw` blocks it.

=== "macOS"

    Turn on Remote Login: System Settings → General → Sharing → **Remote Login** → ⓘ:

    - **Allow access for:** *Only these users* → `sergio`. A second gate on top of `AllowUsers`.
    - **Allow full disk access for remote users:** leave **off** — see [Files in Documents, Desktop and Downloads](#files-in-documents-desktop-and-downloads).

    (`sudo systemsetup -setremotelogin on` does the same, but only if the terminal app itself has Full Disk Access — the Settings toggle is simpler.)

    Check the *effective* configuration (not just what the file says):

    ```bash
    sudo sshd -T | grep -Ei '^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin|pubkeyauthentication|allowusers|port) '
    ls /etc/ssh/sshd_config.d/
    ```

    Expected:

    ```console
    port 22
    permitrootlogin no
    pubkeyauthentication yes
    passwordauthentication no
    kbdinteractiveauthentication no
    allowusers sergio@192.168.1.0/24
    ```

    …and the directory should contain only `10-hardening.conf` and `100-macos.conf`.

    Confirm port 22 is open and that the server refuses anything but keys:

    ```bash
    sudo lsof -nP -iTCP:22 -sTCP:LISTEN
    ssh -o BatchMode=yes -o PubkeyAuthentication=no \
        -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
        sergio@"$(ipconfig getifaddr en0)" true
    ```

    `lsof` shows `launchd` holding the socket — that's expected, it hands each connection to a new `sshd`. The `ssh` command must fail with `Permission denied (publickey).` — `publickey` being the only method offered means password auth is off. Run it while on the home Wi-Fi: the connection then comes from the Mac's own LAN address, the same path the phone takes. (`localhost` would come from `127.0.0.1`, which `AllowUsers` rejects regardless of auth method, so it proves nothing.)

## 4. Generate the key on the phone and authorize it

=== "Termux"

    Install Termux from F-Droid (the Play Store build is outdated), then:

    ```bash
    pkg install openssh
    ssh-keygen -t ed25519 -C "phone"
    cat ~/.ssh/id_ed25519.pub
    ```

=== "Termius"

    Keychain → Generate key → Ed25519, then copy the public key.

**Set a passphrase on the key.** The phone is the device most likely to be lost or stolen; the passphrase is what stops whoever has it from also getting into the workstation.

The public key (one line, `ssh-ed25519 AAAA… comment`) is not secret, so get it to the workstation any way you like. **Never transfer the private key** (`id_ed25519` without `.pub`).

On the workstation (same on Linux and macOS):

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo 'ssh-ed25519 AAAA...paste-your-key... phone' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
ssh-keygen -lf ~/.ssh/authorized_keys
```

Use `>>`, not `>` — a single `>` overwrites any keys already in the file. Compare the fingerprint printed by the last command with the one on the phone (`ssh-keygen -lf ~/.ssh/id_ed25519.pub` in Termux).

!!! tip "Don't enable password auth just to run `ssh-copy-id`"
    It's the usual shortcut, and it's usually never turned back off. Pasting the public key by hand takes the same time.

## 5. Connect and verify the host fingerprint

Get the workstation's host key fingerprint **before** the first connection (same path on Linux and macOS):

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Then, with the phone on home Wi-Fi (connections from mobile data are refused — unless you go through Tailscale):

=== "Termux"

    ```bash
    ssh sergio@192.168.1.100      # Linux workstation, reserved IP
    ssh sergio@razorback.local    # Mac, Bonjour name
    ssh sergio@razorback          # Mac, Tailscale MagicDNS name
    ```

=== "Termius"

    New host: address `192.168.1.100` (or the Mac's name, as above), username `sergio`, the key from step 4, no password.

On first connect the client shows a fingerprint and asks whether to trust it. Accept only if it matches the one above exactly — that comparison is the only thing proving the phone reached the workstation and not something else. If you accepted without comparing, check afterwards with `ssh-keygen -lF <address or name you connected to>` in Termux.

The phone remembers the key under the exact name or address you typed, so `razorback.local` and `razorback` are verified separately — compare the fingerprint the first time for each.

The host key is regenerated if the OS is reinstalled, so the phone will warn about a changed key after a reinstall. That's expected only then; any other time, stop and investigate.

## 6. Give the workstation a stable address

The phone's saved host has to keep pointing at the workstation. Left alone, DHCP may hand the workstation a different IP over time — and on a Mac, which randomizes its Wi-Fi MAC by default, the router may see a "new" device and do so often. Three ways to deal with it:

| Option | Works from | Router work | Notes |
| ------ | ---------- | ----------- | ----- |
| [A. DHCP reservation](#option-a-dhcp-reservation) | Home Wi-Fi | Reservation on the C1111, MAC must be fixed | Needed if the workstation must reach the storage node (the C1111 ACL allows `192.168.1.100/32`) |
| [B. Tailscale MagicDNS](#option-b-tailscale-magicdns) | Anywhere | None | Recommended for the Mac |
| [C. Bonjour `.local` name](#option-c-bonjour-local-name) | Home Wi-Fi | None | Depends on the phone resolving `.local` names |

The Linux workstation uses A. The Mac uses B and C and skips the reservation — it can keep its Private Wi-Fi address on, because nothing depends on its MAC or IP. The trade-off: the Mac can't SSH into the storage node, since the C1111 only allows `192.168.1.100` there.

!!! note "Connect to a name, not to a MAC"
    SSH always connects to an IP address; a MAC only matters on the local link, to the router. A reservation turns a fixed MAC into a fixed IP. B and C skip that: the phone looks up the current IP by name each time.

### Option A: DHCP reservation

Reserve `192.168.1.100` on the C1111 as described in [HowTo add DHCP reservations](./how_to_add_dhcp_reservations.md). Check the current binding:

```cisco
muspell#show ip dhcp binding 192.168.1.100
```

The type must be **Manual**, with client-id `01` + the Wi-Fi MAC in dotted notation. If the workstation was replaced (e.g. a Mac taking over from a Linux laptop), the existing binding still holds the old machine's MAC — clear it and reserve the new one.

A reservation only works if the MAC stays the same, so make sure the Wi-Fi MAC isn't randomized:

=== "Linux"

    Get the MAC with `ip -br link show wlp0s20f3`, then check:

    ```bash
    nmcli -f 802-11-wireless.cloned-mac-address con show "<wifi connection name>"
    ```

    `--` (default) or `permanent` is fine; `random` or `stable` breaks the reservation.

=== "macOS"

    Only needed if you do want a reservation for the Mac (e.g. so it can reach the storage node); with options B/C, skip this.

    macOS uses a **Private Wi-Fi address** by default — a made-up MAC per network, which may rotate. Turn it off for the home network: System Settings → Wi-Fi → **Details…** next to the network → **Private Wi-Fi address** → *Off*. Then rejoin the network and read the MAC that's actually in use:

    ```bash
    ifconfig en0 | awk '/ether/ {print $2}'
    ```

    With the private address on, this shows a locally administered MAC — the second hex digit is `2`, `6`, `a` or `e` (e.g. `22:c1:…`). With it off, it shows the hardware MAC (the one under System Settings → General → About). Reserve that one. *Fixed* also keeps a stable MAC, but it's a different one per network and doesn't survive a reinstall; *Rotating* breaks the reservation.

    `networksetup -getmacaddress Wi-Fi` always prints the hardware MAC, even when a private one is in use — don't use it to check what the router sees.

!!! warning
    The committed router configs (`docs/installation/.files/muspell_startup-config_stage{3,4}.txt`) don't contain this reservation. Rebuilding the router from them loses it — see the ToDo list.

### Option B: Tailscale MagicDNS

Both devices join the same tailnet, and the phone connects to the Mac's Tailscale name. The name never changes, whatever the Mac's LAN IP or MAC — and it works from mobile data too, without opening anything on the router.

1. **Mac:** install the Tailscale app and log in (`/usr/local/bin/tailscale` is its CLI). Get the Mac's MagicDNS name:

    ```bash
    tailscale status --json | jq -r .Self.DNSName   # e.g. razorback.tail1234.ts.net.
    ```

    The machine name comes from the Mac's hostname; rename it in the Tailscale admin console if you like.

2. **sshd:** connections over Tailscale come from the tailnet range, not from `192.168.1.0/24`, so allow it in `/etc/ssh/sshd_config.d/10-hardening.conf`:

    ```
    AllowUsers sergio@192.168.1.0/24 sergio@100.64.0.0/10
    ```

    Check with `sudo sshd -T | grep -i allowusers`. Only devices in your tailnet can reach `100.64.0.0/10` addresses, and they still need the key.

3. **Phone:** install Tailscale (Play Store or F-Droid), log in to the same tailnet and keep *Use Tailscale DNS settings* on. Then connect:

    ```bash
    ssh sergio@razorback                        # short MagicDNS name
    ssh sergio@razorback.tail1234.ts.net        # full name, if the short one doesn't resolve
    ```

!!! warning "This widens access beyond the LAN — by design"
    Over Tailscale the Mac is reachable from wherever the phone is. That's the point, but it also means losing the phone matters more: the key passphrase from step 4 is what stands between whoever has the phone and the Mac. If your tailnet uses a custom access policy (ACLs), it must allow the phone to reach the Mac on `tcp:22`; the default policy allows everything between your own devices.

After a reboot, check that the Mac is back on the tailnet before relying on it from afar — depending on the Tailscale app variant and FileVault, it may only reconnect once you've logged in at the Mac.

### Option C: Bonjour `.local` name

The Mac already advertises itself on the local network via Bonjour (mDNS). Its name:

```bash
scutil --get LocalHostName   # razorback → razorback.local
```

Change it in System Settings → General → Sharing → *Local hostname*. From the phone, on home Wi-Fi:

```bash
ssh sergio@razorback.local
```

Nothing to change in sshd: the connection comes from the phone's LAN address, which `AllowUsers sergio@192.168.1.0/24` already admits.

Limits:

- **Same network only.** mDNS is link-local multicast and doesn't cross VLANs, so the phone and the Mac must both be on the home Wi-Fi (VLAN 2).
- **The phone has to resolve `.local`.** Support on Android depends on the Android version and the app. If Termux or Termius says `Could not resolve hostname razorback.local`, use option B.
- **Name conflicts.** After sleep/wake the Mac occasionally renames itself to `razorback-2.local` when it thinks the name is taken. Check with `scutil --get LocalHostName` and set it back in Sharing.

## macOS-specific caveats

Things that just work on a Linux workstation but need attention on a Mac.

### Sleep

A sleeping Mac doesn't answer SSH, and there's no reliable way to wake it from the phone (Wake-on-LAN over Wi-Fi isn't supported; *Wake for network access* depends on an Apple TV/HomePod acting as sleep proxy). So the Mac has to stay awake:

- **During a session:** `pmset`'s `ttyskeepawake` (on by default) stops idle sleep while an SSH session is active.
- **Lid open, on power:** System Settings → Battery → Options… → **Prevent automatic sleeping on power adapter when the display is off** (same as `sudo pmset -c sleep 0`). The display still turns off; the system stays reachable.
- **Lid closed:** the Mac sleeps — unless it's in clamshell mode (power + external display). `sudo pmset -a disablesleep 1` stops even lid-close sleep; undo with `sudo pmset -a disablesleep 0`, and never leave it on with the Mac in a bag.

Check what's in effect with `pmset -g`; `sleep 1 (sleep prevented by …)` lists what's currently holding it awake.

### Files in Documents, Desktop and Downloads

macOS privacy protection (TCC) applies to SSH sessions: `ls ~/Documents` fails with `Operation not permitted`, as do `~/Desktop`, `~/Downloads`, iCloud Drive and external volumes. `~/Projects` and the rest of the home directory are unaffected.

The *Allow full disk access for remote users* toggle in Remote Login lifts this, but then the phone's key opens everything on the Mac. Leave it off unless you actually need those folders over SSH.

### Keychain

An SSH session can't use the login Keychain, even when you're logged in at the Mac. Tools that keep credentials there — `gh`, git's `osxkeychain` credential helper, Claude Code's login — fail or ask you to log in again when started from SSH. Unlock it for the session:

```bash
security unlock-keychain ~/Library/Keychains/login.keychain-db
```

This doesn't affect programs already running in a tmux session that was started from the Mac's own terminal — they belong to the GUI login and keep their Keychain access when you attach from the phone.

### PATH in one-shot commands

`ssh host <command>` runs a non-interactive zsh, which reads `~/.zshenv` but not `~/.zprofile` or `~/.zshrc`. Homebrew (`/opt/homebrew/bin`) and Nix paths are usually set up in the latter, so `ssh -t sergio@192.168.1.100 tmux new -A -s phone` fails with `zsh: command not found: tmux`. Either use the full path (`/opt/homebrew/bin/tmux`) or move the PATH setup (e.g. `eval "$(/opt/homebrew/bin/brew shellenv)"`) to `~/.zshenv`. Plain interactive logins aren't affected.

## Minimalistic Termux Configuration

```bash
pkg install bash-completion
pkg install git man vim zsh

chsh -s zsh          # needs terminal restart

pkg install openssh
pkg install termux-services 

sv-enable ssh-agent  # enable ssh-agent

termux-setup-storage # allow access to internal storage

cat <<EOT >>~/.ssh/config
# Linux workstation, reserved IP (step 6, option A)
Host 192.168.1.100 serenity
  HostName 192.168.1.100
  User sergio
  IdentityFile ~/.ssh/id_ed25519

# Mac over Tailscale, works anywhere (step 6, option B)
Host razorback
  HostName razorback.tail1234.ts.net
  User sergio
  IdentityFile ~/.ssh/id_ed25519

# Mac via Bonjour, home Wi-Fi only (step 6, option C)
Host razorback.local
  User sergio
  IdentityFile ~/.ssh/id_ed25519
EOT
```

Then `ssh serenity`, `ssh razorback` or `ssh razorback.local`. Replace `tail1234.ts.net` with your tailnet's domain (see [option B](#option-b-tailscale-magicdns)).

### Configure extra keys

Add extra `~`, `_` keys in addition to default ones:

```bash
cat <<EOT >>~/.termux/termux.properties

extra-keys = [ \
  ['ESC','/','~','-','HOME','UP','END','PGUP'], \
  ['TAB','CTRL','ALT','_','LEFT','DOWN','RIGHT','PGDN']
]
EOT
```

> Ref: https://mobile-coding-hub.github.io/termux/customisation/extra_keys/

## Tips

### ssh-agent on the phone

The agent only saves retyping the key passphrase; SSH works without it. In Termux, the `openssh` package ships helpers that are easier than `eval $(ssh-agent)`:

- `ssha sergio@192.168.1.100` — starts the agent if needed, asks for the passphrase once, then connects.
- Add `. source-ssh-agent` to `~/.bashrc` on the phone to start the agent with every Termux session.

Termius holds the key itself — there's no agent to run.

### Survive disconnects with tmux

Android kills or freezes backgrounded apps, which drops the SSH connection. You can make that rarer (next section), but not impossible, so make it harmless: run everything inside `tmux` on the workstation.

```bash
tmux new -A -s phone      # attach to session "phone", creating it if needed
```

Detach with ++ctrl+b++ ++d++; reconnect and run the same command to resume. To do it in one step:

- **Termux:** `ssh -t sergio@192.168.1.100 tmux new -A -s phone` (or with `ssha`) — wrap it in an alias. On macOS, mind the [PATH](#path-in-one-shot-commands).
- **Termius:** host settings → *Startup snippet* → `tmux new -A -s phone`.

A dropped SSH connection itself can't be resumed — you always open a new one and reattach to tmux. (Resuming the connection is what mosh is for, see below.)

### Attach to the session already open on the workstation

```bash
tmux ls                   # list sessions
tmux attach -t 0          # attach to session "0"
```

Both screens then show the same thing live, and typing on either goes to the same place.

**Window size:** a tmux window has one size at a time. With the tmux 3.x default (`window-size latest`), it follows whichever client typed last — so while you type on the phone, the workstation's terminal shows the window shrunk to phone size in a corner, with dots filling the rest. Full-screen programs redraw at phone width and look garbled. That's display only:

- Press any key on the workstation to resize back; ++ctrl+b++ ++r++ redraws if anything is still garbled.
- ++ctrl+b++ `:resize-window -A` forces the size of the largest attached client.

| Setup | Workstation | Phone |
| ----- | ----------- | ----- |
| Default (`window-size latest`) | Squashed while you use the phone | Fits |
| `set -g window-size largest` | Always full size | Shows only the top-left part; unusable for wide output |
| Linked session + separate window | Unaffected | Fits |

The linked session is the best setup for everyday use — it shares session `0`'s windows, but each client selects its own window:

```bash
tmux new -A -s phone -t 0
```

Create a phone-only window with ++ctrl+b++ ++c++. The workstation is only affected when both look at the same window.

The linked session also has its own environment. Attaching the phone directly with `tmux attach -t 0` replaces session `0`'s `DISPLAY`, ssh-agent socket and `SSH_CONNECTION` with the phone's, which breaks the clipboard and ssh-agent in new workstation panes. See [Troubleshooting](#new-workstation-panes-act-like-ssh-sessions-after-the-phone-attaches).

### Keep the app alive in the background

- **Battery:** Android Settings → Apps → Termux/Termius → Battery → **Unrestricted**. This matters most. Samsung, Xiaomi, etc. also have "sleeping apps" lists — remove the app there too.
- **Termux:** pull down the notification → **Acquire wakelock** (or run `termux-wake-lock`).
- **Termius:** keep its connection notification enabled; Android is more likely to kill apps it isn't showing as active.
- **Keepalives:** in the phone's `~/.ssh/config` (Termux) or the host's keep-alive setting (Termius):

    ```
    Host 192.168.1.100
        ServerAliveInterval 30
    ```

    This detects dead connections faster and helps with Wi-Fi power saving, but can't stop Android from killing the app.

!!! note
    On my Google Pixel 9 Pro XL, having optimized battery + tmux (on the server) does not terminate the connection.

### Swipe typing in Termux

Termux deliberately tells the keyboard to send keys one at a time, which disables swipe typing, autocorrect and suggestions in the terminal. It can't be turned off, but Termux has a built-in text input box for this:

1. Show the extra keys row if hidden: long-press **KEYBOARD** in the left drawer, or press Volume Up + Q.
2. **Swipe left on the extra keys row** — it becomes a normal text field where swipe typing works.
3. Type and press Enter; the text is sent to the terminal in one go.
4. Swipe right to get the extra keys back. With a long line in the field, swiping moves the cursor instead — drag the cursor to the start first.

This is ideal for prose (e.g. prompts to an AI agent running in tmux). For shell commands, the regular keyboard is better since ++tab++, arrows and ++ctrl++ live on the extra keys page.

### Mosh (optional)

[Mosh](https://mosh.org) survives the phone sleeping, the app being backgrounded and network changes, and reconnects instantly. Authentication still goes over SSH with your key. It's available in Termux (`pkg install mosh`) and Termius. The cost is one more package and one more firewall rule on the workstation:

=== "Linux"

    ```bash
    sudo apt install mosh
    sudo ufw allow from 192.168.1.0/24 to any port 60000:61000 proto udp comment 'mosh from home LAN'
    ```

=== "macOS"

    ```bash
    brew install mosh
    MOSH_SERVER="$(realpath "$(brew --prefix)/bin/mosh-server")"
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add "$MOSH_SERVER"
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp "$MOSH_SERVER"
    ```

    `mosh-server` isn't signed by Apple, so the application firewall asks for approval on the Mac's screen the first time it listens — with nobody there to click *Allow*, the phone just hangs at `mosh: Nothing received from server`. The commands above pre-approve it. The real path contains the version, so repeat them after `brew upgrade mosh`.

    The firewall rule is per app, not per source address — but `mosh-server` is only ever started through an SSH login, which `AllowUsers` already limits to the home LAN.

    `mosh-server` lives in `/opt/homebrew/bin`, which isn't on the non-interactive [PATH](#path-in-one-shot-commands). Point the client at it: `mosh --server=/opt/homebrew/bin/mosh-server sergio@192.168.1.100`.

Start with tmux and the battery setting; add mosh only if disconnects are still a problem.

### Termux Styling

- Install "Termux:Styling" plugin from F-Droid
- Long-tap anywhere on the terminal -> More... -> Style
- Select theme and font

## Troubleshooting

| Symptom | Likely cause |
| ------- | ------------ |
| Connection times out | Phone on mobile data instead of home Wi-Fi (or Tailscale off on either device); workstation got a different IP (check the [reservation](#option-a-dhcp-reservation), or connect by [name](#6-give-the-workstation-a-stable-address)); workstation asleep (on macOS, see [Sleep](#sleep)) |
| `Could not resolve hostname razorback.local` | The phone's Android version or app doesn't resolve `.local` names, or the phone isn't on the home Wi-Fi — use [Tailscale](#option-b-tailscale-magicdns). Also check the Mac didn't rename itself (`scutil --get LocalHostName`) |
| `Could not resolve hostname razorback` | Tailscale off on the phone, or *Use Tailscale DNS settings* disabled — or use the full `razorback.<tailnet>.ts.net` name |
| `Connection refused` | `sshd` not running: `systemctl status ssh` (Linux); Remote Login off (macOS) |
| `Permission denied (publickey)` | Wrong key on the phone, key not in `~/.ssh/authorized_keys`, wrong permissions on `~/.ssh` (`700`) or `authorized_keys` (`600`), or a user other than the one in `AllowUsers`. On macOS also: connecting from outside `192.168.1.0/24` (e.g. Tailscale without its range in `AllowUsers`), or the user not in Remote Login's *Allow access for* list |
| Host key changed warning | Expected after an OS reinstall only; otherwise don't connect, investigate |
| `Operation not permitted` in `~/Documents` etc. (macOS) | Privacy protection, see [Files in Documents, Desktop and Downloads](#files-in-documents-desktop-and-downloads) |
| `gh`/`git`/Claude Code not logged in over SSH (macOS) | Keychain locked in SSH sessions, see [Keychain](#keychain) |
| `command not found: tmux` with `ssh -t … tmux` (macOS) | Non-interactive PATH, see [PATH in one-shot commands](#path-in-one-shot-commands) |
| Nodes stop PXE booting after enabling `ufw` | PXE port rules missing, see [step 1](#1-enable-the-firewall) and [Troubleshooting PXE Boot](./troubleshooting_pxe_boot.md) |
| On the workstation, new tmux panes lose the clipboard and ssh-agent and show `user@host` | Phone attached directly to session `0`, see [below](#new-workstation-panes-act-like-ssh-sessions-after-the-phone-attaches) |

### New workstation panes act like SSH sessions after the phone attaches

After the phone runs `tmux attach -t 0`, panes opened on the **workstation** behave as if they were the phone's SSH login:

- Copying in tmux no longer reaches the system clipboard.
- The prompt and statusline show `user@host`.
- `git push` and other SSH commands ask for the key passphrase instead of using the agent.

**Cause:** tmux keeps one environment per *session*, not per screen. On every attach, it copies the variables listed in `update-environment` (`DISPLAY`, `XAUTHORITY`, `SSH_AUTH_SOCK`, `SSH_CONNECTION`, …) from the attaching client into the session, and removes the ones that client doesn't have. Attaching the phone to session `0` therefore replaces the desktop's values with the phone's SSH ones. Every new pane inherits them, whichever screen opens it, and so does the `xclip` process the copy bindings start (without `DISPLAY` it fails silently). Panes that already existed keep the environment they started with.

Detaching the phone does **not** undo this: tmux never restores the environment on detach. It only looks fixed if something re-attaches from the desktop afterwards, e.g. a new terminal tab running `tmux attach -t 0`.

**Check:**

```bash
tmux show-environment -t 0 | grep -E '^-?(DISPLAY|SSH_)'
```

`-DISPLAY` (removed) together with `SSH_CONNECTION=192.168.1.… 192.168.1.100 22` means session `0` has the phone's variables.

**Fix:**

- **Prevent it:** attach from the phone with a linked session, `tmux new -A -s phone -t 0` (see [above](#attach-to-the-session-already-open-on-the-workstation)). It shares session `0`'s windows but has its own environment, so session `0` keeps the desktop's values.
- **Repair it without detaching:** on the workstation, press ++ctrl+b++ and run `:switch-client -t 0`. This applies `update-environment` from the desktop client again. Panes opened while the phone's values were active keep them; close those.
