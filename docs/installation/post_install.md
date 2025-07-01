---
icon: material/console
title: Post-Install
---

# :material-console: Post-install

## Backup secrets

Save the following files to a safe location like a password manager (if you're using the sandbox, you can skip this step):

- `~/.ssh/homelab_id_ed25519`
- `~/.ssh/homelab_id_ed25519.pub`
- `./metal/kubeconfig.yaml`

## Admin credentials

- ArgoCD:
    - Username: `admin`
    - Password: run `./scripts/argocd-admin-password`
- Gitea:
    - Username: `gitea_admin`
    - Password: get from `global-secrets` namespace
- Kanidm:
    - Usernames: `admin` and `idm_admin`
    - Password: run `./scripts/kanidm-reset-password admin` and `./scripts/kanidm-reset-password idm_admin`
- Jellyfin and other applications in the \*arr stack: see the [dedicated guide for media management](../guides/how_to_for_media_management.md)
- Other apps:
    - Username: `admin`
    - Password: get from `global-secrets` namespace

## Backup

Now is a good time to set up backups for your homelab.
Follow the [backup and restore guide](../guides/how_to_backup_and_restore.md) to get started.

## Run the full test suite

After the homelab has been stabilized, you can run the full test suite to ensure that everything is working properly:

```sh
make test
```

!!! warning
    The "full" test suite is still in its early stages; any contributions are greatly appreciated.
