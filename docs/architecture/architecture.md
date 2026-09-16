# OpsPilot Architecture

OpsPilot is a production-support and reliability engineering platform operated in an AWS staging environment.

The architecture is designed to demonstrate application delivery, dependency resilience, observability, incident response, and controlled failure testing.

## System Architecture

```mermaid
flowchart LR

    CLIENT[Client / API Consumer]

    subgraph DELIVERY["CI/CD"]
        GH[GitHub Actions]
        OIDC[AWS OIDC / IAM]
        ECR[Amazon ECR]
        MIG[Alembic Migration]
        GH --> OIDC --> ECR --> MIG
    end

    subgraph APP["AWS Staging - Application"]
        ALB[Application Load Balancer]

        API[ECS Fargate API]
        WORKER[ECS Fargate Outbox Worker]

        RDS[(Amazon RDS PostgreSQL)]
        REDIS[(Amazon ElastiCache Redis)]
        SECRETS[AWS Secrets Manager]

        ALB --> API

        API --> RDS
        API --> REDIS
        API -. secrets .-> SECRETS

        RDS --> WORKER
        WORKER --> REDIS
        WORKER -. secrets .-> SECRETS
    end

    subgraph OBS["Observability"]
        PROM[Prometheus]
        AMP[Amazon Managed Prometheus]
        GRAFANA[Grafana]
        LOKI[Loki]
        TEMPO[Tempo]
        BLACKBOX[Blackbox Exporter]
        ALERT[Alertmanager]
        SNS[Amazon SNS]

        PROM --> AMP
        PROM --> GRAFANA
        LOKI --> GRAFANA
        TEMPO --> GRAFANA
        PROM --> ALERT --> SNS
    end

    CLIENT --> ALB

    MIG --> API
    MIG --> WORKER

    API -. metrics .-> PROM
    WORKER -. metrics .-> PROM

    API -. logs .-> LOKI
    WORKER -. logs .-> LOKI

    API -. traces .-> TEMPO

    BLACKBOX -. health probe .-> ALB
```