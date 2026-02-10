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
  metal:
       children:
           nas: null
           k3s: null
  +nas:
  +    hosts:
  +        yggdrasil:
  +            interface:
  +                host: bifrost
  +                interface: Gi0/4
  +            ansible_host: 10.10.10.30
  +            mac: aa:bb:cc:dd:ee:ff
  +            data_drives: # NB! pre-partitioned
  +                - id: ata-ST18000NM000J-FOOBAR_ABCDEF-part1
  +                  brand: seagate
  +            parity_drives: [] # NB! pre-partitioned
  +                - id: ata-ST18000NM000J-FOOBAR_0123456-part1
  +                  brand: seagate
  +            network_interface: eno1
   k3s:
      children:
          control_plane:
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
    Don't forget to create a Deployment as well, unless your template handles that automatically\_

- Use the PVC in your application, for example, Jellyfin:

```yaml title="./apps/jellyfin/values.yaml"
--8<--
./apps/jellyfin/values.yaml:113:113,160:168
--8<--
```

## NFS Permissions and `root_squash`

The NFS server is configured with `root_squash` (the NFS default). This means any process connecting as root (uid 0) from a K8s node is mapped to the anonymous user on the NFS server. Non-root users pass through unchanged.

The anonymous uid/gid is configured via `nfs_anon_uid`/`nfs_anon_gid` (default `1000`) and should match the `fsGroup` used by your application pods. This ensures that:

- **kubelet `fsGroup` chown** works correctly — the kubelet runs as root, so its chown calls are squashed to uid 1000, which matches the target group
- **Root-running containers** (e.g., linuxserver.io images that start as root before dropping to `PUID`/`PGID`) create files owned by uid 1000 on the NFS server
- **Non-root containers** running as uid 1000 can read/write files created by either path above

Your pod spec should set `fsGroup` to match:

```yaml
spec:
  securityContext:
    fsGroup: 1000
```

!!! tip
    If your applications use a different uid (e.g., 568 for some Helm charts), override `nfs_anon_uid` and `nfs_anon_gid` in your inventory to match.

## Reference

- [csi-driver-nfs/charts/README.md@v4.13.0 · kubernetes-csi/csi-driver-nfs](https://github.com/kubernetes-csi/csi-driver-nfs/blob/v4.13.0/charts/README.md)
- [csi-driver-nfs/charts/v4.13.0/csi-driver-nfs/values.yaml@master · kubernetes-csi/csi-driver-nfs](https://github.com/kubernetes-csi/csi-driver-nfs/blob/master/charts/v4.13.0/csi-driver-nfs/values.yaml)
- [csi-driver-nfs/deploy/example/README.md@v4.13.0 · kubernetes-csi/csi-driver-nfs](https://github.com/kubernetes-csi/csi-driver-nfs/blob/v4.13.0/deploy/example/README.md)
