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
  description = "Ledgora service name the volumes belong to."
}

variable "volume_count" {
  type        = number
  description = "Number of volumes to provision (must match instance_count if attaching)."
  default     = 1
}

variable "volume_size_gb" {
  type        = number
  description = "Size of each volume in GiB."
}

variable "volume_type" {
  type        = string
  description = "Cinder volume type (e.g. ssd, hdd). Match what is available in your OpenStack."
  default     = "ssd"
}

variable "instance_ids" {
  type        = list(string)
  description = "List of Nova instance IDs to attach volumes to. Leave empty to skip attachment."
  default     = []
}

variable "change_id" {
  type        = string
  description = "Gerrit change ID injected by Jenkins."
}

variable "commit" {
  type        = string
  description = "Short Git commit SHA injected by Jenkins."
}
