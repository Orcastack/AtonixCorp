# -----------------------------------------------------------------------------
# Ledgora – OpenStack Security Module
# Provisions security groups for API, DB, bastion, and monitoring tiers.
# Default posture: deny-all; only explicitly required ports are opened.
# -----------------------------------------------------------------------------

terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 1.54"
    }
  }
}

# ── API security group ────────────────────────────────────────────────────────

resource "openstack_networking_secgroup_v2" "api" {
  name        = "lgx-${var.env}-sg-api"
  description = "Ledgora API tier – HTTPS ingress only"
  tags        = local.tags
}

# Allow HTTPS from anywhere (load-balancer or public)
resource "openstack_networking_secgroup_rule_v2" "api_https_ingress" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 443
  port_range_max    = 443
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.api.id
}

# Allow HTTP only for health-checks from internal CIDR
resource "openstack_networking_secgroup_rule_v2" "api_http_internal" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  remote_ip_prefix  = var.main_cidr
  security_group_id = openstack_networking_secgroup_v2.api.id
}

# Allow Django/Gunicorn from backend subnet
resource "openstack_networking_secgroup_rule_v2" "api_app_port" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 8000
  port_range_max    = 8000
  remote_ip_prefix  = var.backend_cidr
  security_group_id = openstack_networking_secgroup_v2.api.id
}

# ── Database security group ───────────────────────────────────────────────────

resource "openstack_networking_secgroup_v2" "db" {
  name        = "lgx-${var.env}-sg-db"
  description = "Ledgora database tier – backend subnet ingress only"
  tags        = local.tags
}

resource "openstack_networking_secgroup_rule_v2" "db_postgres" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 5432
  port_range_max    = 5432
  remote_ip_prefix  = var.backend_cidr
  security_group_id = openstack_networking_secgroup_v2.db.id
}

# ── Bastion security group ────────────────────────────────────────────────────

resource "openstack_networking_secgroup_v2" "bastion" {
  name        = "lgx-${var.env}-sg-bastion"
  description = "Ledgora bastion host – SSH from trusted CIDRs only"
  tags        = local.tags
}

resource "openstack_networking_secgroup_rule_v2" "bastion_ssh" {
  for_each = toset(var.trusted_ssh_cidrs)

  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = each.value
  security_group_id = openstack_networking_secgroup_v2.bastion.id
}

# ── Monitoring security group ─────────────────────────────────────────────────

resource "openstack_networking_secgroup_v2" "monitoring" {
  name        = "lgx-${var.env}-sg-monitoring"
  description = "Ledgora monitoring – Prometheus scrape from backend subnet"
  tags        = local.tags
}

resource "openstack_networking_secgroup_rule_v2" "monitoring_prometheus" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 9090
  port_range_max    = 9100
  remote_ip_prefix  = var.backend_cidr
  security_group_id = openstack_networking_secgroup_v2.monitoring.id
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
