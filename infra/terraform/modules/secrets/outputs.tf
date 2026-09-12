output "jwt_secret_arn" {
  description = "ARN of the OpsPilot JWT signing secret"
  value       = aws_secretsmanager_secret.jwt.arn
}