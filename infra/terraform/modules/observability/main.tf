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
  task_role_arn      = aws_iam_role.observability_task.arn

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

rule_files:
  - /etc/opspilot-monitoring/prometheus-rules.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - "127.0.0.1:9093"

remote_write:
  - url: "${aws_prometheus_workspace.metrics.prometheus_endpoint}api/v1/remote_write"
    sigv4:
      region: "${data.aws_region.current.region}"
    queue_config:
      capacity: 2500
      max_samples_per_send: 1000
      max_shards: 4
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

  - name: Loki
    uid: opspilot-loki
    type: loki
    access: proxy
    url: http://127.0.0.1:3100
    isDefault: false
    editable: false

  - name: Tempo
    uid: opspilot-tempo
    type: tempo
    access: proxy
    url: http://127.0.0.1:3200
    isDefault: false
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

          "' | base64 -d > /config/dashboard-json/opspilot-staging-overview.json && printf '%s' '",

          base64encode(templatefile("${path.module}/loki.yml.tftpl", {
            region      = data.aws_region.current.region
            bucket_name = aws_s3_bucket.loki.bucket
          })),

          "' | base64 -d > /config/loki.yml && printf '%s' '",

          base64encode(templatefile("${path.module}/tempo.yml.tftpl", {
            region      = data.aws_region.current.region
            bucket_name = aws_s3_bucket.tempo.bucket
          })),

          "' | base64 -d > /config/tempo.yml && printf '%s' '",

          base64encode(file("${path.module}/prometheus-rules.yml")),

          "' | base64 -d > /config/prometheus-rules.yml && printf '%s' '",

          base64encode(templatefile("${path.module}/alertmanager.yml.tftpl", {
            region        = data.aws_region.current.region
            sns_topic_arn = aws_sns_topic.alerts.arn
          })),

          "' | base64 -d > /config/alertmanager.yml"
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
      name              = "alertmanager"
      image             = var.alertmanager_image
      essential         = true
      memoryReservation = 128

      dependsOn = [
        {
          containerName = "config-init"
          condition     = "SUCCESS"
        }
      ]

      portMappings = [
        {
          containerPort = 9093
          protocol      = "tcp"
        }
      ]

      command = [
        "--config.file=/etc/opspilot-monitoring/alertmanager.yml",
        "--storage.path=/alertmanager",
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
          awslogs-stream-prefix = "alertmanager"
        }
      }
    },
    {
      name      = "loki"
      image     = var.loki_image
      essential = true

      dependsOn = [
        {
          containerName = "config-init"
          condition     = "SUCCESS"
        }
      ]

      portMappings = [
        {
          containerPort = 3100
          protocol      = "tcp"
        }
      ]

      command = [
        "-config.file=/etc/opspilot-monitoring/loki.yml"
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
          awslogs-stream-prefix = "loki"
        }
      }
    },
    {
      name              = "tempo"
      image             = var.tempo_image
      essential         = true
      memoryReservation = 256

      dependsOn = [
        {
          containerName = "config-init"
          condition     = "SUCCESS"
        }
      ]

      portMappings = [
        {
          containerPort = 3200
          protocol      = "tcp"
        },
        {
          containerPort = 4317
          protocol      = "tcp"
        },
        {
          containerPort = 4318
          protocol      = "tcp"
        }
      ]

      command = [
        "-config.file=/etc/opspilot-monitoring/tempo.yml"
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
          awslogs-stream-prefix = "tempo"
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

  service_registries {
    registry_arn = aws_service_discovery_service.loki.arn
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
data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "loki" {
  bucket = lower("${var.name}-loki-${data.aws_caller_identity.current.account_id}")

  tags = {
    Name = "${var.name}-loki"
  }
}

resource "aws_s3_bucket_public_access_block" "loki" {
  bucket = aws_s3_bucket.loki.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "loki" {
  bucket = aws_s3_bucket.loki.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "loki" {
  bucket = aws_s3_bucket.loki.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_iam_role" "observability_task" {
  name               = "${var.name}-observability-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${var.name}-observability-task-role"
  }
}

data "aws_iam_policy_document" "loki_s3" {
  statement {
    sid = "ListLokiBucket"

    actions = [
      "s3:ListBucket",
    ]

    resources = [
      aws_s3_bucket.loki.arn,
    ]
  }

  statement {
    sid = "ManageLokiObjects"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]

    resources = [
      "${aws_s3_bucket.loki.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "loki_s3" {
  name   = "${var.name}-loki-s3"
  role   = aws_iam_role.observability_task.id
  policy = data.aws_iam_policy_document.loki_s3.json
}

resource "aws_vpc_security_group_ingress_rule" "loki_from_app" {
  security_group_id            = aws_security_group.observability.id
  referenced_security_group_id = var.app_security_group_id

  description = "Allow OpsPilot application tasks to send logs to Loki"

  from_port   = 3100
  to_port     = 3100
  ip_protocol = "tcp"
}

resource "aws_service_discovery_private_dns_namespace" "observability" {
  name        = "${var.name}.internal"
  description = "Private service discovery namespace for OpsPilot observability"
  vpc         = var.vpc_id
}

resource "aws_service_discovery_service" "loki" {
  name = "loki"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.observability.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }
}

resource "aws_s3_bucket" "tempo" {
  bucket = lower("${var.name}-tempo-${data.aws_caller_identity.current.account_id}")

  tags = {
    Name = "${var.name}-tempo"
  }
}

resource "aws_s3_bucket_public_access_block" "tempo" {
  bucket = aws_s3_bucket.tempo.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tempo" {
  bucket = aws_s3_bucket.tempo.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "tempo" {
  bucket = aws_s3_bucket.tempo.id

  versioning_configuration {
    status = "Enabled"
  }
}

data "aws_iam_policy_document" "tempo_s3" {
  statement {
    sid = "ReadTempoBucket"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]

    resources = [
      aws_s3_bucket.tempo.arn,
    ]
  }

  statement {
    sid = "ManageTempoObjects"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]

    resources = [
      "${aws_s3_bucket.tempo.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "tempo_s3" {
  name   = "${var.name}-tempo-s3"
  role   = aws_iam_role.observability_task.id
  policy = data.aws_iam_policy_document.tempo_s3.json
}

resource "aws_vpc_security_group_ingress_rule" "tempo_otlp_http_from_app" {
  security_group_id            = aws_security_group.observability.id
  referenced_security_group_id = var.app_security_group_id

  description = "Allow OpsPilot application tasks to export OTLP traces to Tempo"

  from_port   = 4318
  to_port     = 4318
  ip_protocol = "tcp"
}

resource "aws_sns_topic" "alerts" {
  name = "${var.name}-alerts"

  tags = {
    Name = "${var.name}-alerts"
  }
}

data "aws_iam_policy_document" "alertmanager_sns" {
  statement {
    sid = "PublishOpsPilotAlerts"

    actions = [
      "sns:Publish",
    ]

    resources = [
      aws_sns_topic.alerts.arn,
    ]
  }
}

resource "aws_iam_role_policy" "alertmanager_sns" {
  name   = "${var.name}-alertmanager-sns"
  role   = aws_iam_role.observability_task.id
  policy = data.aws_iam_policy_document.alertmanager_sns.json
}

resource "aws_prometheus_workspace" "metrics" {
  alias = "${var.name}-metrics"

  tags = {
    Name = "${var.name}-metrics"
  }
}

data "aws_iam_policy_document" "prometheus_remote_write" {
  statement {
    sid = "RemoteWriteMetrics"

    actions = [
      "aps:RemoteWrite",
    ]

    resources = [
      aws_prometheus_workspace.metrics.arn,
    ]
  }
}

resource "aws_iam_role_policy" "prometheus_remote_write" {
  name   = "${var.name}-prometheus-remote-write"
  role   = aws_iam_role.observability_task.id
  policy = data.aws_iam_policy_document.prometheus_remote_write.json
}
