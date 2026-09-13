output "service_name" {
  description = "Name of the observability ECS service"
  value       = aws_ecs_service.observability.name
}

output "task_definition_arn" {
  description = "ARN of the observability task definition"
  value       = aws_ecs_task_definition.observability.arn
}

output "grafana_target_group_arn" {
  description = "ARN of the Grafana ALB target group"
  value       = aws_lb_target_group.grafana.arn
}

output "observability_security_group_id" {
  description = "Security group ID for observability services"
  value       = aws_security_group.observability.id
}