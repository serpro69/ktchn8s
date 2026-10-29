---
icon: material/crosshairs-question
title: SSH into the Workstation from Android
---

# :material-crosshairs-question: HowTo SSH into the workstation from an Android phone

This guide makes the workstation (the Ansible/PXE controller) reachable over SSH from an Android phone on the home network, without weakening the rest of the setup.

The security model:

- **LAN only.** `ufw` allows SSH from the home network (VLAN 2, `192.168.1.0/24`) and nothing else. No port forwarding on the router, ever. For access from outside the house, use Tailscale (`sudo tailscale up`) instead of exposing port 22.
- **Key only.** Password and keyboard-interactive auth are disabled, root login is disabled, and only one user is allowed.
- **The private key never leaves the phone.** It's generated on the phone; only the public key is copied to the workstation.

The commands below assume a Debian-family workstation (Pop!_OS 22.04 at the time of writing), user `sergio`, Wi-Fi interface `wlp0s20f3`, and the workstation IP `192.168.1.100`. Adjust as needed.

## 1. Enable the firewall

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

## 2. Write the sshd hardening config *before* installing the server

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

## 3. Install and verify the server

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

On the workstation:

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

Get the workstation's host key fingerprint **before** the first connection:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Then, with the phone on home Wi-Fi (mobile data is blocked by the firewall):

=== "Termux"

    ```bash
    ssh sergio@192.168.1.100
    ```

=== "Termius"

    New host: address `192.168.1.100`, username `sergio`, the key from step 4, no password.

On first connect the client shows a fingerprint and asks whether to trust it. Accept only if it matches the one above exactly — that comparison is the only thing proving the phone reached the workstation and not something else. If you accepted without comparing, check afterwards with `ssh-keygen -lF 192.168.1.100` in Termux.

The host key is regenerated if the OS is reinstalled, so the phone will warn about a changed key after a reinstall. That's expected only then; any other time, stop and investigate.

## 6. Keep the workstation's IP fixed

The phone's saved host only works if the workstation keeps `192.168.1.100`. Reserve it on the C1111 as described in [HowTo add DHCP reservations](./how_to_add_dhcp_reservations.md). Check the current binding:

```cisco
muspell#show ip dhcp binding 192.168.1.100
```

The type must be **Manual**, with client-id `01` + the Wi-Fi MAC in dotted notation (get the MAC with `ip -br link show wlp0s20f3`).

Also make sure the Wi-Fi MAC isn't randomized, or the reservation silently stops matching:

```bash
nmcli -f 802-11-wireless.cloned-mac-address con show "<wifi connection name>"
```

`--` (default) or `permanent` is fine; `random` or `stable` breaks the reservation.

!!! warning
    The committed router configs (`docs/installation/.files/muspell_startup-config_stage{3,4}.txt`) don't contain this reservation. Rebuilding the router from them loses it — see the ToDo list.

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

- **Termux:** `ssh -t sergio@192.168.1.100 tmux new -A -s phone` (or with `ssha`) — wrap it in an alias.
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

### Swipe typing in Termux

Termux deliberately tells the keyboard to send keys one at a time, which disables swipe typing, autocorrect and suggestions in the terminal. It can't be turned off, but Termux has a built-in text input box for this:

1. Show the extra keys row if hidden: long-press **KEYBOARD** in the left drawer, or press Volume Up + Q.
2. **Swipe left on the extra keys row** — it becomes a normal text field where swipe typing works.
3. Type and press Enter; the text is sent to the terminal in one go.
4. Swipe right to get the extra keys back. With a long line in the field, swiping moves the cursor instead — drag the cursor to the start first.

This is ideal for prose (e.g. prompts to an AI agent running in tmux). For shell commands, the regular keyboard is better since ++tab++, arrows and ++ctrl++ live on the extra keys page.

### Mosh (optional)

[Mosh](https://mosh.org) survives the phone sleeping, the app being backgrounded and network changes, and reconnects instantly. Authentication still goes over SSH with your key. It's available in Termux (`pkg install mosh`) and Termius. The cost is one more package and one more firewall rule on the workstation:

```bash
sudo apt install mosh
sudo ufw allow from 192.168.1.0/24 to any port 60000:61000 proto udp comment 'mosh from home LAN'
```

Start with tmux and the battery setting; add mosh only if disconnects are still a problem.

## Troubleshooting

| Symptom | Likely cause |
| ------- | ------------ |
| Connection times out | Phone on mobile data instead of home Wi-Fi; workstation got a different IP (check the reservation); workstation asleep |
| `Connection refused` | `sshd` not running: `systemctl status ssh` |
| `Permission denied (publickey)` | Wrong key on the phone, key not in `~/.ssh/authorized_keys`, wrong permissions on `~/.ssh` (`700`) or `authorized_keys` (`600`), or a user other than the one in `AllowUsers` |
| Host key changed warning | Expected after an OS reinstall only; otherwise don't connect, investigate |
| Nodes stop PXE booting after enabling `ufw` | PXE port rules missing, see [step 1](#1-enable-the-firewall) and [Troubleshooting PXE Boot](./troubleshooting_pxe_boot.md) |
