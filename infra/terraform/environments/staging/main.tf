data "aws_availability_zones" "available" {
  state = "available"
}

module "network" {
  source = "../../modules/network"

  name     = "opspilot-staging"
  vpc_cidr = "10.20.0.0/16"

  availability_zones = slice(
    data.aws_availability_zones.available.names,
    0,
    2
  )

  public_subnet_cidrs = [
    "10.20.10.0/24",
    "10.20.20.0/24",
  ]

  private_app_subnet_cidrs = [
    "10.20.30.0/24",
    "10.20.40.0/24",
  ]

  database_subnet_cidrs = [
    "10.20.50.0/24",
    "10.20.60.0/24",
  ]
}

module "security" {
  source = "../../modules/security"

  name   = "opspilot-staging"
  vpc_id = module.network.vpc_id
}

module "database" {
  source = "../../modules/database"

  name                = "opspilot-staging"
  database_subnet_ids = module.network.database_subnet_ids
  security_group_id   = module.security.database_security_group_id
}
module "cache" {
  source = "../../modules/cache"

  name              = "opspilot-staging"
  cache_subnet_ids  = module.network.private_app_subnet_ids
  security_group_id = module.security.redis_security_group_id
}
module "load_balancer" {
  source = "../../modules/load_balancer"

  name              = "opspilot-staging"
  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  security_group_id = module.security.alb_security_group_id
  target_port       = 8000
  health_check_path = "/health"
}
module "compute" {
  depends_on = [module.load_balancer]
  source     = "../../modules/compute"

  name              = "opspilot-staging"
  subnet_ids        = module.network.public_subnet_ids
  security_group_id = module.security.app_security_group_id
  container_image   = var.container_image
  target_group_arn  = module.load_balancer.target_group_arn

  database_host       = module.database.database_address
  database_port       = module.database.database_port
  database_name       = module.database.database_name
  database_user       = module.database.master_username
  database_secret_arn = module.database.master_user_secret_arn
  jwt_secret_arn      = module.secrets.jwt_secret_arn

  redis_host = module.cache.redis_primary_endpoint
  redis_port = module.cache.redis_port

  container_port   = 8000
  cpu              = 256
  memory           = 512
  desired_count    = 1
  assign_public_ip = true
}
module "secrets" {
  source = "../../modules/secrets"

  name = "opspilot-staging"
}
module "registry" {
  source = "../../modules/registry"

  name = "opspilot-staging"
}