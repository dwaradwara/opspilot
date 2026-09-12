resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.name}-cache-subnet-group"
  subnet_ids = var.cache_subnet_ids

  tags = {
    Name = "${var.name}-cache-subnet-group"
  }
}
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.name}-redis"
  description          = "OpsPilot staging Redis"

  engine    = "redis"
  node_type = var.node_type
  port      = var.port

  num_cache_clusters         = 1
  automatic_failover_enabled = false
  multi_az_enabled           = false

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = [var.security_group_id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  snapshot_retention_limit = 1
  apply_immediately        = true

  tags = {
    Name = "${var.name}-redis"
  }
}