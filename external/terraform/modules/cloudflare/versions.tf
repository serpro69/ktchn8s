terraform {
  required_version = "~> 1.9"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.52.0"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.26.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "3.7.2"
    }
  }
}
