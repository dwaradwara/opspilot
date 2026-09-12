output "cache_subnet_group_name" {
  description = "Name of the ElastiCache subnet group"
  value       = aws_elasticache_subnet_group.this.name
}
output "redis_primary_endpoint" {
  description = "Primary endpoint address of the staging Redis replication group"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_port" {
  description = "Port of the staging Redis replication group"
  value       = aws_elasticache_replication_group.redis.port
}

output "redis_replication_group_id" {
  description = "ID of the staging Redis replication group"
  value       = aws_elasticache_replication_group.redis.id
}