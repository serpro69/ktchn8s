---
icon: material/crosshairs-question
title: Renovate
---

# :material-crosshairs-question: Troubleshooting Renovate

## Renovate pods failing with "Authentication failure" error

I've had this strange issue when I just setup the cluster, and I could not find the root-cause, but after configuring renovate, which created an initial "Configure Renovate" PR, no more PRs were made from renovate.

Looking at the pods logs, I could only see this:

```
FATAL: Authentication failure
  INFO: Renovate is exiting with a non-zero code due to the following logged errors
    "loggerErrors": [
      {
        "name": "renovate",
        "level": 60,
        "logContext": "tgi_4XBKjKBu6X7dkrQZ_",
        "msg": "Authentication failure"
      }
    ]
```

Pod events were empty, which hinted at a very early failure in the pod startup.

First thing I cheched was for the renovate token to be present in `global-secrets` namespace, as well as in `gitea_admin` user profile (via gitea UI).

I also checked that the `gitea.renovate` secret in `global-secrets` namespace matched `renovate-secret` in `renovate` namespace:

```bash
kubectl -n global-secrets get secrets gitea.renovate -o jsonpath='{.data.token}' | base64 -d

kubectl -n renovate get secrets renovate-secret -o jsonpath='{.data.RENOVATE_TOKEN}' | base64 -d
```

I then re-ran [post-install script](https://github.com/serpro69/ktchn8s/blob/master/scripts/post-install.py) (which was probably redundant since all the secrets were already in place) and decided to try to trigger the job manually, instead of waiting until next morning, with:

```bash
kubectl -n renovate create job --from=CronJob/renovate manual-renovate-run-$(date +%s)
```

The job completed successfully, and I could see the PRs being created.

I'm still baffled by the root-case of this issue, and I don't know why running a manual job fixed it. However, I do there might have been some race conditions that caused the pods to fail. I've also pused this [commit](https://github.com/serpro69/ktchn8s/commit/5c97deee762ff2016742535a81bc77c74132ae00) which should improve the `renovate -> gitea` interaction a bit and hopefully would fix this problem on a newly-created clusters as well.
