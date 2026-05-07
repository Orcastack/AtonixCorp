variable "env" {
  type        = string
  description = "Environment name: dev | test | stage | prod"

  validation {
    condition     = contains(["dev", "test", "stage", "prod"], var.env)
    error_message = "env must be one of: dev, test, stage, prod."
  }
}

variable "service" {
  type        = string
  description = "Ledgora service name (e.g. ledger, accounts, risk, reporting, bastion)."
}

variable "instance_count" {
  type        = number
  description = "Number of instances to provision for this service."
  default     = 1
}

variable "flavor_name" {
  type        = string
  description = "OpenStack flavor name (defined centrally; no ad-hoc UI selection)."
}

variable "image_name" {
  type        = string
  description = "Base OS image name. Pinned in tfvars; never selected interactively."
}

variable "network_id" {
  type        = string
  description = "ID of the OpenStack network to attach each instance to."
}

variable "security_group_names" {
  type        = list(string)
  description = "Security group names (not IDs) to associate with each instance."
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key material for the service keypair. Store the private key in Vault."
  sensitive   = true
}

variable "user_data" {
  type        = string
  description = "Cloud-init user-data script rendered by the calling env root."
  default     = ""
}

variable "assign_floating_ip" {
  type        = bool
  description = "Whether to allocate and associate a floating IP. Only for bastion/public services."
  default     = false
}

variable "floating_ip_pool" {
  type        = string
  description = "Name of the external floating-IP pool. Required when assign_floating_ip = true."
  default     = "public"
}

variable "change_id" {
  type        = string
  description = "Gerrit change ID injected by Jenkins."
}

variable "commit" {
  type        = string
  description = "Short Git commit SHA injected by Jenkins."
}
