# -----------------------------------------------------------------------------
# AtonixCorp – DEV environment root
# OpenStack Project: lgx-dev
# Applied automatically by Jenkins when changes merge to main.
# Do NOT apply manually.
# -----------------------------------------------------------------------------

provider "openstack" {
  auth_url            = var.os_auth_url
  region              = var.os_region
  application_credential_id     = var.os_application_credential_id
  application_credential_secret = var.os_application_credential_secret
}

# ── Network layer ─────────────────────────────────────────────────────────────

module "network" {
  source = "../../modules/network"

  env                 = "dev"
  main_cidr           = var.main_cidr
  backend_cidr        = var.backend_cidr
  external_network_id = var.external_network_id
  dns_nameservers     = var.dns_nameservers
  change_id           = var.change_id
  commit              = var.commit
}

# ── Security layer ────────────────────────────────────────────────────────────

module "security" {
  source = "../../modules/security"

  env               = "dev"
  main_cidr         = var.main_cidr
  backend_cidr      = var.backend_cidr
  trusted_ssh_cidrs = var.trusted_ssh_cidrs
  change_id         = var.change_id
  commit            = var.commit
}

# ── Bastion host ──────────────────────────────────────────────────────────────

module "bastion" {
  source = "../../modules/compute"

  env                  = "dev"
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

# ── Ledger service ────────────────────────────────────────────────────────────

module "ledger" {
  source = "../../modules/compute"

  env                  = "dev"
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

  env            = "dev"
  service        = "ledger"
  volume_count   = 1
  volume_size_gb = var.ledger_volume_size_gb
  instance_ids   = module.ledger.instance_ids
  change_id      = var.change_id
  commit         = var.commit
}

# ── Accounts service ──────────────────────────────────────────────────────────

module "accounts" {
  source = "../../modules/compute"

  env                  = "dev"
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

# ── Database host ─────────────────────────────────────────────────────────────

module "db" {
  source = "../../modules/compute"

  env                  = "dev"
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

  env            = "dev"
  service        = "db"
  volume_count   = 1
  volume_size_gb = var.db_volume_size_gb
  instance_ids   = module.db.instance_ids
  change_id      = var.change_id
  commit         = var.commit
}
