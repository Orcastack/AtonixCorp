terraform {
  backend "swift" {
    auth_url    = "https://openstack.ledgora.internal:5000/v3"
    container   = "lgx-terraform-state"
    state_name  = "stage/terraform.tfstate"
    region_name = "RegionOne"
    application_credential_id     = ""
    application_credential_secret = ""
  }
}
