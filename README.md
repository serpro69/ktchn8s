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

### History

One of the biggest drivers behind this project was to get a much deeper familiarity with Kubernetes. I could play around with something like minikube on my laptop all day long, but I wanted something that would require me to treat it as production (or at least production-like) to get more hands on feel, break things, get frustrated, then fix them, rinse and repeat. That's pretty much how I like to learn.

I also got my hands on a few old cisco devices and used this opportunity to get more hands-on with networking, which is another area I wanted to improve my skills in. Eventually I want to have a homelab that would be fully-operational and ready for production workloads, so I could use it for my personal projects, as well as for testing and experimenting with new technologies.

I have a lot of experience with Ansible and Terraform, and I spent some time looking into how to provision the nodes. Most solutions were pretty heavy and cumbersome, to say the least. I eventually found [Khue's homelab repo](https://github.com/khuedoan/homelab) which just spins up a container to handle [PXE booting](https://serpro69.github.io/ktchn8s/concepts/pxe_boot/) the machines and then uses ansible for the rest. This immediately drew my attention as it was one of the pain-points I really wanted to automate. I also liked how his code was laid out and how the provisioning flow was structured - you provision baremetal machines, install k3s, and create ArgoCD resources, and then the latter is responsible for deploying everything else - so I used it as a base for my own homelab cluster. I wanted to make my cluster fully-operational first - working in small increments along the way - and modify it heavily afterwards. Forking his repo would require a lot of cleanups and unnecessary work, that's why my repo is technically not a "fork", although a lot of ideas and initial code was borrowed from his repo, for which he gets all the credits.

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

### Features

- [x] Common applications: Gitea, Jellyfin, Paperless...
- [x] Automated bare metal provisioning with PXE boot
- [x] Automated Kubernetes installation and management
- [x] Installing and managing applications using GitOps
- [x] Automatic rolling upgrade for OS and Kubernetes
- [ ] Automatically update apps (with approval)
- [x] Modular architecture, easy to add or remove features/components
- [x] Automated certificate management
- [x] Automatically update DNS records for exposed services
- [ ] VPN (Tailscale or Wireguard)
- [x] Expose services to the internet securely with [Cloudflare Tunnel](https://www.cloudflare.com/products/tunnel/)
- [x] CI/CD platform
- [x] Private container registry
- [ ] Distributed storage
- [ ] Support multiple environments (dev, prod)
- [ ] Monitoring and alerting
- [ ] Automated backup and restore
- [x] Single sign-on
- [x] Infrastructure testing

Some demo videos and screenshots are shown here.
They can't capture all the project's features, but they are sufficient to get a concept of it.

| Demo                                                                                                            |
| :--:                                                                                                            |
| Homepage powered by... [Homepage](https://gethomepage.dev)                                                      |
| [![][homepage-demo]][homepage-demo]                                                                             |
| Git server powered by [Gitea](https://gitea.io/en-us)                                                           |
| [![][gitea-demo]][gitea-demo]                                                                                   |
| Continuous deployment with [ArgoCD](https://argoproj.github.io/cd)                                              |
| [![][argocd-demo]][argocd-demo]                                                                                 |

[homepage-demo]: https://github.com/user-attachments/assets/8b2680c1-53e1-47c5-818d-08d3502f144b
[gitea-demo]: https://github.com/user-attachments/assets/f3775815-6c55-4086-b15a-8e0562e5d6a6
[argocd-demo]: https://github.com/user-attachments/assets/bdd91804-2e10-4910-8cf6-afa15e433178

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
