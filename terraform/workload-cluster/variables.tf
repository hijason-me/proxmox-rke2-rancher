variable "proxmox_url" { type = string }
variable "proxmox_token_id" { type = string }
variable "proxmox_token_secret" { type = string; sensitive = true }
variable "proxmox_insecure" { type = bool; default = false }
variable "proxmox_ssh_user" { type = string; default = "root" }
variable "proxmox_nodes" { type = list(string) }

variable "cluster_name" {
  description = "Logical cluster name (used in VM names, labels)"
  type        = string
  default     = "workload-1"
}

variable "template_vm_id" { type = number; default = 9000 }
variable "datastore_id" { type = string; default = "local-lvm" }
variable "snippets_datastore_id" { type = string; default = "local" }
variable "network_bridge" { type = string; default = "vmbr0" }

variable "vlan_id" {
  description = "VLAN tag ID (1–4094). null = untagged"
  type        = number
  default     = null
  validation {
    condition     = var.vlan_id == null || (var.vlan_id >= 1 && var.vlan_id <= 4094)
    error_message = "vlan_id must be between 1 and 4094, or null for untagged."
  }
}
variable "dns_servers" { type = list(string); default = ["1.1.1.1"] }
variable "ssh_public_keys" { type = list(string) }

variable "rke2_version" { type = string; default = "v1.30.4+rke2r1" }
variable "rke2_token" { type = string; sensitive = true }

variable "cluster_vip" {
  description = "kube-vip VIP for this workload cluster API"
  type        = string
}

variable "cp_ips" {
  description = "Static IPs for the 3 control plane nodes"
  type        = list(string)
  validation {
    condition     = length(var.cp_ips) == 3
    error_message = "Exactly 3 control plane IPs required."
  }
}

variable "extra_sans" { type = list(string); default = [] }
variable "ip_prefix" { type = number; default = 24 }
variable "gateway" { type = string }

variable "vm_id_offset" {
  description = "VM ID base for this cluster (e.g., 300 for cluster 1, 400 for cluster 2)"
  type        = number
  default     = 300
}

# Control plane specs
variable "control_plane_cpu" { type = number; default = 4 }
variable "control_plane_memory" { type = number; default = 8192 }
variable "control_plane_disk" { type = number; default = 50 }

# Worker specs — edit these and re-apply to trigger rolling node replacement
variable "worker_cpu" {
  description = "Worker node vCPU count"
  type        = number
  default     = 4
}

variable "worker_memory" {
  description = "Worker node RAM in MB"
  type        = number
  default     = 8192
}

variable "worker_disk" {
  description = "Worker node disk in GB"
  type        = number
  default     = 50
}

variable "initial_worker_count" {
  description = "Number of worker nodes Terraform manages (minimum baseline)"
  type        = number
  default     = 2
}

variable "worker_ips" {
  description = "Static IPs for initial workers (null = DHCP)"
  type        = list(string)
  default     = null
}

variable "worker_labels" {
  description = "Additional labels for worker nodes"
  type        = map(string)
  default     = {}
}
