provider "aws" {
  region = var.aws_region
}

locals {
  common_tags = {
    Application = "AtonixCorp"
    Environment = "staging"
    ManagedBy   = "Terraform"
  }
}

module "networking" {
  source               = "../../modules/networking"
  name_prefix          = var.name_prefix
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  tags                 = local.common_tags
}

module "load_balancer" {
  source      = "../../modules/load-balancer"
  name_prefix = var.name_prefix
  vpc_id      = module.networking.vpc_id
  tags        = local.common_tags
}

module "kubernetes_cluster" {
  source             = "../../modules/kubernetes-cluster"
  cluster_name       = var.name_prefix
  kubernetes_version = var.kubernetes_version
  subnet_ids         = module.networking.private_subnet_ids
  instance_types     = var.node_instance_types
  desired_size       = var.node_desired_size
  min_size           = var.node_min_size
  max_size           = var.node_max_size
  tags               = local.common_tags
}

module "database" {
  source                    = "../../modules/database"
  name_prefix               = var.name_prefix
  subnet_ids                = module.networking.private_subnet_ids
  cluster_security_group_id = module.kubernetes_cluster.cluster_security_group_id
  db_name                   = var.db_name
  username                  = var.db_username
  password                  = var.db_password
  instance_class            = var.db_instance_class
  allocated_storage         = var.db_allocated_storage
  tags                      = local.common_tags
}

module "object_storage" {
  source      = "../../modules/object-storage"
  bucket_name = var.artifact_bucket_name
  tags        = local.common_tags
}

module "observability" {
  source      = "../../modules/observability-logging"
  name_prefix = var.name_prefix
  tags        = local.common_tags
}

module "secrets_management" {
  source      = "../../modules/secrets-management"
  name_prefix = var.name_prefix
  secret_arns = var.secret_arns
}

module "identity_access" {
  source                      = "../../modules/identity-access"
  name_prefix                 = var.name_prefix
  bitbucket_oidc_provider_arn = var.bitbucket_oidc_provider_arn
  oidc_subject_claim          = var.bitbucket_oidc_subject_claim
  oidc_audience_claim         = var.bitbucket_oidc_audience_claim
  oidc_audience               = var.bitbucket_oidc_audience
  oidc_subjects               = var.bitbucket_oidc_subjects
  ecr_repository_arns         = var.ecr_repository_arns
  state_bucket_arn            = var.state_bucket_arn
  state_lock_table_arn        = var.state_lock_table_arn
  additional_policy_arns      = [module.secrets_management.policy_arn]
  tags                        = local.common_tags
}