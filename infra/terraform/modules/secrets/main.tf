resource "aws_secretsmanager_secret" "jwt" {
  name        = "${var.name}/jwt-secret"
  description = "JWT signing secret for OpsPilot"

  tags = {
    Name = "${var.name}-jwt-secret"
  }
}