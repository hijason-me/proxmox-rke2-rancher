# Architecture Deep Dive

## 兩層叢集設計

### Management Cluster（管理叢集）
- **用途**：只跑平台基礎設施，不跑業務應用
- **節點規格**：3× RKE2 server，固定不自動擴縮
- **上面跑什麼**：
  - Rancher（K8s 管理 UI）
  - ArgoCD（GitOps）
  - Proxmox Autoscaler Controller（自動擴縮控制器）
  - cert-manager
  - Ingress Controller（nginx）
- **HA 設計**：3 節點 embedded etcd，kube-vip 提供 API VIP

### Workload Cluster（工作叢集）
- **用途**：跑業務應用（例如 TWStock）
- **Control plane**：3× RKE2 server，靜態固定
- **Worker nodes**：2–N× RKE2 agent，由 Autoscaler 控制
- **管理方式**：由 Management Cluster 上的 Rancher 管理

## 網路架構

```
Proxmox Host(s)
  └── vmbr0 (VM bridge)
        ├── Management VIP: 192.168.1.100   ← API / Rancher
        ├── mgmt-cp-1:      192.168.1.101
        ├── mgmt-cp-2:      192.168.1.102
        ├── mgmt-cp-3:      192.168.1.103
        │
        ├── Workload VIP:   192.168.1.110   ← Workload API
        ├── wl-cp-1:        192.168.1.111
        ├── wl-cp-2:        192.168.1.112
        ├── wl-cp-3:        192.168.1.113
        ├── wl-worker-1:    192.168.1.121   ← Terraform managed
        ├── wl-worker-2:    192.168.1.122   ← Terraform managed
        └── wl-auto-N:      DHCP            ← Autoscaler managed
```

## VIP (kube-vip)

kube-vip 以 DaemonSet 執行在 control plane 節點上，使用 ARP 廣播。
- 同一時間只有一個節點持有 VIP（leader election）
- 某個 cp 節點掛掉時，VIP 在幾秒內飄移到另一個健康節點
- 不需要外部 LB，純軟體實現

## 自動擴縮完整流程

```
┌─────────────────────────────────────────────────────┐
│                  Autoscaler Controller               │
│                  (每 30 秒執行一次)                   │
└─────────────────────────┬───────────────────────────┘
                          │
         ┌────────────────┼─────────────────┐
         │                │                 │
    metrics-server    K8s API           Proxmox API
    (CPU/mem)      (pending pods,      (clone/delete
                    node status)          VMs)
         │                │
         └────────────────┘
                  │
    ┌─────────────▼──────────────┐
    │    Scale Up 條件（任一）     │
    │  • Pending pods > 2 分鐘   │
    │  • 平均 CPU > 80% 持續 5分  │
    │  • 平均 MEM > 85% 持續 5分  │
    └─────────────┬──────────────┘
                  │ 觸發
    ┌─────────────▼──────────────────────────────────┐
    │  Scale Up 流程                                  │
    │  1. 上傳 cloud-init snippet 到 Proxmox          │
    │  2. Clone VM template → 新 VM                  │
    │  3. 設定 CPU/RAM、掛載 cloud-init              │
    │  4. 開機                                        │
    │  5. cloud-init 自動安裝 RKE2 agent、加入叢集   │
    │  6. 約 3-5 分鐘後 node 出現在 kubectl get nodes │
    └────────────────────────────────────────────────┘

    ┌─────────────▼──────────────┐
    │    Scale Down 條件（全部）   │
    │  • 平均 CPU < 30% 持續 10分 │
    │  • 平均 MEM < 40% 持續 10分 │
    │  • 現有 nodes > min_nodes  │
    └─────────────┬──────────────┘
                  │ 觸發
    ┌─────────────▼──────────────────────────────────┐
    │  Scale Down 流程                               │
    │  1. 找出使用率最低的 worker node               │
    │  2. kubectl cordon → drain（驅逐 pods）        │
    │  3. 等待 30 秒（pods 終止 grace period）       │
    │  4. kubectl delete node                         │
    │  5. 透過 Proxmox API 關閉並刪除 VM             │
    └────────────────────────────────────────────────┘
```

## K8s 版本升級流程

```
1. 確認目標版本：https://github.com/rancher/rke2/releases
2. 觸發 GitHub Actions: upgrade-k8s workflow
   - 輸入 rke2_version (e.g. v1.31.0+rke2r1)
   - 先選 dry_run=true 確認無誤
3. 升級順序（Ansible 控制）：
   a. 第一個 cp node（先停、升、啟、等 Ready、Uncordon）
   b. 第二個 cp node（同上）
   c. 第三個 cp node（同上）
   d. Worker nodes（25% 批次滾動升級）
4. 整個過程叢集持續服務，無停機
```

## Node Spec 變更流程

```
1. 修改 terraform/workload-cluster/terraform.tfvars
   worker_cpu    = 8   # 由 4 改為 8
   worker_memory = 16384  # 由 8192 改為 16384
2. 開 PR → GitHub Actions 自動跑 Terraform plan
3. PR 描述中會顯示計算出的規格差異
4. Merge → 自動觸發 change-node-spec workflow
5. 逐一替換 worker node（drain → 刪 VM → Terraform 建新 VM）
6. 新 VM 規格為新設定，自動加入叢集
7. 全部替換完成後，叢集所有 worker 為新規格
```
