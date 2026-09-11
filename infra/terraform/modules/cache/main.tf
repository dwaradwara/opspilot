resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.name}-cache-subnet-group"
  subnet_ids = var.cache_subnet_ids

  tags = {
    Name = "${var.name}-cache-subnet-group"
  }
}