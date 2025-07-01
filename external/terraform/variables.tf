variable "cloudflare" {
  type = object({
    email      = string
    api_key    = string
    account_id = string
    zone_id    = string
  })
  sensitive = true
}

variable "ntfy" {
  type = object({
    url   = string
    topic = string
  })
  sensitive = true
}

variable "extra_secrets" {
  type        = map(string)
  description = "Key-value pairs of extra secrets that cannot be randomly generated (e.g. third party API tokens)"
  sensitive   = true
  default     = {}
}
