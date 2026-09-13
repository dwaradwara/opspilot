variable "name" {
  description = "Name prefix for observability resources"
  type        = string
}

variable "vpc_id" {
  description = "VPC where observability resources are deployed"
  type        = string
}

variable "cluster_id" {
  description = "ECS cluster ID used by the observability service"
  type        = string
}

variable "subnet_ids" {
  description = "Subnets used by the observability ECS service"
  type        = list(string)
}

variable "alb_listener_arn" {
  description = "Existing application load balancer HTTP listener ARN"
  type        = string
}

variable "alb_security_group_id" {
  description = "Security group ID of the existing application load balancer"
  type        = string
}

variable "api_alb_dns_name" {
  description = "DNS name of the staging API load balancer"
  type        = string
}

variable "assign_public_ip" {
  description = "Whether the observability task receives a public IP"
  type        = bool
  default     = true
}

variable "cpu" {
  description = "Fargate CPU units for the observability task"
  type        = number
  default     = 512
}

variable "memory" {
  description = "Fargate memory in MiB for the observability task"
  type        = number
  default     = 2048
}

variable "prometheus_image" {
  description = "Prometheus container image"
  type        = string
  default     = "prom/prometheus:v3.5.0"
}

variable "grafana_image" {
  description = "Grafana container image"
  type        = string
  default     = "grafana/grafana:12.1.1"
}

variable "config_init_image" {
  description = "Container image used to generate runtime monitoring configuration"
  type        = string
  default     = "alpine:3.20"
}
variable "loki_image" {
  description = "Loki container image"
  type        = string
  default     = "grafana/loki:3.5.0"
}

variable "app_security_group_id" {
  description = "Security group ID used by the OpsPilot application service"
  type        = string
}

variable "tempo_image" {
  description = "Tempo container image"
  type        = string
  default     = "grafana/tempo:2.10.7"
}

variable "alertmanager_image" {
  description = "Alertmanager container image"
  type        = string
  default     = "prom/alertmanager:v0.28.1"
}
