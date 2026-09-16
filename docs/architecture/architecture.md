# OpsPilot Architecture

OpsPilot is a production-support and reliability engineering platform operated in an AWS staging environment.

The architecture is designed to demonstrate application delivery, dependency resilience, observability, incident response, and controlled failure testing.

## System Architecture

```mermaid
flowchart TB

    USER[Client / API Consumer]

    subgraph CICD["CI/CD"]
        GH[GitHub Actions]
        OIDC[AWS OIDC / IAM Role]
        ECR[Amazon ECR]
        MIG[Alembic Migration Task]
    end

    subgraph AWS["AWS Staging Environment"]

        ALB[Application Load Balancer]

        subgraph ECS["Amazon ECS Fargate"]
            API[OpsPilot FastAPI API]
            WORKER[Outbox Worker]
        end

        RDS[(Amazon RDS PostgreSQL)]
        REDIS[(Amazon ElastiCache Redis)]
        SECRETS[AWS Secrets Manager]

        subgraph OBS["Observability"]
            PROM[Prometheus]
            AMP[Amazon Managed Prometheus]
            GRAFANA[Grafana]
            LOKI[Loki]
            TEMPO[Tempo]
            BLACKBOX[Blackbox Exporter]
            ALERT[Alertmanager]
            SNS[Amazon SNS]
        end
    end

    USER --> ALB
    ALB --> API

    API --> RDS
    API --> REDIS
    API --> SECRETS

    RDS --> WORKER
    WORKER --> REDIS
    WORKER --> SECRETS

    GH --> OIDC
    OIDC --> ECR
    ECR --> MIG
    MIG --> API
    MIG --> WORKER

    API -->|Metrics| PROM
    WORKER -->|Metrics| PROM
    PROM --> AMP
    PROM --> GRAFANA

    API -->|Structured Logs via FireLens| LOKI
    WORKER -->|Structured Logs via FireLens| LOKI
    LOKI --> GRAFANA

    API -->|OpenTelemetry Traces| TEMPO
    TEMPO --> GRAFANA

    BLACKBOX -->|Synthetic /health Probe| ALB

    PROM -->|Alert Rules| ALERT
    ALERT --> SNS