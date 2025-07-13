# :material-ship-wheel: Production Deployment

<div class="banner-image-wrapper">
  <img class="banner-image" src="https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/51bad5a5-a63e-4bbf-9937-6b5b78416457/db0rp3n-8742c1ce-eaf8-434a-a42b-370d816b6b77.jpg/v1/fill/w_1024,h_512,q_75,strp/viking_raid_by_allrichart_db0rp3n-fullview.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7ImhlaWdodCI6Ijw9NTEyIiwicGF0aCI6IlwvZlwvNTFiYWQ1YTUtYTYzZS00YmJmLTk5MzctNmI1Yjc4NDE2NDU3XC9kYjBycDNuLTg3NDJjMWNlLWVhZjgtNDM0YS1hNDJiLTM3MGQ4MTZiNmI3Ny5qcGciLCJ3aWR0aCI6Ijw9MTAyNCJ9XV0sImF1ZCI6WyJ1cm46c2VydmljZTppbWFnZS5vcGVyYXRpb25zIl19.3bmnWj_dffrhJrNTE8nls1byhTAjoYhAPfJ2nAo12j4" style="object-position: 0% 73%; height: 350px;">
</div>

This [homelab](https://github.com/serpro69/ktchn8s) is designed to be created from scratch with one command.

Because this project applies GitOps practices, it's the source of truth for _my_ homelab, so you'll need to fork it to make it yours:

[:fontawesome-solid-code-fork: Fork khuedoan/homelab](https://github.com/serpro69/ktchn8s/fork){ .md-button }

By using this project you agree to [the license](../../info/license.md).

Provided that you've finalized the [network configuration](./network.md), which is optional, and ensured [metal requirements](./metal.md#pre-requisites) and dependencies on [external resources](./external.md) are met, simply run:

```bash
make ktchn8s
```

and observe the magic happen.

If you want to have more control over the deployment (possibly to run some verifications after each deployment stage), you can follow the following workflow:

- [Metal provisioning](./metal.md)
- System resources provisioning: `make system`
- [External resources](./external.md) provisioning: `make external`
- Finalize the installation: `make finalize`
    - Followed by [manual post-install steps](../post_install.md)
