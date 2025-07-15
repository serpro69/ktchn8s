---
icon: material/crosshairs-question
title: Rook-Ceph
---

# :material-crosshairs-question: Troubleshooting Rook-Ceph

## OSD pods are not created after zapping devices {#osd-zapping}

!!! warning
    You may sometimes encounter issues with OSD nodes missing when you re-provision an existing node because zapping didn't fully remove the ceph metadata. My [current cleanup version](https://github.com/serpro69/ktchn8s/blob/c007b829e2a28abcf4ee6e7bc03d5fc9a29d34cb/metal/wipe.yml) seems to do the trick most of the times, but sometimes I still see issues with `rook-ceph-osd-prepare` reporting that no partitions were found and that the older partition (i.e. `/dev/nvme0n1p3`) belongs to another cluster. This seems to happen even more often when I try to re-create the entire cluster from scratch.
    <br>
    In such cases, I boot the machine from an Ubuntu live-USB, and wipe->create->wipe the partitions on the disk manually several times via gparted.
    <br>
    _Any PRs to make zapping existing partitions more robust are very much welcome!_

I had to do some manual steps to create OSD on the new node after zapping the disk and once the node was re-provisioned and joined the cluster again. Particularly, I had to restart the `rook-ceph-operator`.

Looking at the OSD pods with:

```bash
kubectl -n rook-ceph get pod -l app=rook-ceph-osd
```

showed only 4 nodes, even after a few hours of re-provisioning the node

```
NAME                               READY   STATUS    RESTARTS   AGE
rook-ceph-osd-0-5554f4f4bc-rrpj6   1/1     Running   0          3h25m
rook-ceph-osd-1-5bdcf57db5-ccwnf   1/1     Running   0          3h25m
rook-ceph-osd-3-7d9f568c86-hjj5m   1/1     Running   0          3h18m
rook-ceph-osd-4-5994f5bf78-kvvlh   1/1     Running   0          3h24m
```

And prepare pod for `draupnir` didn't start on its own after re-provisioning the node:

```bash
kubectl -n rook-ceph get pod -l app=rook-ceph-osd-prepare
```

```
NAME                                     READY   STATUS      RESTARTS   AGE
rook-ceph-osd-prepare-freyja-5x2jp       0/1     Completed   0          3h25m
rook-ceph-osd-prepare-heimdall-qt596     0/1     Completed   0          3h25m
rook-ceph-osd-prepare-megingjord-24cm7   0/1     Completed   0          3h18m
rook-ceph-osd-prepare-odin-v5kwm         0/1     Completed   0          3h24m
```

So I had to dig into troubleshooting guides and eventually found something that seemed to work based on this [solution](https://rook.io/docs/rook/latest-release/Troubleshooting/ceph-common-issues/#solution_5):

> After the settings are updated or the devices are cleaned, trigger the operator to analyze the devices again by restarting the operator. Each time the operator starts, it will ensure all the desired devices are configured. The operator does automatically deploy OSDs in most scenarios, but an operator restart will cover any scenarios that the operator doesn't detect automatically.

```bash
# Delete the operator to ensure devices are configured. 
# A new pod will automatically be started when the current operator pod is deleted.
$ kubectl -n rook-ceph delete pod -l app=rook-ceph-operator
```

Then checking the pods after the operator restarted:

```bash
kubectl -n rook-ceph get pod -l app=rook-ceph-osd

#NAME                               READY   STATUS    RESTARTS   AGE
#rook-ceph-osd-0-5554f4f4bc-rrpj6   1/1     Running   0          3h25m
#rook-ceph-osd-1-5bdcf57db5-ccwnf   1/1     Running   0          3h25m
#rook-ceph-osd-3-7d9f568c86-hjj5m   1/1     Running   0          3h18m
#rook-ceph-osd-4-5994f5bf78-kvvlh   1/1     Running   0          3h24m
#rook-ceph-osd-5-798fd5f45c-xjzz2   1/1     Running   0          6m18s

kubectl -n rook-ceph get pod -l app=rook-ceph-osd-prepare

#NAME                                     READY   STATUS      RESTARTS   AGE
#rook-ceph-osd-prepare-draupnir-gqz9p     0/1     Completed   0          9m25s
#rook-ceph-osd-prepare-freyja-5x2jp       0/1     Completed   0          9m21s
#rook-ceph-osd-prepare-heimdall-qt596     0/1     Completed   0          9m18s
#rook-ceph-osd-prepare-megingjord-24cm7   0/1     Completed   0          9m15s
#rook-ceph-osd-prepare-odin-v5kwm         0/1     Completed   0          9m12s
```

!!! tip
    Useful documentation related to above:
    - [Ceph Teardown - Zapping Devices](https://rook.io/docs/rook/latest-release/Storage-Configuration/ceph-teardown/#zapping-devices)
    - [Ceph Common Issues](https://rook.io/docs/rook/latest-release/Troubleshooting/ceph-common-issues/#osd-pods-are-not-created-on-my-devices)
