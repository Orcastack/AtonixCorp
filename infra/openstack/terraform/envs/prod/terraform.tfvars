os_auth_url         = "https://openstack.ledgora.internal:5000/v3"
os_region           = "RegionOne"
external_network_id = "REPLACE_WITH_OPENSTACK_EXTERNAL_NETWORK_UUID"
floating_ip_pool    = "public"

main_cidr         = "10.40.0.0/24"
backend_cidr      = "10.40.1.0/24"
dns_nameservers   = ["8.8.8.8", "8.8.4.4"]
trusted_ssh_cidrs = ["10.0.0.0/8"]

base_image_name           = "Ubuntu-22.04-LTS"
bastion_flavor            = "m1.small"
api_flavor                = "m1.xlarge"
db_flavor                 = "m1.xlarge"
ledger_instance_count     = 3
accounts_instance_count   = 3
risk_instance_count       = 2
reporting_instance_count  = 2
db_instance_count         = 2
ledger_volume_size_gb     = 200
db_volume_size_gb         = 500
