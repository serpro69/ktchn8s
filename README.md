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

A homelab ☸️ kubernetes cluster 👾
<br>...right in your kitchen 🚀💥

<div markdown="1" style="text-align: center; font-size: 2em;">

**[:material-star-circle-outline: Features](#features) ⟩ [:material-rocket-launch: Getting Started](#getting-started) ⟩ [:material-file-document-multiple: Documentation](https://serpro69.github.io/ktchn8s)**

</div>

---

## About

This project utilizes [Infrastructure as Code](https://en.wikipedia.org/wiki/Infrastructure_as_code) and [GitOps](https://www.weave.works/technologies/gitops) to automate provisioning, operating, and updating self-hosted services in my homelab.
It can also be used as a framework to build your own homelab.

If you encounter an issue or want to contribute a fix or an improvement, please create [a bug issue](https://github.com/serpro69/ktchn8s/issues/new?template=bug.md).
<br>If you have a question or want to chat about this project, please create [a new discussion](https://github.com/serpro69/ktchn8s/discussions/new/choose).

## Overview

This project is still in the experimental stage. This means, among other things, that:

- There might be breaking changes that may require a complete redeployment.
- A proper upgrade path is planned for the stable release.

More information can be found in the [roadmap](https://serpro69.github.io/ktchn8s/info/roadmap/).

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

| Demo Showcase                                                                                                   |
| :--:                                                                                                            |
| Homepage powered by... [Homepage](https://gethomepage.dev)                                                      |
| [![][homepage-demo]][homepage-demo]                                                                             |
| Git server powered by [Gitea](https://gitea.io/en-us)                                                           |
| [![][gitea-demo]][gitea-demo]                                                                                   |
| Continuous Integration with [Woodpecker CI](https://woodpecker-ci.org/)                                         |
| [![][woodpecker-demo]][woodpecker-demo]                                                                         |
| Continuous Deployment with [ArgoCD](https://argoproj.github.io/cd)                                              |
| [![][argocd-demo]][argocd-demo]                                                                                 |

[homepage-demo]: https://github.com/user-attachments/assets/8b2680c1-53e1-47c5-818d-08d3502f144b
[gitea-demo]: https://github.com/user-attachments/assets/f3775815-6c55-4086-b15a-8e0562e5d6a6
[woodpecker-demo]: https://github.com/user-attachments/assets/70b7e19f-22a3-4d95-aad1-da389d90c53e
[argocd-demo]: https://github.com/user-attachments/assets/bdd91804-2e10-4910-8cf6-afa15e433178

## Getting Started

[Deploy on real hardware](https://serpro69.github.io/ktchn8s/installation/production) for production workload.

...or simply:

<pre style="margin-left: 25%; margin-right: auto;">
<style>
.md-clipboard.md-icon {
  display: none;
}
</style>
<code style="background-color: #070707;">
           ╭──────────────────────────────────────────────────╮
           │                        🐧                        │
           │    ╭────────────────────────────────────────╮    │
           │    │$ nix develop                           │    │
           │    │$ make ktchn8s                          │    │
           │    │...                                     │    │
           │    │                                        │    │
           │    │                                        │    │
           │    │                                        │    │
           │    │                                        │    │
           │    │ 🚀                                     │    │
           │    │                                        │    │
           │    │                                        │    │
           │    ╰────────────────────────────────────────╯    │
           │                                                  │
           ╰──────────────────────────────────────────────────╯
                   ╰──────────────────────────────────╯
               ╭───|──────────────────────────────────|───╮
             _-'    .-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.  --- `-_
          _-'.-.-. .---.-.-.-.-.-.-.-.-.-.-.-.-.-.-.--.  .-.-.`-_
       _-'.-.-.-. .---.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-`__`. .-.-.-.`-_
    _-'.-.-.-.-. .-----.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-----. .-.-.-.-.`-_
 _-'.-.-.-.-.-. .---.-. .-------------------------. .-.---. .---.-.-.-.`-_
╭─────────────────────────────────────────────────────────────────────────╮
╰───._.─────────────────────────────────────────────────────────────._.───╯
</code></pre>

## Roadmap

See [roadmap](https://serpro69.github.io/ktchn8s/info/roadmap/) and [open issues](https://github.com/serpro69/ktchn8s/issues) for a list of proposed features and known issues.

## Contributing

Any contributions you make are greatly appreciated.

Please see [contributing guide](https://serpro69.github.io/ktchn8s/info/contributing/) for more information.

## License

Copyright &copy; 2025 - present, [serpro69](https://github.com/serpro69)

Distributed under the MIT License.
See [license page](https://serpro69.github.io/ktchn8s/info/license) or [`LICENSE.md`](https://github.com/serpro69/ktchn8s/blob/master/LICENSE.md) file for more information.
