---
icon: material/format-list-checks
---

# :material-format-list-checks: ToDo

<div class="banner-image-wrapper">
  <img class="banner-image" src="https://images.unsplash.com/photo-1598791318878-10e76d178023?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" style="object-position: 50% 60%; height: 200px;">
</div>

- [ ] Update [architecture/overview](./architecture/overview.md) components
    - Basic diagram of code components and their relations
    - Description of components and their purpose
- [ ] Update [concepts/pxe-boot](../concepts/pxe-boot.md) with a visual "in-action" showcase of how it works, once it's in place

- [ ] Add up-to-date config files of C1111 and C3560 for reference
    - Can be placed in a separate note (probably don't even need to make it visible in nav menu) and referenced from [installation/network](../installation/network.md)

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
    10.10.10.11     thor
    10.10.10.12     heimdall
    10.10.10.20     mjolinr
    10.10.10.21     gungnir
    10.10.10.22     draupnir
    10.10.10.23     megingjord
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

    # bifrost (C3560 switch) in homelab vlan
    Host 10.10.10.2 bifrost
      User cisco
      KexAlgorithms +diffie-hellman-group14-sha1
      HostKeyAlgorithms +ssh-rsa

    # k8s cluster nodes in homelab vlan
    Host 10.10.10.1* 10.10.10.2* odin thor heimdall mjolnir draupnir gungnir megingjord
      User root
      StrictHostKeyChecking no
      LogLevel ERROR
      UserKnownHostsFile /dev/null
      GSSAPIAuthentication no # not supported on OS I use today for servers
    # storage nodes in homelab vlan
    Host 10.10.10.3* yggdrasil
      User root
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
    - [Stage 4 : C1111 Configuration](../installation/network.md#stage-4-implement-basic-firewall-rules-acls-on-c1111)

    ```
    ! --- Define ACL for traffic FROM Homelab Network ---
    ip access-list extended ACL_FROM_HOMELAB_NETWORK
     ! ...
     ! (Optional: Add permits if Homelab needs to SSH to router's Homelab SVI - local management when e.g. laptop is physically
     onnected to homelab network)
     103 remark Permit SSH from Homelab to router's Homelab SVI (local management)
     103 permit tcp 10.10.10.0 0.0.0.255 host 10.10.10.1 eq 22
     104 remark Permit SSH from Homelab to switch's Homelab SVI (local management)
     104 permit tcp 10.10.10.0 0.0.0.255 host 10.10.10.2 eq 22
     199 remark --- END ---
     ! ...
    exit
    ```
    - [ ] Limit permits to specific IP addresses instead of using `10.10.10.0` so that e.g. k8s servers couldn't ssh to Homelab's router or switch
