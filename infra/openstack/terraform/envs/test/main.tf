# -----------------------------------------------------------------------------
# Ledgora – TEST environment root
# OpenStack Project: lgx-test
# Applied via Jenkins promotion job after successful DEV verification.
# TEST mirrors the production topology to ensure meaningful integration tests.
# -----------------------------------------------------------------------------

provider "openstack" {
  auth_url            = var.os_auth_url
  region              = var.os_region
  application_credential_id     = var.os_application_credential_id
  application_credential_secret = var.os_application_credential_secret
}

module "network" {
  source = "../../modules/network"

  env                 = "test"
  main_cidr           = var.main_cidr
  backend_cidr        = var.backend_cidr
  external_network_id = var.external_network_id
  dns_nameservers     = var.dns_nameservers
  change_id           = var.change_id
  commit              = var.commit
}

module "security" {
  source = "../../modules/security"

  env               = "test"
  main_cidr         = var.main_cidr
  backend_cidr      = var.backend_cidr
  trusted_ssh_cidrs = var.trusted_ssh_cidrs
  change_id         = var.change_id
  commit            = var.commit
}

module "bastion" {
  source = "../../modules/compute"

  env                  = "test"
  service              = "bastion"
  instance_count       = 1
  flavor_name          = var.bastion_flavor
  image_name           = var.base_image_name
  network_id           = module.network.main_network_id
  security_group_names = [module.security.bastion_secgroup_id]
  ssh_public_key       = var.ssh_public_key
  assign_floating_ip   = true
  floating_ip_pool     = var.floating_ip_pool
  change_id            = var.change_id
  commit               = var.commit
}

module "ledger" {
  source = "../../modules/compute"

  env                  = "test"
  service              = "ledger"
  instance_count       = 1
  flavor_name          = var.api_flavor
  image_name           = var.base_image_name
  network_id           = module.network.backend_network_id
  security_group_names = [module.security.api_secgroup_id]
  ssh_public_key       = var.ssh_public_key
  change_id            = var.change_id
  commit               = var.commit
}

module "ledger_storage" {
  source = "../../modules/storage"

  env            = "test"
  service        = "ledger"
  volume_count   = 1
  volume_size_gb = var.ledger_volume_size_gb
  instance_ids   = module.ledger.instance_ids
  change_id      = var.change_id
  commit         = var.commit
}

module "accounts" {
  source = "../../modules/compute"

  env                  = "test"
  service              = "accounts"
  instance_count       = 1
  flavor_name          = var.api_flavor
  image_name           = var.base_image_name
  network_id           = module.network.backend_network_id
  security_group_names = [module.security.api_secgroup_id]
  ssh_public_key       = var.ssh_public_key
  change_id            = var.change_id
  commit               = var.commit
}

module "db" {
  source = "../../modules/compute"

  env                  = "test"
  service              = "db"
  instance_count       = 1
  flavor_name          = var.db_flavor
  image_name           = var.base_image_name
  network_id           = module.network.backend_network_id
  security_group_names = [module.security.db_secgroup_id]
  ssh_public_key       = var.ssh_public_key
  change_id            = var.change_id
  commit               = var.commit
}

module "db_storage" {
  source = "../../modules/storage"

  env            = "test"
  service        = "db"
  volume_count   = 1
  volume_size_gb = var.db_volume_size_gb
  instance_ids   = module.db.instance_ids
  change_id      = var.change_id
  commit         = var.commit
}
