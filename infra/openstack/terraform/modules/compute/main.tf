# -----------------------------------------------------------------------------
# Ledgora – OpenStack Compute Module
# Provisions Nova instances for a named Ledgora service.
# Naming convention: lgx-<env>-<service>-<zero-padded-index>
# Every instance carries the full Ledgora traceability tag set.
# -----------------------------------------------------------------------------

terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 1.54"
    }
  }
}

# ── SSH key-pair (one per environment) ───────────────────────────────────────

resource "openstack_compute_keypair_v2" "service" {
  name       = "lgx-${var.env}-${var.service}-keypair"
  public_key = var.ssh_public_key
}

# ── Instances ─────────────────────────────────────────────────────────────────
# count-based so the module can scale from 1 → N without changing call sites.

resource "openstack_compute_instance_v2" "service" {
  count = var.instance_count

  name            = format("lgx-%s-%s-%02d", var.env, var.service, count.index + 1)
  flavor_name     = var.flavor_name
  image_name      = var.image_name
  key_pair        = openstack_compute_keypair_v2.service.name
  security_groups = var.security_group_names

  network {
    uuid = var.network_id
  }

  user_data = var.user_data

  # Ledgora mandatory metadata tags
  metadata = {
    system    = "ledgora"
    env       = var.env
    service   = var.service
    change_id = var.change_id
    commit    = var.commit
  }

  lifecycle {
    # Prevent accidental recreation of production instances; use a targeted
    # replace when intentional upgrades are required.
    ignore_changes = [image_name]
  }
}

# ── Floating IPs (optional – only for bastion and public-facing services) ────

resource "openstack_networking_floatingip_v2" "service" {
  count = var.assign_floating_ip ? var.instance_count : 0
  pool  = var.floating_ip_pool
}

resource "openstack_compute_floatingip_associate_v2" "service" {
  count = var.assign_floating_ip ? var.instance_count : 0

  floating_ip = openstack_networking_floatingip_v2.service[count.index].address
  instance_id = openstack_compute_instance_v2.service[count.index].id
}
