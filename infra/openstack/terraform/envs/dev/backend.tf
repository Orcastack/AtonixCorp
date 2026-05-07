# Remote state backed by Swift (OpenStack Object Storage).
# The container and state key are unique per environment.
terraform {
  backend "swift" {
    auth_url            = "https://openstack.ledgora.internal:5000/v3"
    container           = "lgx-terraform-state"
    state_name          = "dev/terraform.tfstate"
    region_name         = "RegionOne"
    application_credential_id     = ""  # Supplied via env var OS_APPLICATION_CREDENTIAL_ID
    application_credential_secret = ""  # Supplied via env var OS_APPLICATION_CREDENTIAL_SECRET
  }
}
