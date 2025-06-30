# Use Both GitHub and Gitea

Even though we self-host Gitea, you may still want to use GitHub as a backup and for discovery.

Add both push URLs (replace my repositories with yours):

```sh
git remote set-url --add --push origin git@git.0xbad.cloud:ops/homelab
git remote set-url --add --push origin git@github.com:serpro69/ktchn8s

git remote --v
# origin  git@github.com:serpro69/ktchn8s.git (fetch)
# origin  git@git.0xbad.cloud:ops/homelab.git (push)
# origin  git@github.com:serpro69/ktchn8s.git (push)
```

Now you can just run `git push` like usual and it will push to both GitHub and Gitea.
