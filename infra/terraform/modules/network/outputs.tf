output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets."
  value       = aws_subnet.public[*].id
}

output "private_app_subnet_ids" {
  description = "IDs of the private application subnets."
  value       = aws_subnet.private_app[*].id
}

output "database_subnet_ids" {
  description = "IDs of the database subnets."
  value       = aws_subnet.database[*].id
}

output "public_route_table_id" {
  description = "ID of the public route table."
  value       = aws_route_table.public.id
}

output "private_app_route_table_id" {
  description = "ID of the private application route table."
  value       = aws_route_table.private_app.id
}

output "database_route_table_id" {
  description = "ID of the database route table."
  value       = aws_route_table.database.id
}