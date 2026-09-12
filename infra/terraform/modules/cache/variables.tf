variable "name" {
  description = "Name prefix for cache resources"
  type        = string
}

variable "cache_subnet_ids" {
  description = "Private subnet IDs used by the ElastiCache subnet group"
  type        = list(string)
}
variable "security_group_id" {
  description = "Security group ID attached to the ElastiCache Redis replication group"
  type        = string
}

variable "node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t4g.micro"
}

variable "port" {
  description = "Redis port"
  type        = number
  default     = 6379
}