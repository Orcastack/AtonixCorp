# Non-secret configuration for lgx-dev.
# Secrets (credentials, SSH key) are injected by Jenkins from Vault
# and must NEVER be committed here.

os_auth_url         = "https://openstack.atonixcorp.internal:5000/v3"
os_region           = "RegionOne"
external_network_id = "REPLACE_WITH_OPENSTACK_EXTERNAL_NETWORK_UUID"
floating_ip_pool    = "public"

main_cidr         = "10.10.0.0/24"
backend_cidr      = "10.10.1.0/24"
dns_nameservers   = ["8.8.8.8", "8.8.4.4"]
trusted_ssh_cidrs = ["10.0.0.0/8"]  # Corporate VPN CIDR; tighten as needed.

base_image_name = "Ubuntu-22.04-LTS"
bastion_flavor  = "m1.small"
api_flavor      = "m1.small"     # DEV can use smaller flavors
db_flavor       = "m1.medium"

ledger_volume_size_gb = 20
db_volume_size_gb     = 40
