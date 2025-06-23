---
icon: material/earth
---

# :material-earth: Overview

## Components

Main:

```mermaid
architecture-beta
    group home(si:kubernetes)[Ktchn8s]

    group control(mdi:account-tie-hat) in home
    group worker(mdi:worker) in home
    group storage(mdi:network-attached-storage) in home

    service odin(server)[Odin] in control
    service freyja(server)[Freyja] in control
    service heimdall(server)[Heimdall] in control

    service draupnir(server)[Draupnir] in worker
    service megingjord(server)[Megingjord] in worker

    service yggdrasil(server)[Yggdrasil] in storage
    service disks(disk) in storage

    yggdrasil:B -- T:disks

    odin{group}:R <--> L:draupnir{group}
    odin{group}:B <--> T:yggdrasil{group}
    megingjord{group}:L <--> R:yggdrasil{group}

    %% External Services

    group external(mdi:cloud)[External]

    service cloudflare(si:cloudflare)[Cloudflare] in external
    service github(si:github)[Github] in external

    cloudflare{group}:B <--> T:heimdall{group}

    %% service db(database)[Database] in api
    %% service disk1(disk)[Storage] in api
    %% service disk2(disk)[Storage] in api
    %% service server(server)[Server] in api

    %% db:L -- R:server
    %% disk1:T -- B:server
    %% disk2:T -- B:db
```

- ...

Other:

- `./docs`: documentation, written in Markdown and served with [mkdocs](https://www.mkdocs.org/)
