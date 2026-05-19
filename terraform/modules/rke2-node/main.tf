terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.61"
    }
  }
}

resource "proxmox_virtual_environment_vm" "node" {
  name      = var.name
  node_name = var.proxmox_node
  vm_id     = var.vm_id
  tags      = concat(["rke2", var.role], var.extra_tags)

  clone {
    vm_id   = var.template_vm_id
    full    = true
    retries = 3
  }

  cpu {
    cores = var.cpu_cores
    type  = "host"
  }

  memory {
    dedicated = var.memory_mb
  }

  disk {
    datastore_id = var.datastore_id
    interface    = "virtio0"
    size         = var.disk_size
    discard      = "on"
    iothread     = true
  }

  network_device {
    bridge  = var.network_bridge
    model   = "virtio"
    vlan_id = var.vlan_id != null ? var.vlan_id : null
  }

  initialization {
    datastore_id = var.datastore_id

    ip_config {
      ipv4 {
        address = var.ip_address != "" ? "${var.ip_address}/${var.ip_prefix}" : "dhcp"
        gateway = var.ip_address != "" ? var.gateway : null
      }
    }

    dns {
      servers = var.dns_servers
    }

    user_account {
      username = "ubuntu"
      keys     = var.ssh_public_keys
    }

    # Passes RKE2 join config via cloud-init user-data
    user_data_file_id = proxmox_virtual_environment_file.cloud_init[0].id
  }

  agent {
    enabled = true
    timeout = "15m"
  }

  lifecycle {
    # Allow autoscaler to manage VMs outside Terraform
    ignore_changes = [tags]
  }
}

resource "proxmox_virtual_environment_file" "cloud_init" {
  count        = 1
  content_type = "snippets"
  datastore_id = var.snippets_datastore_id
  node_name    = var.proxmox_node

  source_raw {
    file_name = "${var.name}-cloud-init.yaml"
    data      = templatefile("${path.module}/cloud-init.yaml.tpl", {
      hostname          = var.name
      rke2_version      = var.rke2_version
      rke2_role         = var.role
      rke2_server_url   = var.rke2_server_url
      rke2_token        = var.rke2_token
      rke2_sans         = var.rke2_sans
      node_labels       = var.node_labels
      node_taints       = var.node_taints
    })
  }
}
