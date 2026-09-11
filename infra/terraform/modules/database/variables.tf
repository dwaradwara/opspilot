variable "name" {
  description = "Name prefix for database resources"
  type        = string
}

variable "database_subnet_ids" {
  description = "Private subnet IDs used by the RDS subnet group"
  type        = list(string)
}
variable "security_group_id" {
  description = "Security group ID attached to the RDS PostgreSQL instance"
  type        = string
}

variable "instance_class" {
  description = "RDS PostgreSQL instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "Allocated PostgreSQL storage in GiB"
  type        = number
  default     = 20
}

variable "database_name" {
  description = "Initial PostgreSQL database name"
  type        = string
  default     = "opspilot"
}

variable "master_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "opspilot_admin"
}