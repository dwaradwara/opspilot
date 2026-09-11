provider "aws" {
  region  = "eu-central-1"

  default_tags {
    tags = {
      Project     = "OpsPilot"
      Environment = "staging"
      ManagedBy   = "Terraform"
    }
  }
}