variable "proxmox_url" {
  description = "Proxmox API URL"
  type        = string
}

variable "proxmox_token_id" {
  description = "Proxmox API token ID (user@realm!tokenname)"
  type        = string
}

variable "proxmox_token_secret" {
  description = "Proxmox API token secret"
  type        = string
  sensitive   = true
}

variable "proxmox_insecure" {
  description = "Skip TLS verification (dev only)"
  type        = bool
  default     = false
}

variable "proxmox_ssh_user" {
  description = "SSH user for Proxmox node access"
  type        = string
  default     = "root"
}

variable "proxmox_nodes" {
  description = "List of Proxmox cluster nodes to spread VMs across"
  type        = list(string)
}

variable "template_vm_id" {
  description = "Source template VM ID"
  type        = number
  default     = 9000
}

variable "datastore_id" {
  description = "Proxmox datastore for VM disks"
  type        = string
  default     = "local-lvm"
}

variable "snippets_datastore_id" {
  description = "Proxmox datastore that supports snippets"
  type        = string
  default     = "local"
}

variable "network_bridge" {
  type    = string
  default = "vmbr0"
}

variable "vlan_id" {
  description = "VLAN tag ID (1–4094). null = untagged"
  type        = number
  default     = null
  validation {
    condition     = var.vlan_id == null || (var.vlan_id >= 1 && var.vlan_id <= 4094)
    error_message = "vlan_id must be between 1 and 4094, or null for untagged."
  }
}

variable "dns_servers" {
  type    = list(string)
  default = ["1.1.1.1", "8.8.8.8"]
}

variable "ssh_public_keys" {
  description = "SSH public keys for all nodes"
  type        = list(string)
}

variable "rke2_version" {
  description = "RKE2 version (e.g., v1.30.4+rke2r1)"
  type        = string
  default     = "v1.30.4+rke2r1"
}

variable "rke2_token" {
  description = "RKE2 cluster join token (use a long random string)"
  type        = string
  sensitive   = true
}

# Management cluster network config
variable "mgmt_vip" {
  description = "Virtual IP for management cluster API (keepalived/kube-vip)"
  type        = string
}

variable "mgmt_cp_ips" {
  description = "Static IPs for the 3 management control plane nodes"
  type        = list(string)
  validation {
    condition     = length(var.mgmt_cp_ips) == 3
    error_message = "Exactly 3 control plane IPs required."
  }
}

variable "mgmt_extra_sans" {
  description = "Additional SANs for the management cluster API cert"
  type        = list(string)
  default     = []
}

variable "ip_prefix" {
  type    = number
  default = 24
}

variable "gateway" {
  type = string
}

# Node specs
variable "control_plane_cpu" {
  type    = number
  default = 4
}

variable "control_plane_memory" {
  description = "RAM in MB"
  type        = number
  default     = 8192
}

variable "control_plane_disk" {
  description = "Disk size in GB"
  type        = number
  default     = 50
}
