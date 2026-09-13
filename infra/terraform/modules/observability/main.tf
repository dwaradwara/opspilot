resource "aws_security_group" "observability" {
  name        = "${var.name}-observability-sg"
  description = "Security group for OpsPilot observability services"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name}-observability-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "grafana_from_alb" {
  security_group_id            = aws_security_group.observability.id
  description                  = "Allow Grafana traffic from the application load balancer"
  referenced_security_group_id = var.alb_security_group_id

  from_port   = 3000
  to_port     = 3000
  ip_protocol = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "observability_all" {
  security_group_id = aws_security_group.observability.id
  description       = "Allow observability services outbound access"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_grafana" {
  security_group_id            = var.alb_security_group_id
  description                  = "Allow ALB traffic to Grafana"
  referenced_security_group_id = aws_security_group.observability.id

  from_port   = 3000
  to_port     = 3000
  ip_protocol = "tcp"
}

resource "aws_lb_target_group" "grafana" {
  name        = "${var.name}-grafana-tg"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    path                = "/grafana/api/health"
    protocol            = "HTTP"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${var.name}-grafana-tg"
  }
}

resource "aws_lb_listener_rule" "grafana" {
  listener_arn = var.alb_listener_arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana.arn
  }

  condition {
    path_pattern {
      values = [
        "/grafana",
        "/grafana/*",
      ]
    }
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
  name               = "${var.name}-observability-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${var.name}-observability-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_cloudwatch_log_group" "observability" {
  name              = "/opspilot/${var.name}/observability"
  retention_in_days = 7

  tags = {
    Name = "${var.name}-observability-logs"
  }
}

data "aws_region" "current" {}
resource "aws_ecs_task_definition" "observability" {
  family                   = "${var.name}-observability"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = tostring(var.cpu)
  memory = tostring(var.memory)

  execution_role_arn = aws_iam_role.task_execution.arn

  volume {
    name = "monitoring-config"
  }

  container_definitions = jsonencode([
    {
      name      = "config-init"
      image     = var.config_init_image
      essential = false

      entryPoint = [
        "/bin/sh",
        "-c"
      ]

      command = [
        join("", [
          "mkdir -p /config/datasources /config/dashboards /config/dashboard-json && printf '%s' '",

          base64encode(<<-EOT
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "opspilot-staging-api"
    metrics_path: /metrics
    scheme: http
    static_configs:
      - targets:
          - "${var.api_alb_dns_name}:80"
        labels:
          environment: "staging"
EOT
          ),

          "' | base64 -d > /config/prometheus.yml && printf '%s' '",

          base64encode(<<-EOT
apiVersion: 1

datasources:
  - name: Prometheus
    uid: opspilot-prometheus
    type: prometheus
    access: proxy
    url: http://127.0.0.1:9090
    isDefault: true
    editable: false
EOT
          ),

          "' | base64 -d > /config/datasources/prometheus.yml && printf '%s' '",

          base64encode(<<-EOT
apiVersion: 1

providers:
  - name: OpsPilot
    orgId: 1
    folder: OpsPilot
    type: file
    disableDeletion: true
    editable: false
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/provisioning/dashboard-json
EOT
          ),

          "' | base64 -d > /config/dashboards/opspilot.yml && printf '%s' '",

          base64encode(file("${path.module}/opspilot-staging-overview.json")),

          "' | base64 -d > /config/dashboard-json/opspilot-staging-overview.json"
        ])
      ]

      mountPoints = [
        {
          sourceVolume  = "monitoring-config"
          containerPath = "/config"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.observability.name
          awslogs-region        = data.aws_region.current.region
          awslogs-stream-prefix = "config-init"
        }
      }
    },

    {
      name      = "prometheus"
      image     = var.prometheus_image
      essential = true

      dependsOn = [
        {
          containerName = "config-init"
          condition     = "SUCCESS"
        }
      ]

      portMappings = [
        {
          containerPort = 9090
          protocol      = "tcp"
        }
      ]

      command = [
        "--config.file=/etc/opspilot-monitoring/prometheus.yml",
        "--storage.tsdb.path=/prometheus",
        "--storage.tsdb.retention.time=24h",
      ]

      mountPoints = [
        {
          sourceVolume  = "monitoring-config"
          containerPath = "/etc/opspilot-monitoring"
          readOnly      = true
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.observability.name
          awslogs-region        = data.aws_region.current.region
          awslogs-stream-prefix = "prometheus"
        }
      }
    },

    {
      name      = "grafana"
      image     = var.grafana_image
      essential = true

      dependsOn = [
        {
          containerName = "config-init"
          condition     = "SUCCESS"
        },
        {
          containerName = "prometheus"
          condition     = "START"
        }
      ]

      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "GF_SERVER_ROOT_URL"
          value = "http://${var.api_alb_dns_name}/grafana/"
        },
        {
          name  = "GF_SERVER_SERVE_FROM_SUB_PATH"
          value = "true"
        },
        {
          name  = "GF_AUTH_ANONYMOUS_ENABLED"
          value = "true"
        },
        {
          name  = "GF_AUTH_ANONYMOUS_ORG_ROLE"
          value = "Viewer"
        },
        {
          name  = "GF_USERS_ALLOW_SIGN_UP"
          value = "false"
        },
        {
          name  = "GF_SECURITY_DISABLE_INITIAL_ADMIN_CREATION"
          value = "true"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "monitoring-config"
          containerPath = "/etc/grafana/provisioning"
          readOnly      = true
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.observability.name
          awslogs-region        = data.aws_region.current.region
          awslogs-stream-prefix = "grafana"
        }
      }
    }
  ])

  tags = {
    Name = "${var.name}-observability-task"
  }
}
resource "aws_ecs_service" "observability" {
  name            = "${var.name}-observability-service"
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.observability.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  health_check_grace_period_seconds = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.observability.id]
    assign_public_ip = var.assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.grafana.arn
    container_name   = "grafana"
    container_port   = 3000
  }

  depends_on = [
    aws_lb_listener_rule.grafana,
  ]

  tags = {
    Name = "${var.name}-observability-service"
  }
}