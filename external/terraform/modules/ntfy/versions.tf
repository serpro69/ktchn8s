terraform {
  required_version = "~> 1.9"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.26.0"
    }
  }
}
