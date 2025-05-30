---
icon: material/lan
---

# :material-lan: Network Configuration

!!! warning
    The following describes my current network components and configurations. Don't blindly copy-paste, but instead use this as a learning point and adjust to your needs, especially if you're using different hardware components.

!!! info
    For an overview of the network setup refer to [Network Architecture](../reference/architecture/network.md) page.

## Hardware Requirements

- Cisco C1111-8P Router
- Cisco C3560-GS-8P Switch
- Eero 6 Router
- Serial Console Cable
- "Controller" PC
    - Any OS can be used, but since I work on Linux I won't provide serial console connectivity specifics for other OSes (which can also easily be found online). PRs with docs improvements are always welcome!

## Serial Console Connection

### Software

(In order of preference based on own brief experience)

- [minicom](https://help.ubuntu.com/community/Minicom)
    - easy to get started/configure with self-explanatory built-in help menu
    - seems to have some extra useful functionality
    - _NB! default `Ctrl-A` shortcut conflicts with my current `tmux` modifier key, hence I usually use `minicom` outside of `tmux`_
- [screen](https://www.gnu.org/software/screen/manual/screen.html)
- [gtkterm](https://github.com/wvdakker/gtkterm)
    - standalone terminal with easy UI/configurations, but doesn't seem to bring much more value compared to `minicom`
    - only tried it briefly

### Steps

- Install `minicom` (alternatively install `screen` or `gtkterm`, whichever you like best)
    - On ubuntu: `sudo apt install minicom`
- Connect the serial cable to the switch/router and PC
- Determine the port of the serial cable: `sudo dmesg | grep -i tty`
    - Let's assume the device port was `ttyUSB0`
- Follow the [minicom configuration guide](../guides/how_to_configure_minicom.md) to configure it
- Start minicom: `sudo minicom`
    - Alternatively, using screen: `sudo screen /dev/ttyUSB0 9600`

### References

- [Troubleshoot and Apply Correct Terminal Emulator Settings for Console Connections](https://www.cisco.com/c/en/us/support/docs/storage-networking/management/217970-troubleshoot-and-apply-correct-terminal.html)

### Troubleshooting

#### `[screen is terminating]` error

**tldr;** either add your user to `dialout` group, or run `screen` with `sudo`

Long version based on this [unix.stackexchange answer](https://unix.stackexchange.com/a/529120):

Does the user account have the permission to use `/dev/ttyUSB0`? To find out, please run `ls -l /dev/ttyUSB0`. The output might look like this:

```
$ ls -l /dev/ttyUSB0 
crw-rw----+ 1 root dialout 166, 0 Jul  9 08:55 /dev/ttyUSB0
```

The characters at the left-most column are the file type and permissions information:

- The first character is `c`, indicating a character-based device.
- The last character is `+`, indicating that there is an Access Control List (ACL for short) on this device node, specifying further access rules. This is important, because it changes how the other permissions are interpreted.
- The characters 2-4 are a three-letter group `rw-` indicating permissions for the file owner, which is `root` as indicated in the third column.
- The second group of three letters (`rw-` again) would classically indicate permissions applicable to the _group_ of users the file is assigned to. In this case, the group is `dialout` as indicated in the fourth column. **But because this file has an ACL, the meaning is different:** with an ACL in effect, it just indicates the highest permissions granted to a specific user or group that is not the file owner - but you cannot know which user or group it is.
- The third group of three letters (`---`) indicate access permissions for everyone else - if it's all dashes, it means no access is allowed.
- The last character is `+`, indicating that there is an Access Control List (ACL for short) on this device node, specifying further access rules.

Lastly, the ACL can be viewed with `getfacl /dev/ttyUSB0`. The output might look something like this:

```bash
getfacl /dev/ttyUSB0 
```

```
getfacl: Removing leading '/' from absolute path names
# file: dev/ttyUSB0
# owner: root
# group: dialout
user::rw-
user:sddm:rw-
group::rw-
mask::rw-
other::---
```

Basically, it repeats the traditional non-ACL file permissions and allows specifying extra permissions for any number of users and groups. In this case, there is an extra line `user:sddm:rw-` indicating both read and write access to user `sddm`, which is the user account the GUI login manager process `sddm` is currently running as. And there's also the `group::rw-` line that confirms that the classic `dialout` group has full read/write access to this file - this information was hidden from the classic `ls -l` output when an ACL was applied to this device node.

The fact that an ACL grants permissions to `sddm` indicates that this OS is probably configured to automatically grant access to local serial ports if you log in locally using the GUI login dialog. The ACL would be automatically changed to match the logged-in user, and back to `sddm` when the user logs out. If such an ACL is not present, then your distribution might not use such an automatic permissions mechanism.

The group name `dialout` is historical, because serial ports used to be used with modems. But if a device is assigned to a special group like this, it indicates the distribution is probably configured to manage access to serial ports using the `dialout` group. So in this example, you might want to add your user account to the `dialout` group. You'll need root/superuser access to do that:

```bash
sudo usermod -a -G dialout eric
```

New group memberships take effect at next login, so you'll need to log out and back again. Alternatively run:

```bash
newgrp dialout
```

Because the `/dev` filesystem is a virtual, RAM-based filesystem, all the device nodes are created from scratch every time the system boots. Because of this, trying to change the permissions of the actual device nodes would be futile; your changes would be forgotten when you shut down the system. Instead, the default permissions for the devices use specific groups, for the express purpose of allowing the administrators to use group memberships to grant specific users access to specific types of devices: using those groups as intended is probably the easiest way to solve your problem.

#### No (slow) console output

!!! tip
    Usually console output problems are related to faulty or poor-quality cables.

- Check the cable connection and ensure that the serial console cable is properly connected to both the switch/router and the PC.
- Try to reset the cable.

References:

- <https://www.reddit.com/r/homelab/comments/nyacjw/no_console_output_on_cisco_switch/>
- <https://community.cisco.com/t5/switching/blank-screen-and-no-console-access-on-cisco-switch/td-p/2964716>

## Configuration Rollout

!!! info
    I've broken down the network configuration rollout into several stages which allowed me to to work in small, incremental iterations and test things easier w/o introducing big updates.

### Stage 1 - Basic Internet Connectivity via C1111 and Eero

* **Goal:** Home devices (laptop, phone) can connect to the Eero (in bridge mode) and access the internet. The C1111 handles routing, NAT, and DHCP for the home network.

#### C1111 Configuration Steps

- **Initial Access & Factory Reset (Optional but Recommended):**
    * Connect via console cable.
    * If starting fresh:

        ```cisco
        enable
        write erase
        reload
        ```

        (After reload, when prompted `Would you like to enter the initial configuration dialog? [yes/no]:`, enter `no`.)

- **Basic Device Setup:**

    ```cisco
    enable
    configure terminal

    hostname muspell                        ! Muspelheim in Norse mythology is the primordial realm of fire, according to Snorri, 
                                            ! which was instrumental in the creation of the world

    enable secret <your_strong_password>

    username <your_admin_user> privilege 15 secret <your_admin_password>

    line con 0
     login local
     logging synchronous                    ! Prevents console messages from interrupting typing
    exit

    line vty 0 4
     login local
     transport input ssh
    exit

    ip domain name midgard.local            ! Or your preferred local domain

    crypto key generate rsa modulus 2048    ! For SSH

    service password-encryption             ! Encrypts plaintext passwords in the config

    no ip http server                       ! Disable HTTP management interface
    no ip http secure-server                ! Disable HTTPS management interface

    clock timezone UTC 0 0                  ! Or your local timezone
    ! ntp server <ip_address_of_ntp_server> ! Optional, for accurate time on the router
    ```

- **WAN Interface Configuration (Assuming `GigabitEthernet0/0/0` is a dedicated routed WAN port):**

    ```cisco
    interface GigabitEthernet0/0/0
     description WAN_to_ISP_Modem
     ip address dhcp                ! Assuming the ISP modem provides an IP via DHCP
     ip nat outside
     negotiation auto               ! Usually default, but good to ensure
     no shutdown
    exit
    ```

    * **Note:** The command `ip address dhcp` should work if your ISP modem is providing DHCP. If your ISP requires PPPoE, the configuration here would be very different (involving a Dialer interface).

    * **If `GigabitEthernet0/0/0` is _not_ a dedicated WAN port and is actually part of the switch block (unlikely for `0/0/x` naming but possible on some variants):**
        * You would _not_ configure `ip address dhcp` directly. Instead, you'd create a "WAN VLAN" (e.g., VLAN 99), assign this physical port to VLAN 99, create `interface Vlan99`, and put `ip address dhcp` and `ip nat outside` on `interface Vlan99`.
        * _This is a crucial distinction based on your router's specific hardware port types._

- **Home Network LAN Configuration (_using integrated switchports_):**

    * First, create the VLAN globally:

        ```cisco
        vlan 2
         name HOME_NETWORK
        exit
        ```

    * Next, create the Switched Virtual Interface (SVI) for Layer 3 routing for this VLAN:

        ```cisco
        interface Vlan2
         description Gateway_for_Home_Network_192.168.1.0
         ip address 192.168.1.1 255.255.255.0
         ip nat inside
         no shutdown
        exit
        ```

    * Then, assign a physical switchport to this VLAN (e.g., `GigabitEthernet0/1/0` for the Eero):

        ```cisco
        interface GigabitEthernet0/1/0
         description LAN_to_Eero_AP_VLAN2
         switchport mode access      ! This port will only carry traffic for one VLAN
         switchport access vlan 2  ! Assigns this port to VLAN 2
         spanning-tree portfast    ! Recommended for edge ports connected to end devices/APs
         no shutdown
        exit
        ```

- **DHCP Server Configuration for Home Network (VLAN 2):**

    ```cisco
    ip dhcp excluded-address 192.168.1.1 192.168.1.9  ! Reserve IPs for router, Eero mgmt, etc.
    !
    ip dhcp pool HOME_POOL_VLAN2
     network 192.168.1.0 255.255.255.0
     default-router 192.168.1.1         ! Gateway for clients in this pool
     dns-server 1.1.1.1 8.8.8.8         ! Start with public DNS servers
     lease 1                            ! Lease time in days (e.g., 1 day)
     domain-name midgard.local          ! (Optional: provides domain suffix to clients.) Midgard is the realm of humans in Norse mythology
    exit
    ```

- **Network Address Translation (NAT) Configuration:**

    * Define an access list to identify traffic from your Home Network that needs to be NATted:

        ```cisco
        ip access-list standard ACL_NAT_HOME_NETWORK
         permit 192.168.1.0 0.0.0.255
        exit
        ```

    * Apply NAT, translating addresses from `ACL_NAT_HOME_NETWORK` to the IP address of the `GigabitEthernet0/0/0` (WAN) interface:

        ```cisco
        ip nat inside source list ACL_NAT_HOME_NETWORK interface GigabitEthernet0/0/0 overload
        ```

        * **Note:** This assumes `GigabitEthernet0/0/0` is the correct NAT outside interface. If your WAN setup uses an SVI (e.g., `interface Vlan99` because you're using a switchport for WAN), then that SVI would be specified here instead of the physical interface.

- **Default Route to the Internet:**

    * If `ip address dhcp` on the WAN interface (`GigabitEthernet0/0/0`) successfully obtains an IP and a default gateway from your ISP modem, a default route should be automatically installed. You can verify with `show ip route`.

    * If a default route is not automatically installed, or if you had a static public IP, you'd add it manually (this is less common for typical home ISP DHCP setups):

        ```cisco
        ! ip route 0.0.0.0 0.0.0.0 <IP_of_ISP_Modem_Gateway_on_WAN_subnet>
        ! or potentially just:
        ! ip route 0.0.0.0 0.0.0.0 GigabitEthernet0/0/0
        ```

        For now, we rely on DHCP to provide the route.

- **Save Configuration:**

    ```cisco
    end
    write memory
    ! or
    ! copy running-config startup-config
    ```

#### Eero Configuration Steps

- Physically connect Eero WAN port to `GigabitEthernet0/1/0` on C1111.
- Factory reset Eero if needed.
    * Note: I didn't perform a reset or anything, keept using existing configuration and mobile eero app as it was
    * Follow Eero app setup instructions.
- Configure Eero in Access Point mode:
    * In order for eeros to be used as Access Points, you will need to wire one eero to your existing router and set it up in Double NAT. Once the setup is complete, you can go to the Settings--Network Settings--DHCP & NAT and select Bridge. Let the system reboot and the eeros will no longer perform DHCP.
    * tldr: connect the Eero to C1111 g0/1/0 port, open eero app and wait for it to show that it has internet connection, then change it to bridge mode, wait for it to restart and show as online again in the app, profit
    * ref: <https://www.reddit.com/r/eero/comments/uuuvdc/comment/i9hkazz/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button>
- Configure WiFi SSID and password (if wasn't configured previously)
    * Since I didn't reset the Eero router, I could just keep using the existing SSID w/o any modifications needed


#### Verification Steps

- On C1111:
    * `show ip interface brief`:
        * `GigabitEthernet0/0/0` should be `up`, `up`, method `DHCP`, status `administratively down` if `no shutdown` was missed. IP should be public.
        * `Vlan2` should be `up`, `up`, with IP `192.168.1.1`.
        * `GigabitEthernet0/1/0` should be `up`, `up`.
    * `show vlan brief`: Should show VLAN 2 "HOME_NETWORK" active with port `Gi0/1/0` assigned.
    * `show ip route`: Crucially, look for a default route (e.g., `S* 0.0.0.0/0 [1/0] via <ISP_GATEWAY_IP>` or `S* 0.0.0.0/0 is directly connected, GigabitEthernet0/0/0` if DHCP sets it that way).
    * `show ip nat translations`: Will be empty initially, but will populate as devices NAT out.
    * `ping 1.1.1.1 source Vlan2` (or `ping 1.1.1.1` if that doesn't work, try pinging from global exec mode).
- Connect a laptop/phone to the Eero's WiFi.
- Verify laptop/phone gets an IP from `192.168.1.x` range, gateway `192.168.1.1`, DNS `1.1.1.1`/`8.8.8.8`.
- Verify laptop/phone can browse the internet.
- On C1111, `show ip nat translations` should now show entries.

#### Key Points

* The C1111-8P acts like a router with an integrated switch.
* You define VLANs globally (`vlan <id>`).
* You create SVIs (`interface Vlan<id>`) to give those VLANs Layer 3 gateway IPs.
* You assign the integrated physical switchports (`GigabitEthernet0/1/x`) to these VLANs in access mode.
* The dedicated WAN port (`GigabitEthernet0/0/0`) is typically a routed port, not a switchport.

### Stage 2 - Setup Homelab VLAN and Basic Connectivity to C3560 Switch

* **Goal:** The C3560 switch is connected to the C1111, and the Homelab VLAN (`VLAN 10`) is active on the C1111. The C3560 can be managed via its IP on VLAN 10, and devices in VLAN 10 (including the switch itself) can potentially reach the internet if NAT is updated.

* **Physical Connection:** Connect a network cable from C1111's `GigabitEthernet0/1/1` port to C3560's `GigabitEthernet0/9` port (or your chosen uplink port on the C3560).

#### C1111 Configuration Steps

```cisco
! Enter global configuration mode
configure terminal

! --- Homelab VLAN Definition ---
! Create VLAN 10 globally on the router
vlan 10
 ! Assign a descriptive name to VLAN 10
 name HOMELAB_SERVERS
exit

! --- Homelab Switched Virtual Interface (SVI) for Layer 3 ---
! Create a virtual interface representing VLAN 10 for routing
interface Vlan10
 ! Add a description for this interface
 description Gateway_for_Homelab_Network_10.10.10.0
 ! Assign an IP address and subnet mask to this SVI. This will be the gateway for devices in VLAN 10.
 ip address 10.10.10.1 255.255.255.0
 ! Include traffic from this interface in NAT (Network Address Translation)
 ! so devices in VLAN 10 can access the internet via the router's WAN IP.
 ip nat inside
 ! Ensure the interface is administratively up
 no shutdown
exit

! --- LAN Port Configuration for Connection to C3560 Switch ---
! Select the physical switchport on the C1111 that connects to the C3560
interface GigabitEthernet0/1/1
 ! Add a description for this port
 description Link_To_C3560_Homelab_Switch
 ! Set the port to access mode, meaning it will carry traffic for a single VLAN
 switchport mode access
 ! Assign this access port to VLAN 10
 switchport access vlan 10
 ! Enable PortFast: causes a Layer 2 access port to enter the forwarding state immediately,
 ! bypassing the listening and learning states. Use only on ports connected to end devices or
 ! to another switch where no loops are expected through this port.
 spanning-tree portfast
 ! Ensure the physical port is administratively up
 no shutdown
exit

! --- Update NAT Access Control List (ACL) ---
! If you want Homelab devices to have internet access immediately.
! First, remove the old NAT ACL if it was specific to only the Home Network.
! (Check your running config for the exact name you used in Stage 1, e.g., ACL_NAT_HOME_NETWORK)
no ip access-list standard ACL_NAT_HOME_NETWORK

! Create a new (or modify existing) standard ACL to permit traffic from BOTH Home and Homelab networks for NAT.
ip access-list standard ACL_NAT_TRAFFIC_ALL_LANS
 ! Permit traffic from the Home Network (192.168.1.0/24)
 permit 192.168.1.0 0.0.0.255
 ! Permit traffic from the Homelab Network (10.10.10.0/24)
 permit 10.10.10.0 0.0.0.255
exit

end

! Clear active NAT translations using older NAT acl rule.
! You need to clear these active translations before you can remove or modify the NAT rule.
! `*`: This clears all dynamic NAT translations. You can be more specific if needed, but for a homelab environment during setup, clearing all is usually fine and quickest.
! NB! This will temporarily drop any active internet sessions for devices being NATted by this rule.
clear ip nat translation *

configure terminal

! --- Update NAT Rule to use the new/updated ACL ---
! First, remove the old NAT rule that used the old ACL.
! (The interface GigabitEthernet0/0/0 is assumed to be your WAN interface)
no ip nat inside source list ACL_NAT_HOME_NETWORK interface GigabitEthernet0/0/0 overload

! Apply the new NAT rule using the updated ACL that includes both LANs.
ip nat inside source list ACL_NAT_TRAFFIC_ALL_LANS interface GigabitEthernet0/0/0 overload

! Exit configuration mode
end

! Save the running configuration to the startup configuration
copy running-config startup-config
! or "write memory"
```

#### C3560 Configuration Steps (Minimal Initial Setup)

* Connect to the C3560 via console cable.

* If it has a previous configuration you want to wipe:

    ```cisco
    enable
    write erase
    reload
    ```

    (Answer "no" to initial configuration dialog if it appears after reload).

* Configure the switch with the following commands:

```cisco
! Enter global configuration mode
configure terminal

! --- Basic Device Setup ---
! Set the hostname for the switch
hostname bifrost

! Set the enable secret password (for privileged EXEC mode)
enable secret <your_strong_switch_password>

! Create a local user for login (more secure than just enable password)
username <your_admin_user> privilege 15 secret <your_admin_password_for_switch>

! Configure console line for local login
line con 0
 login local
 logging synchronous ! Prevents console messages from interrupting typing
exit

! Configure VTY lines (for Telnet/SSH) for local login
line vty 0 4 ! For the first 5 VTY lines
 login local
 transport input ssh ! Prefer SSH over Telnet. Telnet can be "transport input telnet" or "transport input all"
exit
! (To enable SSH, you'll also need to configure a domain name and generate crypto keys, see below)

service password-encryption

! Set the IP domain name (required for generating SSH keys)
ip domain name midgard.local

! Generate RSA crypto keys for SSH
crypto key generate rsa modulus 2048 ! 1024 is usually sufficient for lab, 2048 for better security

! --- Homelab VLAN Definition on Switch ---
! Create VLAN 10 on the switch
vlan 10
 ! Assign a descriptive name to VLAN 10 (should match C1111 for clarity)
 name HOMELAB_SERVERS
exit

! --- Switch Virtual Interface (SVI) for Management ---
! Create a virtual interface representing VLAN 10 for switch management
interface Vlan10
 ! Add a description for this management interface
 description Management_IP_for_Switch_VLAN10
 ! Assign an IP address and subnet mask to this SVI. This IP is used to manage the switch.
 ip address 10.10.10.2 255.255.255.0
 ! Ensure the interface is administratively up
 no shutdown
exit

! --- Set Default Gateway for Switch Management ---
! Configure the default gateway for the switch itself (for management traffic, e.g., NTP, AAA, SSH from other networks)
! This IP should be the SVI IP of VLAN 10 on the C1111 router.
ip default-gateway 10.10.10.1

! --- Port Configuration for Uplink to C1111 Router ---
! Select the physical port on the C3560 that connects to the C1111
interface GigabitEthernet0/9 ! Or your chosen uplink port (e.g., Gi0/1 if it's a different model/slot)
 ! Add a description for this port
 description Uplink_To_C1111_Router_VLAN10
 ! Set the port to access mode
 switchport mode access
 ! Assign this access port to VLAN 10
 switchport access vlan 10
 ! (PortFast might not be strictly necessary here if this is an uplink to another switch/router,
 !  but for a simple P2P link in access mode to the router's access port, it's generally safe.
 !  If you were trunking, you would not use PortFast on a trunk to another switch.)
 ! spanning-tree portfast
 ! Ensure the physical port is administratively up
 no shutdown
exit

! (Optional: Configure other switchports for future devices in VLAN 10 later in Stage 3)
! Example:
! interface range GigabitEthernet0/1 - 8
!  switchport mode access
!  switchport access vlan 10
!  spanning-tree portfast
!  no shutdown
! exit

! Exit configuration mode
end

! Save the running configuration to the startup configuration
copy running-config startup-config
! or "write memory"
```

#### (Optional) Controller PC ssh configuration

- Ensure the following ssh configuration is present in `~/.ssh/config`:

```
# 'muspell' C1111 router in homelab vlan
Host 10.10.10.1 muspell
  User <your_admin_user>

# 'bifrost' C3560 switch in homelab vlan
Host 10.10.10.2 bifrost
  User <your_admin_user>
  KexAlgorithms +diffie-hellman-group14-sha1
  HostKeyAlgorithms +ssh-rsa
```

- See ['no matching key exchange method found'](#ssh-error-no-matching-key-exchange-method-found) and ['no matching host key type found'](#ssh-error-no-matching-host-key-type-found) ssh troubleshooting info for more details.

#### Verification Steps

- **Physical Connectivity:** Ensure the cable between C1111 (`Gi0/1/1`) and C3560 (`Gi0/9`) is securely connected.
- **On C1111 Router:**
    * `show ip interface brief`:
        * `Vlan10` should be `up`, `up`, protocol `up`, IP `10.10.10.1`.
        * `GigabitEthernet0/1/1` should be `up`, `up`, protocol `up`.
    * `show vlan brief`: Should show VLAN 10 "HOMELAB_SERVERS" active with port `Gi0/1/1` assigned.
    * `show cdp neighbors`: You should see the C3560-Homelab-Switch listed on `GigabitEthernet0/1/1`.
    * `ping 10.10.10.2`: Try pinging the C3560's management IP. This tests L3 connectivity from C1111 to C3560 SVI.
- **On C3560 Switch:**
    * `show ip interface brief`:
        * `Vlan10` should be `up`, `up`, protocol `up`, IP `10.10.10.2`.
        * `GigabitEthernet0/9` (or your uplink port) should be `up`, `up`, protocol `up`.
    * `show vlan brief`: Should show VLAN 10 "HOMELAB_SERVERS" active with port `Gi0/9` (uplink) assigned.
    * `show cdp neighbors`: You should see the C1111-Router listed on `GigabitEthernet0/9`.
    * `ping 10.10.10.1`: Try pinging the C1111's SVI for VLAN 10. This tests L3 connectivity from C3560 to C1111.
    * `ping 1.1.1.1` (or any public IP): This tests if the C3560 can reach the internet (requires the NAT update on C1111 to be effective).
- **From a device on your Home Network (e.g., the controller laptop on `192.168.1.x`):**
    * `ping 10.10.10.1`: Ping the C1111's Homelab VLAN gateway.
    * `ping 10.10.10.2`: Ping the C3560 switch's management IP.
        * _Note:_ This inter-VLAN ping will work because the C1111 routes between directly connected networks (`Vlan2` and `Vlan10`). No specific ACLs are blocking it yet (those come in Stage 4).
    * Try to SSH to `10.10.10.1` (the C1111 router) using the admin credentials you set up for the router.
    * Try to SSH to `10.10.10.2` (the C3560 switch) using the admin credentials you set up for the switch.

### Stage 3 - Connect k8s Nodes and NAS to Homelab VLAN & Enable DHCP

* **Goal:** K8s nodes and NAS are physically connected to the C3560, obtain IPs (or have static IPs configured correctly) in the `10.10.10.0/24` range, and can access the internet (assuming NAT on C1111 from Stage 2 is working).

* **Physical Connection:** Connect your k8s nodes and NAS device to available ports on the C3560 switch (e.g., `GigabitEthernet0/1` through `GigabitEthernet0/8`).

#### C1111 Configuration Steps

```cisco
! Enter global configuration mode
configure terminal

! --- DHCP Server Configuration for Homelab Network (VLAN 10) ---
! This pool will serve IP addresses to devices in the Homelab VLAN.

! Define a range of IP addresses to EXCLUDE from being dynamically assigned by DHCP.
! These are typically for static assignments (router SVI, switch management IP, servers, MetalLB range, etc.)
ip dhcp excluded-address 10.10.10.1 10.10.10.9      ! Exclude C1111's Vlan10 SVI (10.10.10.1) and C3560's Mgmt IP (10.10.10.2) and reserve a few more addresses for similar purposes (APs etc)

! Exclude IPs you plan to assign to your k8s nodes and NAS.
! Example:
!   Control: 10.10.10.1x
!   Workers: 10.10.10.2x
!   Storage: 10.10.10.3x
!   MetalLb: 10.10.10.4x - 10.10.10.6x
ip dhcp excluded-address 10.10.10.10 10.10.10.19    ! k8s control plane nodes
ip dhcp excluded-address 10.10.10.20 10.10.10.29    ! k8s worker nodes
ip dhcp excluded-address 10.10.10.30 10.10.10.39    ! storage nodes

! Exclude the IP range you plan to use for MetalLB (for K8s LoadBalancer services).
! This range should NOT overlap with any static or DHCP-assigned IPs.
ip dhcp excluded-address 10.10.10.40 10.10.10.69    ! metal lb range

! Define the DHCP pool for the Homelab network
ip dhcp pool HOMELAB_POOL_VLAN10
 ! Specify the network address and subnet mask for this DHCP pool
 network 10.10.10.0 255.255.255.0
 ! Specify the default gateway IP address for DHCP clients (C1111's SVI for VLAN 10)
 default-router 10.10.10.1
 ! Specify DNS server(s) for DHCP clients.
 ! Start with public DNS. Later, you might change this to your internal DNS server (e.g., Pi-hole).
 dns-server 1.1.1.1 8.8.8.8
 ! Specify the domain name to be provided to DHCP clients (should match global ip domain name for consistency)
 domain-name midgard.local
 ! Specify the lease duration for IP addresses (e.g., 1 day)
 lease 1
exit

! Exit configuration mode
end

! Save the running configuration to the startup configuration
copy running-config startup-config
! or "write memory"
```

#### C3560 Configuration Steps

```cisco
! Enter global configuration mode
configure terminal

! --- Port Configuration for K8s Nodes and NAS ---
! Configure the switchports that your K8s nodes and NAS will connect to.
! This example uses ports Gi0/1 through Gi0/8. Adjust the range as needed.

! Use 'interface range' to configure multiple ports simultaneously.
interface range GigabitEthernet0/1 - 8 ! Assuming these are the ports for your servers/NAS
 ! Add a generic description for these device ports
 description Homelab_Server_Device_Port_VLAN10
 ! Set the ports to access mode, as they will carry traffic for a single VLAN (VLAN 10)
 switchport mode access
 ! Assign these access ports to VLAN 10
 switchport access vlan 10
 ! Enable PortFast: causes Layer 2 access ports to enter the forwarding state immediately.
 ! Use only on ports connected to end devices (like servers/NAS) to avoid STP delays.
 spanning-tree portfast
 ! Ensure the physical ports are administratively up
 no shutdown
exit

! Configure Gi0/10 as an additional port with Vlan 10 access
! Can be used to e.g. connect a laptop to Vlan 10 directly for PXE-boot provisioning
interface GigabitEthernet0/10
  description "Homelab additional device port VLAN10"
  switchport mode access
  switchport access vlan 10
  spanning-tree portfast
  no shutdown
exit

! Exit configuration mode
end

! Save the running configuration to the startup configuration
copy running-config startup-config
! or "write memory"
```

#### (Optional) K8s Nodes & NAS Device Network Configuration

!!! info
    This is an optional step and can usually be skipped.
    However, if you already have your nodes with some pre-installed OS on them, you can use follow the following steps and test the connectivity.
    <br>
    This part is done on the operating system of each server. The method varies by OS (Linux distribution type, etc.).

- **Physical Connection:**

    * Connect each K8s node (Control 1-3, Worker 1-4) to one of the C3560 switchports you just configured (e.g., `Gi0/1` through `Gi0/8`).

- **IP Configuration on Devices:** You have two main options:

    * **Option A: Static IP Configuration (Recommended for Servers/NAS/K8s Nodes):**
        * Manually configure the network interface on each device.
        * **Example for K8s Control 1 (`10.10.10.10`):**
            * IP Address: `10.10.10.10`
            * Subnet Mask: `255.255.255.0` (or `/24`)
            * Gateway: `10.10.10.1` (C1111's SVI for VLAN 10)
            * DNS Server 1: `1.1.1.1` (or your future internal DNS IP)
            * DNS Server 2: `8.8.8.8` (optional)
        * Repeat for all K8s nodes and the NAS, using their designated static IPs (which you excluded from DHCP on the C1111).

    * **Option B: DHCP Client Configuration (Less common for servers, but possible):**
        * Configure the network interface on each device to obtain an IP address automatically via DHCP.
        * If you use this, the device will get an IP from the `HOMELAB_POOL_VLAN10` range _that is not in the excluded list_.
        * For consistent IPs with DHCP, you would typically set up DHCP reservations (MAC address to IP mapping) on the C1111. This is more advanced and can be added later if desired. For now, static configuration on the end devices is simpler if you want specific IPs.

#### Verification Steps

- **On C1111 Router:**
    * If any of your K8s/NAS devices are configured for DHCP (and not in the excluded list), check bindings:
        `show ip dhcp binding` - You should see any devices that successfully got an IP via DHCP from the `HOMELAB_POOL_VLAN10`.
- **On C3560 Switch:**
    * `show mac address-table vlan 10`: You should see the MAC addresses of your connected K8s nodes and NAS learned on their respective switchports (e.g., `Gi0/1`, `Gi0/2`, etc.).
    * `show interfaces status`: Verify that the ports connected to your K8s nodes/NAS are `connected` and in `vlan 10`.
- **On each K8s Node and NAS Device:**
    * **Verify IP Configuration:**
        * Linux: `ip addr show <interface_name>` or `ifconfig <interface_name>`
        * NAS: Check network settings in its web UI.
        * Confirm the IP, subnet mask, gateway, and DNS servers are correctly set (either statically or received via DHCP).
    * **Test Gateway Connectivity:**
        * `ping 10.10.10.1` (Should reply from C1111's Vlan10 SVI).
    * **Test Internet Connectivity:**
        * `ping 1.1.1.1` (or any public IP like `8.8.8.8`).
        * `ping google.com` (Tests both internet and DNS resolution).
    * **Test DNS Resolution (if using public DNS for now):**
        * Linux: `nslookup google.com` or `dig google.com`
        * Confirm it resolves to public IP addresses.
- **From a device on your Home Network (e.g., laptop on `192.168.1.x`):**
    * `ping 10.10.10.10` (Ping K8s Control 1).
    * `ping 10.10.10.20` (Ping K8s Worker 1).
        * These pings should work because the C1111 routes between VLAN 2 and VLAN 10 by default, and no restrictive ACLs are in place yet.
- Connect a PC to the `g0/10` port on the C3560 switch
    * `ifconfig` should show an interface with `10.10.10.x` IP, e.g.
      ```bash
      $ ifconfig
      foobarbaz: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
          inet 10.10.10.71  netmask 255.255.255.0  broadcast 10.10.10.255
      ```

### Troubleshooting

#### SSH error 'no matching key exchange method found'

**Problem:**

After completing stage 2 setup on both C1111 and C3560, the following test was failing from a home network laptop:

```bash
ssh user@10.10.10.2
Unable to negotiate with 10.10.10.2 port 22: no matching key exchange method found. Their offer: diffie-hellman-group-exchange-sha1,diffie-hellman-group14-sha1,diffie-hellman-group1-sha1
```

The following is showed in c3560 console:

```
Jan  2 00:14:02.766: %SSH-3-NO_MATCH: No matching kex algorithm found: client curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp3841...
```

**Explanation:**

This is a classic compatibility issue between modern SSH clients and older network gear like the Cisco Catalyst 3560.

The laptop's SSH client (which is likely using modern, more secure algorithms) is trying to negotiate a Key Exchange (KEX) method with the Cisco 3560. The 3560, running older software, only supports older, less secure KEX methods based on SHA-1 (like `diffie-hellman-group-exchange-sha1`, `diffie-hellman-group14-sha1`, `diffie-hellman-group1-sha1`). Modern SSH clients are configured by default to _reject_ these older, potentially vulnerable methods.
As a result, Neither side can find a mutually agreeable way to establish the secure channel, so the connection fails immediately.

**The Solution:**

The most practical way to fix this is to configure the SSH client on the laptop to temporarily accept one of the older KEX algorithms that the Cisco 3560 _does_ offer.

!!! warning
    Accepting older, SHA-1 based key exchange algorithms is inherently less secure than using modern ones. Use this as a workaround to connect to the device, ideally while planning for a potential IOS upgrade on the 3560 (if available and feasible) or limiting where you use this configuration.

- You can either specify the algorithm on the command line or configure your SSH client file.

    - **Using the Command Line (Temporary for Testing):**
        This is the quickest way to test if this is the issue.
        * Open your terminal or command prompt.
        * Use the `-o KexAlgorithms` option to specify an accepted algorithm. Pick one from the C3560's offer list. `diffie-hellman-group14-sha1` is slightly preferred over `group1-sha1`.
        * Enter the command:
          ```bash
          ssh -o KexAlgorithms=diffie-hellman-group14-sha1 user@10.10.10.2
          ```
        * If this connects, the KEX mismatch was indeed the problem.

    - **Using the SSH Config File (More Permanent):**
        This is better if you need to connect to this device frequently.
        * Open a terminal or command prompt.
        * Navigate to or create the `.ssh` directory in your user's home directory: `cd ~/.ssh` (If it doesn't exist, create it: `mkdir ~/.ssh`).
        * Open the `config` file in a text editor (e.g., `nano ~/.ssh/config` or `notepad ~/.ssh/config` on Windows).
        * Add the following block to the file. Replace `10.10.10.2` if you need to connect using a hostname instead.
          ```
          Host 10.10.10.2
              KexAlgorithms +diffie-hellman-group14-sha1
          ```
          _NB! The `+` sign is important!_ It tells the client to _add_ `diffie-hellman-group14-sha1` to its list of acceptable algorithms, rather than replacing the entire list. This is safer.
        * Save the file.
        * Now, try connecting using your regular command:
          ```bash
          ssh user@10.10.10.2
          ```

    - **On the Cisco 3560 (Verification):**

        You don't usually need to configure the 3560 itself for this specific issue, as the problem is the client _rejecting_ what the server offers. However, you can verify the available algorithms on the switch using:

        ```cisco
        show ip ssh server algorithms
        ```

        This command will list the supported KEX, encryption (cipher), and integrity (MAC) algorithms. Confirm that the list includes the `diffie-hellman-group` options.

#### SSH error 'no matching host key type found'

After fixing the above error, I started getting another one when connecting to the same switch:

```bash
ssh -o KexAlgorithms=diffie-hellman-group14-sha1 user@10.10.10.2
Unable to negotiate with 10.10.10.2 port 22: no matching host key type found. Their offer: ssh-rsa
```

**The Problem:**

After key exchange, the server (the Cisco 3560) presents its **host key** to the client. This host key is used by the client to verify the server's identity (to prevent Man-in-the-Middle attacks). The error message tells you:

- The switch is offering a host key of type `ssh-rsa`.
- Your modern SSH client is _not_ configured by default to accept `ssh-rsa` as a valid host key type.

Why is this happening?

* More recent versions of OpenSSH clients (starting around version 8.2) have started disabling `ssh-rsa` by default when the server uses SHA-1 for signing, because SHA-1 is considered cryptographically weak. Older Cisco IOS versions often rely on SHA-1 for this.
* While the host key itself might be RSA, the _signature algorithm_ used with it might be `rsa-sha2-256` or `rsa-sha2-512` on modern servers. Older servers only support the original `ssh-rsa` signature which implicitly uses SHA-1.

**The Solution:**

Similar to the KEX issue, you need to configure your SSH client to accept `ssh-rsa` as a valid host key type for this specific connection.

!!! warning
    As before, enabling older algorithms carries potential security risks. Only do this when connecting to trusted legacy devices and be aware that you are relying on less robust cryptography for server identity verification.

- **Using the Command Line (Temporary for Testing):**

    Add another `-o` option for `HostKeyAlgorithms`. You can chain multiple `-o` options.

    ```bash
    ssh -o KexAlgorithms=diffie-hellman-group14-sha1 -o HostKeyAlgorithms=ssh-rsa user@10.10.10.2
    ```

    _Note:_ You might need to add the `+` prefix here as well, especially if you have a very recent SSH client, although sometimes `ssh-rsa` alone works for `HostKeyAlgorithms`:

    ```bash
    # If the above fails, try adding '+'
    ssh -o KexAlgorithms=diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa user@10.10.10.2
    ```

- **Using the SSH Config File (More Permanent):**

    Edit your `~/.ssh/config` file again. Add a line for `HostKeyAlgorithms` under the `Host` block for 10.10.10.2. Use the `+` prefix to _add_ `ssh-rsa` without removing other, more secure host key types you might need for other servers.

    ```
    Host 10.10.10.2
        KexAlgorithms +diffie-hellman-group14-sha1
        HostKeyAlgorithms +ssh-rsa  # Add this line
    ```

    Save the file. Now try connecting with the regular command:

    ```bash
    ssh user@10.10.10.2
    ```

