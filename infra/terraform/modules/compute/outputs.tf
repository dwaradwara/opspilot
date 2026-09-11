output "cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.this.id
}

output "cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.this.name
}

output "task_execution_role_arn" {
  description = "IAM role ARN used by ECS to start tasks"
  value       = aws_iam_role.task_execution.arn
}

output "task_role_arn" {
  description = "IAM role ARN used by the OpsPilot application containers"
  value       = aws_iam_role.task.arn
}
output "api_task_definition_arn" {
  description = "ARN of the OpsPilot API ECS task definition"
  value       = aws_ecs_task_definition.api.arn
}