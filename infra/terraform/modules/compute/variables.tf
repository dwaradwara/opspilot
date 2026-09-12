variable "name" {
  description = "Name prefix for ECS compute resources"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs used by ECS Fargate tasks"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID attached to ECS tasks"
  type        = string
}

variable "container_image" {
  description = "Container image used by the OpsPilot API task"
  type        = string
}

variable "container_port" {
  description = "Port exposed by the OpsPilot API container"
  type        = number
  default     = 8000
}

variable "cpu" {
  description = "Fargate task CPU units"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate task memory in MiB"
  type        = number
  default     = 512
}
variable "target_group_arn" {
  description = "ALB target group ARN used by the ECS API service"
  type        = string
}

variable "desired_count" {
  description = "Number of API Fargate tasks"
  type        = number
  default     = 1
}

variable "assign_public_ip" {
  description = "Whether Fargate tasks receive a public IP"
  type        = bool
  default     = false
}