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

    * **If `GigabitEthernet0/0/0` is *not* a dedicated WAN port and is actually part of the switch block (unlikely for `0/0/x` naming but possible on some variants):**
        * You would *not* configure `ip address dhcp` directly. Instead, you'd create a "WAN VLAN" (e.g., VLAN 99), assign this physical port to VLAN 99, create `interface Vlan99`, and put `ip address dhcp` and `ip nat outside` on `interface Vlan99`. 
        * *This is a crucial distinction based on your router's specific hardware port types.*

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
   * ref: https://www.reddit.com/r/eero/comments/uuuvdc/comment/i9hkazz/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button
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
