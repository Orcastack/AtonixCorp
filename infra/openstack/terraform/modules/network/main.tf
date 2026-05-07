# -----------------------------------------------------------------------------
# Ledgora – OpenStack Network Module
# Provisions: network, subnets (main + backend), router, and floating-IP pool
# Every resource is tagged per the Ledgora traceability standard.
# -----------------------------------------------------------------------------

terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 1.54"
    }
  }
}

# ── Main tenant network ──────────────────────────────────────────────────────

resource "openstack_networking_network_v2" "main" {
  name           = "lgx-${var.env}-net-main"
  admin_state_up = true
  tags           = local.tags
}

resource "openstack_networking_subnet_v2" "main" {
  name            = "lgx-${var.env}-subnet-main"
  network_id      = openstack_networking_network_v2.main.id
  cidr            = var.main_cidr
  ip_version      = 4
  dns_nameservers = var.dns_nameservers
  tags            = local.tags
}

# ── Backend (service-to-service) network ─────────────────────────────────────

resource "openstack_networking_network_v2" "backend" {
  name           = "lgx-${var.env}-net-backend"
  admin_state_up = true
  tags           = local.tags
}

resource "openstack_networking_subnet_v2" "backend" {
  name            = "lgx-${var.env}-subnet-backend"
  network_id      = openstack_networking_network_v2.backend.id
  cidr            = var.backend_cidr
  ip_version      = 4
  dns_nameservers = var.dns_nameservers
  tags            = local.tags
}

# ── Router (external gateway) ────────────────────────────────────────────────

resource "openstack_networking_router_v2" "main" {
  name                = "lgx-${var.env}-router-main"
  admin_state_up      = true
  external_network_id = var.external_network_id
  tags                = local.tags
}

resource "openstack_networking_router_interface_v2" "main" {
  router_id = openstack_networking_router_v2.main.id
  subnet_id = openstack_networking_subnet_v2.main.id
}

resource "openstack_networking_router_interface_v2" "backend" {
  router_id = openstack_networking_router_v2.main.id
  subnet_id = openstack_networking_subnet_v2.backend.id
}

# ── Shared tags ───────────────────────────────────────────────────────────────

locals {
  tags = [
    "system=ledgora",
    "env=${var.env}",
    "service=shared",
    "change_id=${var.change_id}",
    "commit=${var.commit}",
  ]
}
