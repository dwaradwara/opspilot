resource "aws_ecs_cluster" "this" {
  name = "${var.name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.name}-cluster"
  }
}

data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = "${var.name}-ecs-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name               = "${var.name}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}
resource "aws_cloudwatch_log_group" "api" {
  name              = "/opspilot/${var.name}/api"
  retention_in_days = 7

  tags = {
    Name = "${var.name}-api-logs"
  }
}
data "aws_region" "current" {}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = tostring(var.cpu)
  memory = tostring(var.memory)

  execution_role_arn = aws_iam_role.task_execution.arn
  task_role_arn      = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = var.container_image
      essential = true

      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "ENVIRONMENT"
          value = "staging"
        },
        {
          name  = "DATABASE_HOST"
          value = var.database_host
        },
        {
          name  = "DATABASE_PORT"
          value = tostring(var.database_port)
        },
        {
          name  = "DATABASE_NAME"
          value = var.database_name
        },
        {
          name  = "DATABASE_USER"
          value = var.database_user
        },
        {
          name  = "REDIS_URL"
          value = "rediss://${var.redis_host}:${var.redis_port}/0"
        }
      ]

      secrets = [
        {
          name      = "DATABASE_PASSWORD"
          valueFrom = "${var.database_secret_arn}:password::"
        },
        {
          name      = "JWT_SECRET"
          valueFrom = var.jwt_secret_arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = data.aws_region.current.region
          awslogs-stream-prefix = "api"
        }
      }
    }
  ])

  tags = {
    Name = "${var.name}-api-task"
  }
}
resource "aws_ecs_service" "api" {
  name            = "${var.name}-api-service"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  health_check_grace_period_seconds = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = var.assign_public_ip
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "api"
    container_port   = var.container_port
  }

  lifecycle {
    ignore_changes = [
      task_definition,
    ]
  }

  tags = {
    Name = "${var.name}-api-service"
  }
}
data "aws_iam_policy_document" "task_execution_secrets" {
  statement {
    sid = "ReadDatabaseSecret"

    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = [
      var.database_secret_arn,
      var.jwt_secret_arn,
    ]
  }
}

resource "aws_iam_role_policy" "task_execution_secrets" {
  name   = "${var.name}-ecs-secret-access"
  role   = aws_iam_role.task_execution.id
  policy = data.aws_iam_policy_document.task_execution_secrets.json
}