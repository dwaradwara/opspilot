variable "name" {
  description = "Name prefix for database resources"
  type        = string
}

variable "database_subnet_ids" {
  description = "Private subnet IDs used by the RDS subnet group"
  type        = list(string)
}