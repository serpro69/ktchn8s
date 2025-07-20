locals {
  api_token_permission_groups = {
    user    = { for token in data.cloudflare_api_token_permission_groups_list.all.result : token.name => token.id if token.scopes[0] == "com.cloudflare.api.user" }
    zone    = { for token in data.cloudflare_api_token_permission_groups_list.all.result : token.name => token.id if token.scopes[0] == "com.cloudflare.api.account.zone" }
    account = { for token in data.cloudflare_api_token_permission_groups_list.all.result : token.name => token.id if token.scopes[0] == "com.cloudflare.api.account" }
    r2      = { for token in data.cloudflare_api_token_permission_groups_list.all.result : token.name => token.id if token.scopes[0] == "com.cloudflare.edge.r2.bucket" }
  }
}

data "cloudflare_api_token_permission_groups_list" "all" {
  max_items = 999999
}

