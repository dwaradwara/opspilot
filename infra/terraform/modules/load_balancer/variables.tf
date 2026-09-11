variable "name" {
  description = "Name prefix for load balancer resources"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID used by the target group"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs used by the application load balancer"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID attached to the application load balancer"
  type        = string
}

variable "target_port" {
  description = "Port used by the OpsPilot API target group"
  type        = number
  default     = 8000
}

variable "health_check_path" {
  description = "HTTP path used by the ALB target group health check"
  type        = string
  default     = "/health"
}