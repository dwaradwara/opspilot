locals {
  github_repository_parts = split("/", var.github_repository)

  github_subject = "repo:${local.github_repository_parts[0]}@${var.github_owner_id}/${local.github_repository_parts[1]}@${var.github_repository_id}:ref:refs/heads/${var.github_branch}"
}

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com",
  ]
}

data "aws_iam_policy_document" "github_assume_role" {
  statement {
    effect = "Allow"

    actions = [
      "sts:AssumeRoleWithWebIdentity",
    ]

    principals {
      type = "Federated"

      identifiers = [
        aws_iam_openid_connect_provider.github.arn,
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"

      values = [
        "sts.amazonaws.com",
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"

      values = [
        local.github_subject,
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:repository_owner_id"

      values = [
        var.github_owner_id,
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:repository_id"

      values = [
        var.github_repository_id,
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:ref"

      values = [
        "refs/heads/${var.github_branch}",
      ]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "${var.name}-github-actions"
  assume_role_policy = data.aws_iam_policy_document.github_assume_role.json

  max_session_duration = 3600

  tags = {
    Name = "${var.name}-github-actions"
  }
}

data "aws_iam_policy_document" "ecr_publish" {
  statement {
    sid = "ECRAuthentication"

    actions = [
      "ecr:GetAuthorizationToken",
    ]

    resources = ["*"]
  }

  statement {
    sid = "PublishToOpsPilotRepository"

    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]

    resources = [
      var.ecr_repository_arn,
    ]
  }
}

resource "aws_iam_role_policy" "ecr_publish" {
  name   = "${var.name}-ecr-publish"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.ecr_publish.json
}
data "aws_iam_policy_document" "ecs_deploy" {
  statement {
    sid = "ReadAndRegisterTaskDefinition"

    actions = [
      "ecs:DescribeTaskDefinition",
      "ecs:RegisterTaskDefinition",
    ]

    resources = ["*"]
  }

  statement {
    sid = "DeployToStagingService"

    actions = [
      "ecs:DescribeServices",
      "ecs:UpdateService",
    ]

    resources = [
      var.ecs_service_arn,
    ]
  }

  statement {
    sid = "PassECSTaskRoles"

    actions = [
      "iam:PassRole",
    ]

    resources = [
      var.ecs_task_execution_role_arn,
      var.ecs_task_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"

      values = [
        "ecs-tasks.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role_policy" "ecs_deploy" {
  name   = "${var.name}-ecs-deploy"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.ecs_deploy.json
}