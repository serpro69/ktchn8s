# About

This is my homelab. There are many like it, but this one is mine.

> **What is a homelab?**
>
> Homelab is the name given to a server (or multi-server) setup that resides locally in your home and where you host several applications, virtualized systems, containerized applications and so on, either for testing and developing, or for home and functional usage.
> The hardware you use can be anything from an old laptop, a simple tower or mini-PC, to a RaspberryPi-like device, to a repurposed professional server that you can acquire from companies who discard them due to their age but are still usable, a combination of all of these, or anything in between.
>
> See the [r/homelab introduction](https://www.reddit.com/r/homelab/wiki/introduction) for more information.

## History

One of the biggest drivers behind this project was to get a much deeper familiarity with Kubernetes. I could play around with something like minikube on my laptop all day long, but I wanted something that would require me to treat it as production (or at least production-like) to get more hands on feel, break things, get frustrated (get others frustrated?), then fix them, rinse and repeat. That's pretty much how I like to learn.

I also got my hands on a few old cisco devices and used this opportunity to get more hands-on with networking, which is another area I wanted to improve my skills in. Eventually I want to have a homelab that would be fully-operational and ready for production workloads, so I could use it for my personal projects, as well as for testing and experimenting with new technologies.

I have a lot of experience with Ansible and Terraform, and I spent some time looking into how to provision the nodes. Most solutions were pretty heavy and cumbersome, to say the least. I eventually found [Khue's homelab repo](https://github.com/khuedoan/homelab) which just spins up a container to handle [PXE booting](https://serpro69.github.io/ktchn8s/concepts/pxe_boot/) the machines and then uses ansible for the rest. This immediately drew my attention as it was one of the pain-points I really wanted to automate. I also liked how his code was laid out and how the provisioning flow was structured - you provision baremetal machines, install k3s, and create ArgoCD resources, and then the latter is responsible for deploying everything else - so I used it as a base for my own homelab cluster. I wanted to make my cluster fully-operational first - working in small increments along the way - and modify it heavily afterwards. Forking his repo would require a lot of cleanups and unnecessary work, that's why my repo is technically not a "fork", although a lot of ideas and initial code was borrowed from his repo, for which he gets all the credits.

## Ack

I've used a lot of resources on the internet while researching and learning on how to build my homelab. The following references, among other things, are of particular noteworthiness:

- [Project TinyMiniMicro on servethehome.com](https://www.servethehome.com/introducing-project-tinyminimicro-home-lab-revolution/)
- [Many examples from khuedoan/homelab](https://github.com/khuedoan/homelab?tab=readme-ov-file#acknowledgements)
    - [Ephemeral PXE server inspired by Minimal First Machine in the DC](https://speakerdeck.com/amcguign/minimal-first-machine-in-the-dc)
        - [pdf version](../reference/external/minimal_first_machine_in_the_dc.pdf)
    - [ArgoCD usage and monitoring configuration in locmai/humble](https://github.com/locmai/humble)
    - [README template](https://github.com/othneildrew/Best-README-Template)
    - [Run the same Cloudflare Tunnel across many `cloudflared` processes](https://developers.cloudflare.com/cloudflare-one/tutorials/many-cfd-one-tunnel)
        - [markdown version](../reference/external/many_cfs_one_tunnel.md)
    - [MAC address environment variable in GRUB config](https://askubuntu.com/questions/1272400/how-do-i-automate-network-installation-of-many-ubuntu-18-04-systems-with-efi-and)
    - [Official k3s systemd service file](https://github.com/k3s-io/k3s/blob/master/k3s.service)
    - [Official Cloudflare Tunnel examples](https://github.com/cloudflare/argo-tunnel-examples)
    - [Initialize GitOps repository on Gitea and integrate with Tekton by RedHat](https://github.com/redhat-scholars/tekton-tutorial/tree/master/triggers)
    - [SSO configuration from xUnholy/k8s-gitops](https://github.com/xUnholy/k8s-gitops)
    - [Diátaxis technical documentation framework](https://diataxis.fr)
    - [Official Terratest examples](https://github.com/gruntwork-io/terratest/tree/main/test)
    - [Self-host an automated Jellyfin media streaming stack](https://zerodya.net/self-host-jellyfin-media-streaming-stack)
        - [markdown version](../reference/external/self_host_an_automated_jellyfin_media_streaming_stack.md)
    - [App Template Helm chart by bjw-s-labs](https://bjw-s-labs.github.io/helm-charts/docs/)
- [App configs from onedr0p/home-ops](https://github.com/onedr0p/home-ops)
    - [and the cluster-template](https://github.com/onedr0p/cluster-template)
