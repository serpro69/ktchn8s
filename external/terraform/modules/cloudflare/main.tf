resource "random_password" "tunnel_secret" {
  length  = 64
  special = false
}

resource "cloudflare_zero_trust_tunnel_cloudflared" "homelab" {
  account_id    = var.cloudflare_account_id
  name          = "homelab"
  tunnel_secret = base64encode(random_password.tunnel_secret.result)
}

# Not proxied, not accessible. Just a record for auto-created CNAMEs by external-dns.
resource "cloudflare_dns_record" "tunnel" {
  zone_id = var.cloudflare_zone_id
  type    = "CNAME"
  name    = "homelab-tunnel.${var.cloudflare_domain}"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.homelab.id}.cfargotunnel.com"
  proxied = false
  ttl     = 1 # Auto
}

resource "kubernetes_secret" "cloudflared_credentials" {
  metadata {
    name      = "cloudflared-credentials"
    namespace = "cloudflared"

    annotations = {
      "app.kubernetes.io/managed-by" = "Terraform"
    }
  }

  data = {
    "credentials.json" = jsonencode({
      AccountTag   = var.cloudflare_account_id
      TunnelName   = cloudflare_zero_trust_tunnel_cloudflared.homelab.name
      TunnelID     = cloudflare_zero_trust_tunnel_cloudflared.homelab.id
      TunnelSecret = base64encode(random_password.tunnel_secret.result)
    })
  }
}

resource "cloudflare_api_token" "external_dns" {
  name = "homelab_external_dns"

  policies = [{
    effect = "allow"
    permission_groups = [{
      id = local.api_token_permission_groups.zone["Zone Read"],
      }, {
      id = local.api_token_permission_groups.zone["DNS Write"]
    }]
    resources = {
      "com.cloudflare.api.account.zone.*" = "*"
    }
  }]
}

resource "kubernetes_secret" "external_dns_token" {
  metadata {
    name      = "cloudflare-api-token"
    namespace = "external-dns"

    annotations = {
      "app.kubernetes.io/managed-by" = "Terraform"
    }
  }

  data = {
    "value" = cloudflare_api_token.external_dns.value
  }
}

resource "cloudflare_api_token" "cert_manager" {
  name = "homelab_cert_manager"

  policies = [{
    effect = "allow"
    permission_groups = [{
      id = local.api_token_permission_groups.zone["Zone Read"],
      }, {
      id = local.api_token_permission_groups.zone["DNS Write"]
    }]
    resources = {
      "com.cloudflare.api.account.zone.*" = "*"
    }
  }]
}

resource "kubernetes_secret" "cert_manager_token" {
  metadata {
    name      = "cloudflare-api-token"
    namespace = "cert-manager"

    annotations = {
      "app.kubernetes.io/managed-by" = "Terraform"
    }
  }

  data = {
    "api-token" = cloudflare_api_token.cert_manager.value
  }
}

resource "cloudflare_bot_management" "main" {
  zone_id            = var.cloudflare_zone_id
  ai_bots_protection = "block"
  crawler_protection = "enabled"
  enable_js          = true
  fight_mode         = true

  lifecycle {
    ignore_changes = [
      auto_update_model,
      optimize_wordpress,
      sbfm_definitely_automated,
      sbfm_likely_automated,
      sbfm_static_resource_protection,
      sbfm_verified_bots,
      stale_zone_configuration,
      suppress_session_score,
      using_latest_model,
    ]
  }
}
