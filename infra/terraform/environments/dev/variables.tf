variable "aws_region" {
	type = string
}

variable "name_prefix" {
	type    = string
	default = "ledgora-dev"
}

variable "availability_zones" {
	type = list(string)
}

variable "vpc_cidr" {
	type    = string
	default = "10.10.0.0/16"
}

variable "public_subnet_cidrs" {
	type    = list(string)
	default = ["10.10.0.0/24", "10.10.1.0/24"]
}

variable "private_subnet_cidrs" {
	type    = list(string)
	default = ["10.10.10.0/24", "10.10.11.0/24"]
}

variable "kubernetes_version" {
	type    = string
	default = "1.30"
}

variable "node_instance_types" {
	type    = list(string)
	default = ["t3.medium"]
}

variable "node_desired_size" {
	type    = number
	default = 2
}

variable "node_min_size" {
	type    = number
	default = 1
}

variable "node_max_size" {
	type    = number
	default = 4
}

variable "db_name" {
	type    = string
	default = "ledgora"
}

variable "db_username" {
	type = string
}

variable "db_password" {
	type      = string
	sensitive = true
}

variable "db_instance_class" {
	type    = string
	default = "db.t4g.medium"
}

variable "db_allocated_storage" {
	type    = number
	default = 50
}

variable "artifact_bucket_name" {
	type = string
}

variable "secret_arns" {
	type = list(string)
}

variable "bitbucket_oidc_provider_arn" {
	type = string
}

variable "bitbucket_oidc_subject_claim" {
	type = string
}

variable "bitbucket_oidc_audience_claim" {
	type = string
}

variable "bitbucket_oidc_audience" {
	type = string
}

variable "bitbucket_oidc_subjects" {
	type = list(string)
}

variable "ecr_repository_arns" {
	type = list(string)
}

variable "state_bucket_arn" {
	type = string
}

variable "state_lock_table_arn" {
	type = string
}