terraform {
  backend "s3" {
    bucket       = "opspilot-tfstate-a09c02d0"
    key          = "staging/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}