---
icon: material/file-document-multiple
---

# :material-file-document-multiple: Decision Records

Architecture decisions play a crucial role in driving the design and development of a software project. They guide the selection of technologies, the design of software components, and the organization of the codebase. However, these decisions are often made in isolation and without proper documentation. This can lead to confusion, inconsistencies, and suboptimal solutions. Moreover, it makes it nearly impossible to answer questions like "why did we decide to do this? 🤔" as the time goes on.

Therefore, it is important to keep a record of architecture decisions, including the context, the decision itself, and the consequences. This practice, known as Architecture Decision Records (ADRs), fosters transparency, improves communication, and provides a historical context to help future decision-making.

This page contains a list of ADRs, both overarching (with cross-cutting concerns across the entirety of ktchn8s), as well as those specific to a given component.

We follow a simple template for documenting architecture decisions, which is inspired by this Michael Nygard's [post](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions)

<!-- markdownlint-disable MD046 -->
??? Template

    \## AD-000X - Title

    > These documents have names that are short noun phrases. For example, "ADR 1: Deployment on Ruby on Rails 3.0.10" or "ADR 9: LDAP for Multitenant Integration"
    > We prefix the title with the ADR number for easier reference.

    **Context**

    > This section describes the forces at play, including technological, political, social, and project local. These forces are probably in tension, and should be called out as such. The language in this section is value-neutral. It is simply describing facts.

    **Decision**

    > This section describes our response to these forces. It is stated in full sentences, with active voice. "We will …"

    **Status**

    > A decision may be "proposed" if the project stakeholders haven't agreed with it yet, or "accepted" once it is agreed. If a later ADR changes or reverses a decision, it may be marked as "deprecated" or "superseded" with a reference to its replacement.
    > While it may not seem necessary to have 'status' section for a project with a single maintainer, decisions may also come from external parties, for example from discussions in pull-requests, so it is still useful to have this section and document these decisions, as well as reasoning behind i.e. rejecting a proposed change.

    **Consequences**

    > This section describes the resulting context, after applying the decision. All consequences should be listed here, not just the "positive" ones. A particular decision may have positive, negative, and neutral consequences, but all of them affect the team and project in the future.
<!-- markdownlint-enable MD046 -->


## AD-0001 - Plugging C1111 router directly into ISP modem

**Context**

Before I started home-labbing, our home network was managed via an Eero 6 router connected to the ISP modem.

I initially thought to connect the C1111 router to the Eero:

```mermaid
flowchart LR
    I[Internet] -.- M[ISP Modem] o--o E[Eero 6 Router] o--o C[C1111 Router]
    E -.- |wlan| D[Home Devices]
    C o--o H[Homelab Servers]
```

This would, however, result in Double-NAT, which is usually not recommended.

I found out that Eero can be used as an Access Point in this [post](https://www.reddit.com/r/eero/comments/uuuvdc/comment/i9hkazz/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button) by first wiring one eero to your existing router and setting it up in Double NAT. Once the setup is complete, you can go to the Settings --> Network Settings --> DHCP & NAT and select Bridge. Eero will restart and then work as an Access Point.

Therefore, I can use C1111 as the main (and only) router, and use the existing Eero 6 router as an AP.

**Decision**

- We will connect the C1111 router directly to the ISP modem, and connect Eero 6 to C1111, using Eero router as an AP.

```mermaid
flowchart LR
    I[Internet] -.- M[ISP Modem] o--o C[C1111 Router] o--o E[Eero 6 WiFi AP]
    E -.- |wlan| D[Home Devices]
    C o--o H[Homelab Servers]
```

**Status**

- Accepted

**Consequences**

- No Double-NAT
- Eero 6 will be used as an Access Point, which will allow us to use it for WiFi connectivity.
- Eero 6 in bridge mode has limited functionality (e.g. you won't be able to enable built-in security settings anymore)
    - This is not a big problem because we can ensure security via router or pfsense or something similar.
