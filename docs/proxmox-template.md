# Proxmox VM Template 準備

在執行 Terraform 之前，先在 Proxmox 上手動建立 cloud-init 模板（Terraform 也可以自動建，但第一次手動較直觀）。

## 方法 A：手動建立（推薦首次）

```bash
# 在 Proxmox 節點上執行（SSH 進去）

# 下載 Ubuntu 24.04 cloud image
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img \
     -O /tmp/ubuntu-24.04-cloud.img

# 建立 VM（ID 9000）
qm create 9000 \
  --name ubuntu-24.04-rke2-template \
  --memory 2048 \
  --net0 virtio,bridge=vmbr0 \
  --scsihw virtio-scsi-pci \
  --scsi0 local-lvm:0,import-from=/tmp/ubuntu-24.04-cloud.img \
  --ide2 local-lvm:cloudinit \
  --boot order=scsi0 \
  --serial0 socket \
  --vga serial0 \
  --agent enabled=1 \
  --ostype l26

# 調整磁碟大小到 30GB
qm resize 9000 scsi0 30G

# 轉換成 template
qm template 9000
```

## 方法 B：Terraform 自動建立

```bash
cd terraform
terraform -chdir=modules/proxmox-template init
terraform -chdir=modules/proxmox-template apply \
  -var="node_name=pve1" \
  -var='ssh_public_keys=["ssh-ed25519 AAAA..."]'
```

## 驗證模板

```bash
# 確認 template 存在
pvesh get /nodes/pve1/qemu/9000/config | grep template
# 應該看到 template: 1
```

## Proxmox API Token 建立

```bash
# 在 Proxmox 節點或 UI 建立
pveum user add terraform@pve
pveum aclmod / -user terraform@pve -role PVEVMAdmin
pveum aclmod /storage -user terraform@pve -role PVEDatastoreAdmin
pveum user token add terraform@pve terraform-token --privsep=0
# 複製輸出的 token secret
```
