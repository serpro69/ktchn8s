variable "cloudflare" {
  type = object({
    email      = string
    account_id = string
    api_key    = string
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
