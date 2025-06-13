---
title: "Use cloudflared to expose a Kubernetes app to the Internet"
source: "https://developers.cloudflare.com/cloudflare-one/tutorials/many-cfd-one-tunnel/"
author:
  - "[[Overview]]"
  - "[[Validate JWTs]]"
  - "[[Application token]]"
  - "[[CORS]]"
published: 2024-08-20
created: 2025-06-13
description: "You can use Cloudflare Tunnel to connect applications and servers to Cloudflare's network. Tunnel relies on a piece of software, cloudflared, to create those connections."
tags:
  - "clippings"
---
[Skip to content](https://developers.cloudflare.com/cloudflare-one/tutorials/many-cfd-one-tunnel/#_top)

You can use [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) to connect applications and servers to Cloudflare's network. Tunnel relies on a piece of software, [cloudflared ↗](https://github.com/cloudflare/cloudflared), to create those connections.

The same Tunnel can be run from multiple instances of `cloudflared`, giving you the ability to run many `cloudflared` replicas to scale your system when incoming traffic changes.

In this tutorial, we will walk through running an application as a Kubernetes [Service ↗](https://kubernetes.io/docs/concepts/services-networking/service/), and then running `cloudflared` in a separate [Deployment ↗](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/).

This architecture allows `cloudflared` instances to proxy Internet traffic into whichever Kubernetes Service it was configured to.

**This tutorial covers how to:**

- Deploy `cloudflared` in a replica model
- Proxy traffic into a Kubernetes service with Tunnel

**Time to complete: 45 minutes**

## Install cloudflared

Start by [downloading and installing](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) the lightweight Cloudflare Tunnel daemon, `cloudflared`. Reference our installation guide for instructions on how to install `cloudflared` on your operating system.

Once installed, you can use the `tunnel login` command in `cloudflared` to obtain a certificate.

In the example below, simply change `<example-tunnel>` to the name you wish to assign to your Tunnel.

```sh
cloudflared tunnel create example-tunnel
```

```sh
Tunnel credentials written to /Users/cf000197/.cloudflared/ef824aef-7557-4b41-a398-4684585177ad.json. cloudflared chose this file based on where your origin certificate was found. Keep this file secret. To revoke these credentials, delete the tunnel.

Created tunnel example-tunnel with id ef824aef-7557-4b41-a398-4684585177ad
```

Next, you will upload the generated Tunnel credential file as a secret to your Kubernetes cluster. You will also need to provide the filepath that the Tunnel credentials file was created under. You can find that path in the output of `cloudflared tunnel create <example-tunnel>` above.

```sh
kubectl create secret generic tunnel-credentials \
--from-file=credentials.json=/Users/cf000197/.cloudflared/ef824aef-7557-4b41-a398-4684585177ad.json
```

1. Go to the Cloudflare dashboard.
2. Go to the DNS tab.
3. Now create a CNAME targeting `.cfargotunnel.com`. In this example, the tunnel ID is ef824aef-7557-4b41-a398-4684585177ad, so create a CNAME record specifically targeting `ef824aef-7557-4b41-a398-4684585177ad.cfargotunnel.com`.

You can also create multiple CNAME records targeting the same Tunnel, if desired.

Alternatively, you can perform this step from the command line by running `cloudflared tunnel route dns <tunnel> <hostname>`. For example, `cloudflared tunnel route dns example-tunnel tunnel.example.com`. You can use a similar method to route traffic to `cloudflared` from a [Cloudflare Load Balancer ↗](https://www.cloudflare.com/load-balancing/), see [docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/routing-to-tunnel/lb/) for details.

## Deploy cloudflared

Now, we'll deploy `cloudflared` by applying its [manifest ↗](https://github.com/cloudflare/argo-tunnel-examples/blob/master/named-tunnel-k8s/cloudflared.yaml). This will start a [Deployment ↗](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) for running `cloudflared` and a [ConfigMap ↗](https://kubernetes.io/docs/concepts/configuration/configmap/) with `cloudflared` 's config. When Cloudflare receives traffic for the DNS or Load Balancing hostname you configured in the previous step, it will send that traffic to the `cloudflared` instances running in this deployment. Then, those `cloudflared` instances will proxy the request to your [application's Service ↗](https://github.com/cloudflare/argo-tunnel-examples/blob/master/named-tunnel-k8s/app.yaml).

```sh
kubectl apply -f cloudflared.yaml
```

```sh
deployment.apps/cloudflared created
configmap/cloudflared configured
```

```plaintext
$ kubectl get pods
    NAME                                  READY   STATUS    RESTARTS   AGE
    cloudflared-57746f77fd-frc99          1/1     Running   0          12m
    cloudflared-57746f77fd-xht8n          1/1     Running   0          12m
    httpbin-deployment-67f749774f-42tqj   1/1     Running   0          20h
    $ kubectl logs $(kubectl get pod -l app=cloudflared -o jsonpath="{.items[0].metadata.name}")
    2021-05-04T17:39:49Z INF Starting tunnel tunnelID=ef824aef-7557-4b41-a398-4684585177ad
    2021-05-04T17:39:49Z INF Version
    2021-05-04T17:39:49Z INF GOOS: linux, GOVersion: go1.15.7, GoArch: amd64
    2021-05-04T17:39:49Z INF Settings: map[config:/etc/cloudflared/config/config.yaml cred-file:/etc/cloudflared/creds/credentials.json credentials-file:/etc/cloudflared/creds/credentials.json metrics:0.0.0.0:2000 no-autoupdate:true]
    2021-05-04T17:39:49Z INF Generated Connector ID: 4c5dc5d3-8e10-480e-ac74-e385e591553e
    2021-05-04T17:39:49Z INF Initial protocol h2mux
    2021-05-04T17:39:49Z INF Starting metrics server on [::]:2000/metrics
```

At this point, you'll see the httpbin welcome page.

In this tutorial, we've covered how the same Tunnel can be run in many `cloudflared` processes. You can also use this knowledge to support elastic scaling, graceful `cloudflared` restarts, and rolling upgrades in the future.

We love to hear your feedback! Join the discussion in our [community ↗](https://community.cloudflare.com/).
