terraform {
  required_version = ">= 1.6"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.61"
    }
  }

  # Recommended: use remote state so GitHub Actions can access it
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "proxmox-rke2/management/terraform.tfstate"
  #   region = "auto"
  # }
}

provider "proxmox" {
  endpoint  = var.proxmox_url
  api_token = "${var.proxmox_token_id}=${var.proxmox_token_secret}"
  insecure  = var.proxmox_insecure
  ssh {
    agent    = true
    username = var.proxmox_ssh_user
  }
}

# ── Control plane nodes (static, HA) ───────────────────────────────────────

module "mgmt_server" {
  count  = 3
  source = "../modules/rke2-node"

  name           = "mgmt-cp-${count.index + 1}"
  vm_id          = 200 + count.index
  proxmox_node   = var.proxmox_nodes[count.index % length(var.proxmox_nodes)]
  template_vm_id = var.template_vm_id
  role           = "server"

  cpu_cores  = var.control_plane_cpu
  memory_mb  = var.control_plane_memory
  disk_size  = var.control_plane_disk

  datastore_id          = var.datastore_id
  snippets_datastore_id = var.snippets_datastore_id
  network_bridge        = var.network_bridge
  dns_servers           = var.dns_servers
  ssh_public_keys       = var.ssh_public_keys

  # First node bootstraps, others join it
  rke2_version    = var.rke2_version
  rke2_server_url = count.index == 0 ? "" : "https://${var.mgmt_vip}:9345"
  rke2_token      = var.rke2_token
  rke2_sans       = concat([var.mgmt_vip], var.mgmt_extra_sans)

  node_labels = {
    "node-role" = "management"
  }

  node_taints = [
    "CriticalAddonsOnly=true:NoSchedule"
  ]

  ip_address = var.mgmt_cp_ips[count.index]
  ip_prefix  = var.ip_prefix
  gateway    = var.gateway
}
