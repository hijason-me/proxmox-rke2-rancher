variable "node_name" {
  description = "Proxmox node to create template on"
  type        = string
}

variable "template_name" {
  description = "Name for the VM template"
  type        = string
  default     = "ubuntu-24.04-rke2-template"
}

variable "template_vm_id" {
  description = "VM ID for the template (9000-9999 range recommended)"
  type        = number
  default     = 9000
}

variable "datastore_id" {
  description = "Proxmox datastore for disk and image storage"
  type        = string
  default     = "local-lvm"
}

variable "disk_size" {
  description = "Template disk size in GB"
  type        = number
  default     = 30
}

variable "network_bridge" {
  description = "Proxmox network bridge"
  type        = string
  default     = "vmbr0"
}

variable "ssh_public_keys" {
  description = "SSH public keys for cloud-init"
  type        = list(string)
}
