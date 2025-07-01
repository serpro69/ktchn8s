---
icon: fontawesome/brands/cloudflare
title: External Resources
---

# :fontawesome-brands-cloudflare: External Resources/Dependencies

!!! info
    These resources are optional, the homelab still works without them but will lack some features like trusted certificates and offsite backup

We try to keep the amount of external dependencies to an absolute minimum, but there's still need for a few of them.
Below is a list of external resources and why we need them (also see some [alternatives](#alternatives) below).

| Provider        | Resource  | Purpose                                                                                                     |
| --------        | --------  | -------                                                                                                     |
| Cloudflare      | DNS       | DNS and [DNS-01 challenge](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge) for certificates |
| Cloudflare      | Tunnel    | Public services to the internet without port forwarding                                                     |
| ntfy            | Topic     | External notification service to receive alerts                                                             |

## Create credentials

You'll be asked to provide these credentials on first build.

### Cloudflare

- Buy a domain 
    - You may also wish to [transfer domain to Cloudflare](https://developers.cloudflare.com/registrar/get-started/transfer-domain-to-cloudflare) entirely, it's up to you.
- Get Cloudflare email and account ID
- Get Cloudflare **Global API key**: <https://dash.cloudflare.com/profile/api-tokens>

### ntfy

- Choose a random topic name like <https://ntfy.sh/random_topic_name_here_a8sd7fkjxlkcjasdw33813> (treat it like your password)

## Alternatives

To avoid vendor lock-in, each external provider must have an equivalent alternative that is easy to replace:

- Cloudflare DNS:
    - Update cert-manager and external-dns to use a different provider
    - [Alternate DNS setup](../../guides/how_to_alternate_dns_setup.md)
- Cloudflare Tunnel:
    - Use port forwarding if it's available
    - Create a small VPS in the cloud and utilize Wireguard to route traffic via it
    - Access everything via VPN
    - See also [awesome tunneling](https://github.com/anderspitman/awesome-tunneling)
- ntfy:
    - [Self-host your own ntfy server](https://docs.ntfy.sh/install)
    - Any other [integration supported by Grafana Alerting](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/manage-contact-points/integrations/#list-of-supported-integrations)
