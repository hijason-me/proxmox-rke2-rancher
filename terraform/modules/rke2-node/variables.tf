variable "name" {
  description = "VM hostname"
  type        = string
}

variable "vm_id" {
  description = "Proxmox VM ID"
  type        = number
}

variable "proxmox_node" {
  description = "Proxmox host node"
  type        = string
}

variable "template_vm_id" {
  description = "Source template VM ID"
  type        = number
  default     = 9000
}

variable "role" {
  description = "RKE2 role: server or agent"
  type        = string
  validation {
    condition     = contains(["server", "agent"], var.role)
    error_message = "Role must be 'server' or 'agent'."
  }
}

variable "cpu_cores" {
  description = "Number of vCPU cores"
  type        = number
  default     = 4
}

variable "memory_mb" {
  description = "RAM in MB"
  type        = number
  default     = 8192
}

variable "disk_size" {
  description = "Disk size in GB"
  type        = number
  default     = 50
}

variable "datastore_id" {
  description = "Proxmox datastore for VM disk"
  type        = string
  default     = "local-lvm"
}

variable "snippets_datastore_id" {
  description = "Proxmox datastore that supports snippets (for cloud-init)"
  type        = string
  default     = "local"
}

variable "network_bridge" {
  description = "Proxmox network bridge"
  type        = string
  default     = "vmbr0"
}

variable "ip_address" {
  description = "Static IP address (empty = DHCP)"
  type        = string
  default     = ""
}

variable "ip_prefix" {
  description = "IP prefix length (e.g., 24)"
  type        = number
  default     = 24
}

variable "gateway" {
  description = "Default gateway IP"
  type        = string
  default     = ""
}

variable "dns_servers" {
  description = "DNS server IPs"
  type        = list(string)
  default     = ["1.1.1.1", "8.8.8.8"]
}

variable "ssh_public_keys" {
  description = "SSH public keys for cloud-init"
  type        = list(string)
}

variable "rke2_version" {
  description = "RKE2 version to install (e.g., v1.30.4+rke2r1)"
  type        = string
  default     = "v1.30.4+rke2r1"
}

variable "rke2_server_url" {
  description = "RKE2 server URL for agents to join"
  type        = string
  default     = ""
}

variable "rke2_token" {
  description = "RKE2 cluster join token"
  type        = string
  sensitive   = true
}

variable "rke2_sans" {
  description = "Additional SANs for RKE2 API server TLS cert"
  type        = list(string)
  default     = []
}

variable "node_labels" {
  description = "Kubernetes node labels"
  type        = map(string)
  default     = {}
}

variable "node_taints" {
  description = "Kubernetes node taints"
  type        = list(string)
  default     = []
}

variable "extra_tags" {
  description = "Additional Proxmox tags"
  type        = list(string)
  default     = []
}
