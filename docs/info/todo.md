---
icon: material/format-list-checks
title: ToDo
---

# :material-format-list-checks: ToDo

<div class="banner-image-wrapper">
  <img class="banner-image" src="https://images.unsplash.com/photo-1598791318878-10e76d178023?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" style="object-position: 50% 60%; height: 200px;">
</div>

- [ ] Apps/Services
    - [ ] [NextCloud](https://github.com/nextcloud/server)
    - [ ] (wip) `*arr` suite (<s>Radarr</s>, <s>Sonarr</s>, Readarr, Lidarr, Bazaar, <s>Prowlarr</s>, Profilarr)
        - [rreading-glasses](https://github.com/blampe/rreading-glasses) as metadata service
    - [x] Media streaming via Jellyfin / Jellyseer (shared with fam)
    - [Vaultwarden](https://github.com/dani-garcia/vaultwarden) 
    - [Mealie](https://github.com/mealie-recipes/mealie)
    - Ebook/Audiobook manager via [Kavita](https://github.com/Kareadita/Kavita) + [Audiobookshelf](https://github.com/advplyr/audiobookshelf)
        - Also evaluate [Calibre](https://github.com/kovidgoyal/calibre) vs Kavita
    - [Actual](https://github.com/actualbudget/actual) for budget management
    - [StirlingPDF](https://github.com/Stirling-Tools/Stirling-PDF) for PDF tools
    - [Syncthing](https://github.com/syncthing/syncthing) to sync some files between devices
        - Extremely useful if you own a PocketBook e-reader, which runs basically linux, so you can run Syncthing on it, meaning you... get... to... sync... your... eBooks... directly! 🤯😲😱
    - Whatever else I have starred in 'Self-Hosted' category on github that might be useful for home-use or to play around with
        - ... TBC

- [ ] Improve docs and add configuration script for new users
    - Ansible inventory config for [metal provisioning](../installation/production/metal.md)
        - Prompt user to edit the inventory file
        - Update docs - add sample inventory file contents for reference
    - Search-and-replace throughut the repo files:
        - Domain name
        - Github repository name
        - ... ?

- [ ] Automate [personal gitea user provisioning](../installation/post_install.md#gitea)

- [ ] Add [flaresolverr](https://trash-guides.info/Prowlarr/prowlarr-setup-flaresolverr/) to [media management stack](../guides/how_to_for_media_management.md)

- [ ] Stream/export sensor data from baremetal and visualize it in grafana
    - some potentially-useful resources to explore:
        - https://grafana.com/blog/2019/11/06/how-to-stream-sensor-data-with-grafana-and-influxdb/
        - https://grafana.com/blog/2021/08/12/streaming-real-time-sensor-data-to-grafana-using-mqtt-and-grafana-live/
        - https://grafana.com/blog/2024/01/03/how-to-create-alert-rules-to-monitor-sensor-data-with-grafana-and-raspberry-pi/
        - https://github.com/sbnb-io/sbnb/blob/main/README-GRAFANA.md
            - https://www.reddit.com/r/homelab/comments/1iuvbxp/fastest_way_to_start_bare_metal_server_from_zero/
        - https://grafana.com/grafana/dashboards/237-sensors/
        - https://github.com/ncabatoff/sensor-exporter

- [ ] Automate [firmware updates](../guides/how_to_update_firmware.md)

- [ ] Test zapping devices and make sure it works fine. Current version was tested on `draupnir`, which seemed to wipe the disk fine, but I had to do some [manual steps afterwards to create OSD on the new node](../guides/troubleshooting_rook_ceph.md#osd-zapping) once the node was re-provisioned and joined the cluster again.

- [ ] Install [ARA](https://github.com/ansible-community/ara) to record ansible executions

- [ ] Try [rke2](https://docs.rke2.io/networking/basic_network_options?CNIplugin=Cilium+CNI+Plugin) which includes by default Cilium and nginx-ingress + etcd db
    - ref: https://github.com/khuedoan/homelab/issues/179#issue-2875515756

- [ ] Replace kickstart with cloud-init
    - Kickstart is gonna end (?) and cloud-init is much more agnostic; also it can trigger ansible pull
    - Cloud-init can also be used across muppet OSes, not just Fedora, as is the case with kickstart
    - ref: https://github.com/khuedoan/homelab/issues/179#issue-2875515756

- [ ] Improve github+gitea workflow
    - One of the downsides is that I need to delete non-master (PR) branches on gitea manually (well, via cli, but still)
    - Maybe use a separate branch for gitea? E.g. `main`?
    - Or maybe use a separate remote for gitea (or for github? since gitea is technically considered "the origin"?) E.g. `gitea` (or `github`, for github repo origin)?
- [ ] Encrypt kubeconfig with sops so it can be committed to git

- [ ] Update [architecture/overview](../reference/architecture/overview.md) components
    - Basic diagram of code components and their relations
    - Description of components and their purpose

- [ ] Update [concepts/pxe_boot](../concepts/pxe_boot.md) with a visual "in-action" showcase of how it works, once it's in place

- [ ] Add up-to-date config files of C1111 and C3560 for reference
    - Can be placed in a separate note (probably don't even need to make it visible in nav menu) and referenced from [installation/production/network](../installation/production/network.md)

- [ ] Check that devices on Guest WiFi network (when Eero is in AP/Bridge mode!) are still isolated and cannot see or communicate with each other or the main network.
    - Eero in Bridge mode looses a lot of security related functionality (it becomes "greyed out" in the app also.) However, it seems that the guest network can still be enabled from the app. Hopefully that guest network is still isolated, but needs double-checking.
    - Some related links:
        - <https://www.reddit.com/r/eero/comments/g0mjqi/guest_network_and_general_routing_questions/>

- [ ] When storing terraform state locally one needs to think about where/how to back it up. An alternative would be to use terraform cloud or opentofu TACOS, which are paid services (Plus your state is stored on someone else's computer, and hence should be [encrypted](https://opentofu.org/docs/language/state/encryption/))
    - What can be alternatives to storing the state locally?
        - Initial provisioning can be done with local state
            - Once the cluster is up and running, we can host [Atlantis](https://www.runatlantis.io/docs/installation-guide.html) and migrate the state to it.
            - As an added benefit, this makes it possible to [run terraform from PRs](https://www.runatlantis.io/guide.html#overview-%E2%80%93-what-is-atlantis)
        - Store/commit [sops](https://github.com/getsops/sops)-encrypted state. Run `terraform` with a script/make wrapper that decrypts the state before running `terraform` commands, and re-encrypts it at the end.

- [ ] Configure `/etc/hosts` on local controller machine as part of `metal` provisioning
    ```
    # midgard.local homelab
    # network devices
    10.10.10.1      muspell
    10.10.10.2      bifrost
    # k8s cluster
    10.10.10.10     odin
    10.10.10.11     freyja
    10.10.10.12     heimdall
    10.10.10.20     mjolinr
    10.10.10.21     gungnir
    10.10.10.22     draupnir
    10.10.10.23     megingjord
    10.10.10.24     hofund
    10.10.10.25     gjallarhorn
    10.10.10.26     brisingamen
    # storage devices
    10.10.10.30     yggdrasil
    ```

- [ ] Configure `~/.ssh/config` on local controller machine as part of `metal` provisioning
    ```
    Host 10.10.10.*
      StrictHostKeyChecking no
      LogLevel ERROR
      UserKnownHostsFile /dev/null

    # muspell (C1111 router) in homelab vlan
    Host 10.10.10.1 muspell
      User cisco
      PasswordAuthentication yes

    # bifrost (C3560 switch) in homelab vlan
    Host 10.10.10.2 bifrost
      User cisco
      PasswordAuthentication yes
      KexAlgorithms +diffie-hellman-group14-sha1
      HostKeyAlgorithms +ssh-rsa

    # k8s cluster nodes in homelab vlan
    Host 10.10.10.1* 10.10.10.2* odin freyja heimdall mjolnir draupnir gungnir megingjord hofund brisingamen gjallarhorn
      User root
      IdentityFile ~/.ssh/homelab_id_ed25519
      StrictHostKeyChecking no
      LogLevel ERROR
      UserKnownHostsFile /dev/null
      GSSAPIAuthentication no # not supported on OS I use today for servers

    # storage nodes in homelab vlan
    Host 10.10.10.3* yggdrasil
      User root
      IdentityFile ~/.ssh/homelab_id_ed25519
      StrictHostKeyChecking no
      LogLevel ERROR
      UserKnownHostsFile /dev/null
    ```

- [ ] Check if server is up before sending WoL magic packets

- [ ] Ask before proceeding when running `make bootstrap` in `metal` provisioning
    - The server prefers to boot from Network when woken up, which will erase all data on the disk and re-install the OS
    - Ask the user for confirmation before proceeding.
        - Mention `make wake` alternative which can be used just to wake up the machines

- [ ] Consider restricting ssh access from homelab to router/switch SVI to specific IPs
    - [Stage 4 : C1111 Configuration](../installation/production/network.md#stage-4)

    ```
    ! --- Define ACL for traffic FROM Homelab Network ---
    ip access-list extended ACL_FROM_HOMELAB_NETWORK
     ! ...
     ! (Optional: Add permits if Homelab needs to SSH to router's Homelab SVI - local management when e.g. laptop is physically connected to homelab network)
     103 remark Permit SSH from Homelab to router's Homelab SVI (local management)
     103 permit tcp 10.10.10.0 0.0.0.255 host 10.10.10.1 eq 22
     104 remark Permit SSH from Homelab to switch's Homelab SVI (local management)
     104 permit tcp 10.10.10.0 0.0.0.255 host 10.10.10.2 eq 22
     199 remark --- END ---
     ! ...
    exit
    ```
    - [ ] Limit permits to specific IP addresses instead of using `10.10.10.0` so that e.g. k8s servers couldn't ssh to Homelab's router or switch

- [ ] Provision cisco devices with Ansible
    - [cisco.ios collection](https://docs.ansible.com/ansible/latest/collections/cisco/ios/index.html)

- Explore Enchanced Power Saving Mode in BIOS
    - Newer Lenovo machines support enhanced power saving mode which lowers power consumption during power-off.
    - [x] Won't do: WoL is not supported!

- [ ] Configure and document BIOS -> Power -> After Power Loss
    - What option is better for my use-cases? Make sure it's configured everywhere and document it.

- [x] Figure out why dnf is very slow
    - References:
        - <https://unix.stackexchange.com/questions/496775/extremely-slow-dnf>
        - <https://ostechnix.com/how-to-speed-up-dnf-package-manager-in-fedora>
    - Seems like adding `fastestmirror=True` to `/etc/dnf/dnf.conf` helps at least to some degree

- [ ] Setup pi-hole on the cluster
