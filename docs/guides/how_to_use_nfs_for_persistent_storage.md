---
icon: material/crosshairs-question
title: Use NFS for Persistent Storage
---

# :material-crosshairs-question: HowTo use NFS for Persistent Storage

You can have some (or all) of your persistent volumes provisioned on your NAS server via NFS using [csi-driver-nfs](https://github.com/kubernetes-csi/csi-driver-nfs).

## Prerequisites

- The [csi-driver-nfs](https://github.com/kubernetes-csi/csi-driver-nfs?tab=readme-ov-file#overview) driver requires existing and already configured NFSv3 or NFSv4 server.

## High-level Setup Overview

- Provision the NFS server by updating the [metal/inventory/metal.yml](https://github.com/serpro69/ktchn8s/blob/master/metal/inventory/metal.yml) hosts to include a new NAS host under `storage` group:

    ```diff
    diff --git a/metal/inventory/metal.yml b/metal/inventory/metal.yml
    index aaaaaaa..bbbbbbb 100644
    --- a/metal/inventory/metal.yml
    +++ b/metal/inventory/metal.yml
    @@ -1,16 +1,20 @@
     metal:
       children:
    +    storage:
    +      vars:
    +        ansible_user: root
    +      hosts:
    +        nas:
    +          interface: Gi0/4
    +          ansible_host: 10.10.10.30
    +          mac: aa:bb:cc:dd:ee:ff
    +          nfs_disks:
    +            - sda1
    +            - sda2
    +            - sda3
    +            - sda4
    +          network_interface: eno1
         control_plane:
           vars:
             ansible_user: root
    ```

    !!! note
        _NB! Unlike k8s nodes, the NAS OS is **not** installed via PXE. It's assumed a base server OS is already installed (both Debian-based and Fedora OSes are supported) on the NAS server._

    - Then run `make metal`

- [Install the driver on a Kubernetes cluster](https://github.com/kubernetes-csi/csi-driver-nfs?tab=readme-ov-file#install-driver-on-a-kubernetes-cluster). See [`system/csi-driver-nfs`](https://github.com/serpro69/ktchn8s/tree/master/system/csi-driver-nfs) for more details.
    - _I use the static mode based on my own needs._

- Create a static PV:

```yaml title="./apps/jellyfin/templates/pv-videos.yaml"
--8<--
./apps/jellyfin/templates/pv-videos.yaml
--8<--
```

- Create a static PVC:

```yaml title="./apps/jellyfin/templates/pvc-videos.yaml"
--8<--
./apps/jellyfin/templates/pvc-videos.yaml
--8<--
```

!!! note
    Don't forget to create a Deployment as well, unless your template handles that automatically_

- Use the PVC in your application, for example, Jellyfin:

```yaml title="./apps/jellyfin/values.yaml"
--8<--
./apps/jellyfin/values.yaml:113:113,160:168
--8<--
```

## Reference

* [csi-driver-nfs/charts/README.md@v4.11.0 · kubernetes-csi/csi-driver-nfs](https://github.com/kubernetes-csi/csi-driver-nfs/blob/v4.11.0/charts/README.md)
* [csi-driver-nfs/charts/v4.11.0/csi-driver-nfs/values.yaml@master · kubernetes-csi/csi-driver-nfs](https://github.com/kubernetes-csi/csi-driver-nfs/blob/master/charts/v4.11.0/csi-driver-nfs/values.yaml)
* [csi-driver-nfs/deploy/example/README.md@v4.11.0 · kubernetes-csi/csi-driver-nfs](https://github.com/kubernetes-csi/csi-driver-nfs/blob/v4.11.0/deploy/example/README.md)
