---
icon: material/crosshairs-question
title: Use Both GitHub and Gitea
---

# :material-crosshairs-question: HowTo use both github and gitea

Even though we self-host Gitea, you may still want to use GitHub as a backup and for discovery.

## Pushing to both remotes with a single command

Add both push URLs (_NB! replace my repositories with yours_):

```sh
git remote set-url --add --push origin git@git.0xbad.cloud:ops/homelab
git remote set-url --add --push origin git@github.com:serpro69/ktchn8s

git remote --v
# origin  git@github.com:serpro69/ktchn8s.git (fetch)
# origin  git@git.0xbad.cloud:ops/homelab.git (push)
# origin  git@github.com:serpro69/ktchn8s.git (push)
```

Now you can just run `git push` like usual and it will push to both GitHub and Gitea.

## Pushing to a specific remote

_At this moment I prefer this option for more control and flexibility, even though technically I need to run `git push` twice to update both repos._

Add a new `gitea` remote:

```sh
git remote add gitea git@git.0xbad.cloud:ops/homelab.git

git remote --v
# gitea   git@git.0xbad.cloud:ops/homelab.git (fetch)
# gitea   git@git.0xbad.cloud:ops/homelab.git (push)
# origin  git@github.com:serpro69/ktchn8s.git (fetch)
# origin  git@github.com:serpro69/ktchn8s.git (push)
```

Now when you run `git push`, it will push to github (`origin` remote). 
To push to `gitea` add the new remote name to the push command: `git push gitea`.
