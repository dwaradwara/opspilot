output "db_subnet_group_name" {
  description = "Name of the RDS DB subnet group"
  value       = aws_db_subnet_group.this.name
}
output "database_address" {
  description = "DNS address of the PostgreSQL RDS instance"
  value       = aws_db_instance.postgres.address
}

output "database_port" {
  description = "Port of the PostgreSQL RDS instance"
  value       = aws_db_instance.postgres.port
}

output "database_name" {
  description = "Initial PostgreSQL database name"
  value       = aws_db_instance.postgres.db_name
}

output "master_user_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the RDS master credentials"
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}
output "master_username" {
  description = "PostgreSQL master username"
  value       = aws_db_instance.postgres.username
}