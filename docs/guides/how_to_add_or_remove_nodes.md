---
icon: material/crosshairs-question
title: Add, Move/Rename, Remove Nodes
---

# :material-crosshairs-question: HowTo add, move (rename), or remove nodes

...or how to scale vertically. To replace the same node with a clean OS, remove it and add it again.

## Add new nodes

!!! tip
    You can add multiple nodes at the same time

Add its details to the inventory **at the end of the group** (masters or workers):

```diff title="metal/inventories/prod.yml"
diff --git a/metal/inventory/metal.yml b/metal/inventory/metal.yml
index aaaaaaa..bbbbbbb 100644
--- a/metal/inventory/metal.yml
+++ b/metal/inventory/metal.yml
@@ -75,14 +77,14 @@ metal:
     nodes:
       hosts:
+        bar:
+          interface:
+            host: bifrost
+            interface: Gi0/6
+          ansible_host: 10.10.10.21
+          mac: aa:bb:cc:dd:ee:ff
+          disk: sda
+          network_interface: eno1
         baz:
             interface:
                 host: bifrost
```

Install the OS and join the cluster:

```
make metal
```

That's it!

## Remove a node

!!! danger
    It is highly recommended to remove nodes one at a time.

Remove it from the inventory:

```diff title="metal/inventories/prod.yml"
diff --git a/metal/inventories/prod.yml b/metal/inventories/prod.yml
index 123456..abcdef 100644
--- a/metal/inventories/prod.yml
+++ b/metal/inventories/prod.yml
@@ -8,3 +8,4 @@ metal:
     nodes:
       hosts:
         foo: {ansible_host: 10.10.10.23, mac: '...', disk: nvme0n1, network_interface: eno1}
-        bar: {ansible_host: 10.10.10.24, mac: '...', disk: nvme0n1, network_interface: eno1}
```

Drain the node:

```sh
kubectl drain ${NODE_NAME} --delete-emptydir-data --ignore-daemonsets --force
```

Remove the node from the cluster

```sh
kubectl delete node ${NODE_NAME}
```

Shutdown the node:

```
ssh root@${NODE_IP} poweroff
```

!!! tip
    You can run `make remove NODE_NAME=bar` to achieve the above steps.
    <br>
    _**NB! this will also wipe the disk on the node!**_

## Rename a node

!!! warning
    Make sure to stop and remove ephemeral pxe docker containers before you re-run `bootstrap`:
    `docker stop files-http-1 files-dnsmasq-1 && docker rm files-http-1 files-dnsmasq-1`

First [remove the node](#remove-a-node), then update the inventory file:

```diff title="metal/inventories/prod.yml"
diff --git a/metal/inventories/prod.yml b/metal/inventories/prod.yml
index 123456..abcdef 100644
--- a/metal/inventories/prod.yml
+++ b/metal/inventories/prod.yml
@@ -8,3 +8,4 @@ metal:
     nodes:
       hosts:
         foo: {ansible_host: 10.10.10.23, mac: '...', disk: nvme0n1, network_interface: eno1}
-        bar: {ansible_host: 10.10.10.24, mac: '...', disk: nvme0n1, network_interface: eno1}
+        baz: {ansible_host: 10.10.10.24, mac: '...', disk: nvme0n1, network_interface: eno1}
```

After that, install the OS and join the cluster:

```
make metal
```
