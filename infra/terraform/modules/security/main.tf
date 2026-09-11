resource "aws_security_group" "alb" {
  name        = "${var.name}-alb-sg"
  description = "Security group for public application load balancer"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name}-alb-sg"
  }
}

resource "aws_security_group" "app" {
  name        = "${var.name}-app-sg"
  description = "Security group for application services"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name}-app-sg"
  }
}

resource "aws_security_group" "database" {
  name        = "${var.name}-database-sg"
  description = "Security group for PostgreSQL"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name}-database-sg"
  }
}

resource "aws_security_group" "redis" {
  name        = "${var.name}-redis-sg"
  description = "Security group for Redis"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name}-redis-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "Allow public HTTP traffic"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Allow ALB traffic to application"
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = var.app_port
  to_port                      = var.app_port
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  description                  = "Allow application traffic from ALB"
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = var.app_port
  to_port                      = var.app_port
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "app_all" {
  security_group_id = aws_security_group.app.id
  description       = "Allow application outbound traffic"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_ingress_rule" "database_from_app" {
  security_group_id            = aws_security_group.database.id
  description                  = "Allow PostgreSQL only from application"
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = var.postgres_port
  to_port                      = var.postgres_port
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_app" {
  security_group_id            = aws_security_group.redis.id
  description                  = "Allow Redis only from application"
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = var.redis_port
  to_port                      = var.redis_port
  ip_protocol                  = "tcp"
}