variable "name" {
  description = "Name prefix for GitHub Actions IAM resources"
  type        = string
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the AWS role"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch allowed to assume the AWS role"
  type        = string
  default     = "master"
}

variable "ecr_repository_arn" {
  description = "ARN of the ECR repository GitHub Actions may push to"
  type        = string
}
variable "github_owner_id" {
  description = "Immutable GitHub owner ID used in OIDC subject claims"
  type        = string
}

variable "github_repository_id" {
  description = "Immutable GitHub repository ID used in OIDC subject claims"
  type        = string
}