variable "name" {
  description = "Name prefix for cache resources"
  type        = string
}

variable "cache_subnet_ids" {
  description = "Private subnet IDs used by the ElastiCache subnet group"
  type        = list(string)
}