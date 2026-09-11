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