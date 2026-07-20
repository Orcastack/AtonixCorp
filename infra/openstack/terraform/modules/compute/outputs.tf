output "instance_ids" {
  description = "List of Nova instance IDs in provisioning order."
  value       = openstack_compute_instance_v2.service[*].id
}

output "instance_names" {
  description = "Canonical AtonixCorp instance names (lgx-<env>-<service>-<n>)."
  value       = openstack_compute_instance_v2.service[*].name
}

output "instance_ips" {
  description = "Fixed IP addresses on the primary network interface."
  value = [
    for inst in openstack_compute_instance_v2.service :
    inst.network[0].fixed_ip_v4
  ]
}

output "floating_ips" {
  description = "Floating IPs, if assigned; empty list otherwise."
  value       = openstack_networking_floatingip_v2.service[*].address
}

output "keypair_name" {
  description = "Name of the provisioned Nova keypair."
  value       = openstack_compute_keypair_v2.service.name
}
