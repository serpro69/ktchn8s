---
icon: material/map-check-outline
title: Roadmap
---

## :material-map-check-outline: Roadmap

<div class="banner-image-wrapper">
  <img class="banner-image" src="https://plus.unsplash.com/premium_photo-1661311950994-d263ea9681a1?q=80&w=1974&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" style="object-position: 50% 70%;">
</div>

!!! info
    Current status: **ALPHA**

## Alpha requirements

Anything that works (...or doesn't 🤷).

## Beta requirements

Good enough for tinkering and personal usage, and reasonably secure.

- [ ] Automated bare metal provisioning
    - [ ] Controller set up (Docker)
    - [ ] OS installation (PXE boot)
- [ ] Automated cluster creation (k3s)
- [ ] Automated application deployment (ArgoCD)
- [ ] Automated DNS management
- [ ] Initialize GitOps repository on Gitea automatically
- [ ] Observability
    - [ ] Monitoring
    - [ ] Logging
    - [ ] Alerting
- [ ] SSO
- [ ] Reasonably secure
    - [ ] Automated certificate management
    - [ ] Declarative secret management
    - [ ] Replace all default passwords with randomly generated ones
    - [ ] Expose services to the internet securely with Cloudflare Tunnel
- [ ] Only use open-source technologies (except external managed services in `./external`)
- [ ] Everything is defined as code
- [ ] Backup solution (3 copies, 2 seperate devices, 1 offsite)
- [ ] Define [SLOs](https://en.wikipedia.org/wiki/Service-level_objective):
    - [ ] 70% availability (might break in the weekend due to new experimentation)
- [ ] Core applications
    - [ ] Gitea
    - [ ] Woodpecker
    - [ ] Private container registry
    - [ ] Homepage

## Stable requirements

Can be used in "production" (for family or even small scale businesses).

- [ ] A single command to deploy everything
- [ ] Fast deployment time (from empty hard drive to running services in under 1 hour)
- [ ] Fully _automatic_, not just _automated_
    - [ ] Bare-metal OS rolling upgrade
    - [ ] Kubernetes version rolling upgrade
    - [ ] Application version upgrade
    - [ ] Encrypted backups
    - [ ] Secrets rotation
    - [ ] Self healing
- [ ] Secure by default
    - [ ] SELinux
    - [ ] Network policies
- [ ] Static code analysis
- [ ] Chaos testing
- [ ] Minimal dependency on external services
- [ ] Complete documentation
    - [ ] Diagram as code
    - [ ] Book (this book)
    - [ ] Walkthrough tutorial and feature demo (video)
- [ ] Configuration script for new users
- [ ] More dashboards and alert rules
- [ ] SLOs:
    - [ ] 99,9% availability (less than 9 hours of downtime per year)
    - [ ] 99,99% data durability
- [ ] Clear upgrade path
- [ ] Additional applications
    - [ ] Matrix with bridges
    - [ ] VPN server
    - [ ] PeerTube
    - [ ] Blog
    - [ ] [Development Dashboard](https://github.com/backstage/backstage)
