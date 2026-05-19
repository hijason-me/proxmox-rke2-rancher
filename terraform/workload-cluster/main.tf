terraform {
  required_version = ">= 1.6"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.61"
    }
  }
}

provider "proxmox" {
  endpoint  = var.proxmox_url
  api_token = "${var.proxmox_token_id}=${var.proxmox_token_secret}"
  insecure  = var.proxmox_insecure
  ssh {
    agent            = false
    username         = var.proxmox_ssh_user
    private_key_file = var.proxmox_ssh_private_key_path
  }
}

# ── Workload cluster control plane (static) ────────────────────────────────

module "workload_server" {
  count  = 3
  source = "../modules/rke2-node"

  name           = "${var.cluster_name}-cp-${count.index + 1}"
  vm_id          = var.vm_id_offset + count.index
  proxmox_node   = var.proxmox_nodes[count.index % length(var.proxmox_nodes)]
  template_vm_id = var.template_vm_id
  role           = "server"

  cpu_cores  = var.control_plane_cpu
  memory_mb  = var.control_plane_memory
  disk_size  = var.control_plane_disk

  datastore_id          = var.datastore_id
  snippets_datastore_id = var.snippets_datastore_id
  network_bridge        = var.network_bridge
  vlan_id               = var.vlan_id
  dns_servers           = var.dns_servers
  ssh_public_keys       = var.ssh_public_keys

  rke2_version    = var.rke2_version
  rke2_server_url = count.index == 0 ? "" : "https://${var.cluster_vip}:9345"
  rke2_token      = var.rke2_token
  rke2_sans       = concat([var.cluster_vip], var.extra_sans)

  node_labels = {
    "node-role"      = "control-plane"
    "cluster"        = var.cluster_name
  }

  node_taints = [
    "node-role.kubernetes.io/control-plane=true:NoSchedule"
  ]

  ip_address = var.cp_ips[count.index]
  ip_prefix  = var.ip_prefix
  gateway    = var.gateway
}

# ── Initial worker pool (autoscaler manages additional nodes) ──────────────
# This creates the minimum baseline nodes.
# The autoscaler controller handles scale-up/down beyond this.

module "workload_agent_initial" {
  count  = var.initial_worker_count
  source = "../modules/rke2-node"

  name           = "${var.cluster_name}-worker-${count.index + 1}"
  vm_id          = var.vm_id_offset + 10 + count.index
  proxmox_node   = var.proxmox_nodes[count.index % length(var.proxmox_nodes)]
  template_vm_id = var.template_vm_id
  role           = "agent"

  cpu_cores  = var.worker_cpu
  memory_mb  = var.worker_memory
  disk_size  = var.worker_disk

  datastore_id          = var.datastore_id
  snippets_datastore_id = var.snippets_datastore_id
  network_bridge        = var.network_bridge
  vlan_id               = var.vlan_id
  dns_servers           = var.dns_servers
  ssh_public_keys       = var.ssh_public_keys

  rke2_version    = var.rke2_version
  rke2_server_url = "https://${var.cluster_vip}:9345"
  rke2_token      = var.rke2_token

  node_labels = merge(var.worker_labels, {
    "node-role" = "worker"
    "cluster"   = var.cluster_name
    "managed-by" = "terraform"
  })

  ip_address = var.worker_ips != null ? var.worker_ips[count.index] : ""
  ip_prefix  = var.ip_prefix
  gateway    = var.gateway
}
