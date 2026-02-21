---
icon: material/crosshairs-question
title: Add DHCP Reservations
---

# :material-crosshairs-question: HowTo add DHCP reservations

Sometimes you'll want to reserve IP addresses for certain clients. For example, let's say you want to permit ssh access from your workstation on your home network (VLAN2) to your servers network (VLAN10), but don't want to allow all devices in your home vlan. You could easily do this via firewall settings on the servers, but if you want to limit to a specific device - those devices would need to have static IP addresses. To ensure that only your workstation gets assigned the "permitted" IP address - you can configure DHCP reservations.

On a cisco router, you'd do this as follows.

Check your client's currently assigned IP and mac address on a given interface, for example:

```bash
ifconfig wlp0s20f3 | grep ether
ether ab:cd:ef:00:11:42 txqueuelen 1000 (Ethernet)

ifconfig wlp0s20f3 | grep inet | grep -v grep inet6
inet 192.168.1.23  netmask 255.255.255.0  broadcast 192.168.1.255
```

Then, on the cisco router, look up current dhcp bindings:

```cisco
muspell#sh ip dhcp binding assigned

Bindings from all pools not associated with VRF:
IP address      Client-ID/              Lease expiration        Type       State      Interface
                Hardware address/
                User name
...
192.168.1.23    01ab.cdef.0011.42       Feb 22 2026 04:13 PM    Automatic  Active     Vlan2
```

Before we can assign the reservation to the given client-id, we need to clear the current binding:

```cisco
clear ip dhcp binding 192.168.1.23
```

Next, add a reserved address (let's say, we want to reserve `192.168.1.100`) to the VLAN2 pool:

```cisco
muspell#conf t
Enter configuration commands, one per line.  End with CNTL/Z.
muspell(config)#ip dhcp pool HOME_POOL_VLAN2
muspell(dhcp-config)#address 192.168.1.100 client-id 01ab.cdef.0011.42
muspell(dhcp-config)#exit
muspell(config)#exit
```

Check the assigned bindings:

```cisco
muspell#sh ip dhcp binding assigned
Bindings from all pools not associated with VRF:
IP address      Client-ID/              Lease expiration        Type       State      Interface
                Hardware address/
                User name
192.168.1.100   01ab.cdef.0011.42       Infinite                Manual     Selecting  Unknown
```

On the client side we need to renew the IP address on the selected interface:

```bash
➜ nmcli connection show
NAME                 UUID                                  TYPE      DEVICE
Silence of the LANs  6f11bd9b-7d7e-4272-b8df-c3770d3f0348  wifi      wlp0s20f3

nmcli connection down Silence\ of\ the\ LANs

nmcli connection up Silence\ of\ the\ LANs
```

Now check the newly assigned IP address:

```bash
ifconfig wlp0s20f3 | grep inet | grep -v inet6
inet 192.168.1.100 netmask 255.255.255.0 broadcast 192.168.1.255
```

In cisco cli we should now see the assigned binding as "Active":

```cisco
muspell#sh ip dhcp binding assigned
Bindings from all pools not associated with VRF:
IP address      Client-ID/              Lease expiration        Type       State      Interface
                Hardware address/
                User name
192.168.1.100   01ab.cdef.0011.42       Infinite                Manual     Active     Unknown
```

We can also see currently reserved addresses in the pool:

```cisco
muspell#sh ip dhcp pool HOME_POOL_VLAN2

Pool HOME_POOL_VLAN2 :
 Utilization mark (high/low)    : 100 / 0
 Subnet size (first/next)       : 0 / 0
 Total addresses                : 254
 Leased addresses               : 10
 Excluded addresses             : 10
 Pending event                  : none
 1 subnet is currently in the pool :
 Current index        IP address range                    Leased/Excluded/Total
 192.168.1.31         192.168.1.1      - 192.168.1.254     10    / 10    / 254
 1 reserved address is currently in the pool :
 Address          Client
 192.168.1.100    01ab.cdef.0011.42
```

!!! note
    DHCP clients require client identifiers. You can specify the unique identifier for the client in either of the following ways:

    - A 7-byte dotted hexadecimal notation. For example, 0100.04f3.0158.b3, where **01** at the start represents the Ethernet media type and the remaining bytes represent the MAC address of the DHCP client.
    - 27-byte dotted hexadecimal notation. For example, 7665.6e64.6f72.2d30.3032.342e.3937.6230.2e33.3734.312d.4661.302f.31. The equivalent ASCII string for this hexadecimal value is vendor-0024.97b0.3741, where vendor represents the vendor, 0024.97b0.3741 represents the MAC address of the source interface.

!!! important
    If you put the address in the excluded addresses and in a manual binding scope your system won't get ip address.

