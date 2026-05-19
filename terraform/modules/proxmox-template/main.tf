terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.61"
    }
  }
}

# Downloads Ubuntu 24.04 cloud image and creates a VM template
resource "proxmox_virtual_environment_download_file" "ubuntu_cloud_image" {
  content_type = "iso"
  datastore_id = var.datastore_id
  node_name    = var.node_name
  url          = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
  file_name    = "ubuntu-24.04-cloud.img"
  overwrite    = false
}

resource "proxmox_virtual_environment_vm" "template" {
  name      = var.template_name
  node_name = var.node_name
  vm_id     = var.template_vm_id
  template  = true
  tags      = ["rke2", "template", "ubuntu-24.04"]

  cpu {
    cores = 2
    type  = "host"
  }

  memory {
    dedicated = 2048
  }

  disk {
    datastore_id = var.datastore_id
    file_id      = proxmox_virtual_environment_download_file.ubuntu_cloud_image.id
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
        address = "dhcp"
      }
    }

    user_account {
      username = "ubuntu"
      keys     = var.ssh_public_keys
    }
  }

  serial_device {}

  operating_system {
    type = "l26"
  }

  agent {
    enabled = true
  }
}
