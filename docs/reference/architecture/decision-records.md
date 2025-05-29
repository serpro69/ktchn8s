---
icon: material/file-document-multiple
---

# :material-file-document-multiple: Decision Records

Architecture decisions play a crucial role in driving the design and development of a software project. They guide the selection of technologies, the design of software components, and the organization of the codebase. However, these decisions are often made in isolation and without proper documentation. This can lead to confusion, inconsistencies, and suboptimal solutions. Moreover, it makes it nearly impossible to answer questions like "why did we decide to do this? 🤔" as the time goes on.

Therefore, it is important to keep a record of architecture decisions, including the context, the decision itself, and the consequences. This practice, known as Architecture Decision Records (ADRs), fosters transparency, improves communication, and provides a historical context to help future decision-making.

This page contains a list of ADRs, both overarching (with cross-cutting concerns across the entirety of Ktchn8s), as well as those specific to a given component.

We follow a simple template for documenting architecture decisions, which is inspired by this Michael Nygard's [post](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions)

??? Template

    ## Title

    > These documents have names that are short noun phrases. For example, "ADR 1: Deployment on Ruby on Rails 3.0.10" or "ADR 9: LDAP for Multitenant Integration"

    **Context**

    > This section describes the forces at play, including technological, political, social, and project local. These forces are probably in tension, and should be called out as such. The language in this section is value-neutral. It is simply describing facts.

    **Decision**

    > This section describes our response to these forces. It is stated in full sentences, with active voice. "We will …"

    **Status**

    > A decision may be "proposed" if the project stakeholders haven't agreed with it yet, or "accepted" once it is agreed. If a later ADR changes or reverses a decision, it may be marked as "deprecated" or "superseded" with a reference to its replacement.
    > While it may not seem necessary to have 'status' section for a project with a single maintainer, decisions may also come from external parties, for example from discussions in pull-requests, so it is still useful to have this section and document these decisions, as well as reasoning behind i.e. rejecting a proposed change.

    **Consequences**

    > This section describes the resulting context, after applying the decision. All consequences should be listed here, not just the "positive" ones. A particular decision may have positive, negative, and neutral consequences, but all of them affect the team and project in the future.

