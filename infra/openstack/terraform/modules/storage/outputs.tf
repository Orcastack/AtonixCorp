output "volume_ids" {
  description = "List of Cinder volume IDs in provisioning order."
  value       = openstack_blockstorage_volume_v3.data[*].id
}

output "volume_names" {
  description = "Canonical AtonixCorp volume names."
  value       = openstack_blockstorage_volume_v3.data[*].name
}
