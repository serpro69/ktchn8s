---
icon: material/console
title: Post-Install
---

# :material-console: Post-install

## Backup secrets

Save the following files to a safe location like a password manager (if you're using the sandbox, you can skip this step):

- `~/.ssh/homelab_id_ed25519`
- `~/.ssh/homelab_id_ed25519.pub`
- `./metal/kubeconfig.yaml` (optional, since you can always restore it via `scp` from one of the nodes in the cluster)

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

## Apps

### Gitea

- Create a new user account
  _NB! you can also [onboard a new user](../guides/how_to_onboard_users.md) and login to gitea with dex (this is optional, and you can also later associate your onboarded dex user with gitea user). If you don't see "login with Dex" on the gitea page, try to re-run the [`post-install.py`](https://github.com/serpro69/ktchn8s/blob/master/scripts/post-install.py) script which adds [dex oauth to gitea](https://github.com/serpro69/ktchn8s/blob/e90594b6a6e0b0cce76f86b8d0fe9b0b90c2f16f/scripts/post-install.py#L127-L152)._
    - (optional) Add ssh key so you can push with ssh
    - Add your github email if you want to associate commits made in gitea with your github account
        - You can use the noreply email address as well, if your real email is hidden in github
- Login with `admin` user and add your personal user to the `Owners` team in the `ops` organization

### Woodpecker

- Login with gitea using `gitea_admin` user
- Authorize the application
- Add the `ops/homelab` repository
