# ktchn8s

<div markdown="1" style="text-align: center; font-size: 1.2em;">

_...there's no place like_ `~`

<b>🚧 Fork in progress, expect some dust 🚧</b>

[![github-tag](https://img.shields.io/github/v/tag/serpro69/ktchn8s?style=for-the-badge&logo=semver&logoColor=white)](https://github.com/serpro69/ktchn8s/tags)
[![github-license](https://img.shields.io/github/license/serpro69/ktchn8s?style=for-the-badge&logo=unlicense&logoColor=white)](https://opensource.org/license/mit)
[![github-stars](https://img.shields.io/github/stars/serpro69/ktchn8s?logo=github&logoColor=white&color=gold&style=for-the-badge)](https://github.com/serpro69/ktchn8s)
[![website](https://img.shields.io/website?label=docs&logo=gitbook&logoColor=white&style=for-the-badge&url=https%3A%2F%2Fserpro69.github.io/ktchn8s)](https://serpro69.github.io/ktchn8s)

</div>

> `/ˈkɪtʃ.ən.eɪts/` (“Kitch-en-ates”)

A K8s ☸️ homelab cluster 👾
<br>...right in your kitchen 🚀💥

<div markdown="1" style="text-align: center; font-size: 2em;">

**[:material-star-circle-outline: Features](#features) ⟩ [:material-rocket-launch: Getting Started](#getting-started) ⟩ [:material-file-document-multiple: Documentation](https://serpro69.github.io/ktchn8s)**

</div>

---

## About

This project utilizes [Infrastructure as Code](https://en.wikipedia.org/wiki/Infrastructure_as_code) and [GitOps](https://www.weave.works/technologies/gitops) to automate provisioning, operating, and updating self-hosted services in my homelab.
It can also be used as a framework to build your own homelab.

> **What is a homelab?**
>
> Homelab is the name given to a server (or multi-server) setup that resides locally in your home and where you host several applications, virtualized systems, containerized applications and so on, either for testing and developing, or for home and functional usage.
> The hardware you use can be anything from an old laptop, a simple tower or mini-PC, to a RaspberryPi-like device, to a repurposed professional server that you can acquire from companies who discard them due to their age but are still usable, a combination of all of these, or anything in between.
>
> See the [r/homelab introduction](https://www.reddit.com/r/homelab/wiki/introduction) for more information.

If you encounter an issue or want to contribute a fix or an improvement, please create [a bug issue](https://github.com/serpro69/ktchn8s/issues/new?template=bug.md).
<br>If you have a question or want to chat about this project, please create [a new discussion](https://github.com/serpro69/ktchn8s/discussions/new/choose).

## Overview

This project is still in the experimental stage. This means, among other things, that:

- There might be breaking changes that may require a complete redeployment.
- A proper upgrade path is planned for the stable release.

More information can be found in the [roadmap](https://serpro69.github.io/ktchn8s/reference/roadmap/).

### Hardware

![PXL_20250627_134343069_21](https://github.com/user-attachments/assets/7a5c9ce3-c1de-4d23-a5a6-796e0e08a2ec)

- Network:
    - Cisco C1111-8P Router
    - Cisco C3560-GS-8P Switch
    - Eero 6 Router (used as access-point for WiFi at home)
- Servers:
    - 3 × Lenovo Tiny M70q Gen.3
        - CPU: `Intel Core i5-12400T`
        - RAM: `16GB DDR4`
        - SSD: `256GB`
    - 2 × Lenovo Tiny M70q Gen.2
        - CPU: `Intel Core i5-11400T`
        - RAM: `16GB DDR4`
        - SSD: `256GB`
    - 7 × Lenovo Tiny M720q
        - CPU: `Intel Core i5-8100T`
        - RAM: `16GB`
        - SSD: `512GB`

## Getting Started

[Deploy on real hardware](https://serpro69.github.io/ktchn8s/installation/production) for production workload.

## Roadmap

See [roadmap](https://serpro69.github.io/ktchn8s/reference/roadmap/) and [open issues](https://github.com/serpro69/ktchn8s/issues) for a list of proposed features and known issues.

## Contributing

Any contributions you make are greatly appreciated.

Please see [contributing guide](https://serpro69.github.io/ktchn8s/reference/contributing/) for more information.

## License

Copyright &copy; 2025 - present, [serpro69](https://github.com/serpro69)

Distributed under the MIT License.
See [license page](https://serpro69.github.io/ktchn8s/reference/license) or [`LICENSE.md`](https://github.com/serpro69/ktchn8s/blob/master/LICENSE.md) file for more information.

## Ack

I've used the following references, among other things, while building my homelab:

- [Project TinyMiniMicro on servethehome.com](https://www.servethehome.com/introducing-project-tinyminimicro-home-lab-revolution/)
- [Many examples from khuedoan/homelab](https://github.com/khuedoan/homelab?tab=readme-ov-file#acknowledgements)
    - [Ephemeral PXE server inspired by Minimal First Machine in the DC](https://speakerdeck.com/amcguign/minimal-first-machine-in-the-dc)
        - [pdf version](./reference/external/minimal_first_machine_in_the_dc.pdf)
    - [ArgoCD usage and monitoring configuration in locmai/humble](https://github.com/locmai/humble)
    - [README template](https://github.com/othneildrew/Best-README-Template)
    - [Run the same Cloudflare Tunnel across many `cloudflared` processes](https://developers.cloudflare.com/cloudflare-one/tutorials/many-cfd-one-tunnel)
        - [markdown version](./reference/external/many_cfs_one_tunnel.md)
    - [MAC address environment variable in GRUB config](https://askubuntu.com/questions/1272400/how-do-i-automate-network-installation-of-many-ubuntu-18-04-systems-with-efi-and)
    - [Official k3s systemd service file](https://github.com/k3s-io/k3s/blob/master/k3s.service)
    - [Official Cloudflare Tunnel examples](https://github.com/cloudflare/argo-tunnel-examples)
    - [Initialize GitOps repository on Gitea and integrate with Tekton by RedHat](https://github.com/redhat-scholars/tekton-tutorial/tree/master/triggers)
    - [SSO configuration from xUnholy/k8s-gitops](https://github.com/xUnholy/k8s-gitops)
    - [Diátaxis technical documentation framework](https://diataxis.fr)
    - [Official Terratest examples](https://github.com/gruntwork-io/terratest/tree/main/test)
    - [Self-host an automated Jellyfin media streaming stack](https://zerodya.net/self-host-jellyfin-media-streaming-stack)
        - [markdown version](./reference/external/self_host_an_automated_jellyfin_media_streaming_stack.md)
    - [App Template Helm chart by bjw-s-labs](https://bjw-s-labs.github.io/helm-charts/docs/)
- [App configs from onedr0p/home-ops](https://github.com/onedr0p/home-ops)
    - [and the cluster-template](https://github.com/onedr0p/cluster-template)
