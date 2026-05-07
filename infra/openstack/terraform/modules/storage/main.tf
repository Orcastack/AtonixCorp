# -----------------------------------------------------------------------------
# Ledgora – OpenStack Storage Module
# Provisions Cinder volumes for a named Ledgora service.
# Naming convention: lgx-<env>-<service>-data-<zero-padded-index>
# Volume snapshots are managed via a separate scheduled Jenkins job.
# -----------------------------------------------------------------------------

terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 1.54"
    }
  }
}

# ── Data volumes ─────────────────────────────────────────────────────────────

resource "openstack_blockstorage_volume_v3" "data" {
  count = var.volume_count

  name        = format("lgx-%s-%s-data-%02d", var.env, var.service, count.index + 1)
  size        = var.volume_size_gb
  volume_type = var.volume_type
  description = "Ledgora ${var.service} data volume – ${var.env}"

  metadata = {
    system    = "ledgora"
    env       = var.env
    service   = var.service
    change_id = var.change_id
    commit    = var.commit
  }
}

# ── Volume attachments ────────────────────────────────────────────────────────
# Attach each volume to the corresponding instance if instance_ids is provided.

resource "openstack_compute_volume_attach_v2" "data" {
  count = length(var.instance_ids) > 0 ? var.volume_count : 0

  instance_id = var.instance_ids[count.index]
  volume_id   = openstack_blockstorage_volume_v3.data[count.index].id
}
