# proxmox-rke2-rancher

GKE-like Kubernetes platform on Proxmox VE — RKE2 + Rancher with automatic node scaling, GitOps-driven upgrades, and minimal manual intervention.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub                                  │
│  proxmox-rke2-rancher repo  ←──→  GitHub Actions Workflows     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ GitOps triggers
          ┌────────────────┼─────────────────┐
          │                │                 │
     Terraform          Ansible           Helm/Rancher API
     (VM lifecycle)   (OS + RKE2)       (cluster config)
          │                │                 │
          └────────────────┼─────────────────┘
                           │
                ┌──────────▼──────────┐
                │     Proxmox VE      │
                │                     │
                │  ┌───────────────┐  │
                │  │  Management   │  │
                │  │   Cluster     │  │
                │  │  (RKE2 x3)   │  │
                │  │               │  │
                │  │  • Rancher    │  │
                │  │  • ArgoCD     │  │
                │  │  • Autoscaler │  │
                │  └───────┬───────┘  │
                │          │          │
                │  ┌───────▼───────┐  │
                │  │   Workload    │  │
                │  │   Cluster(s)  │  │
                │  │               │  │
                │  │  CP: 3 nodes  │  │
                │  │  Workers: N   │  │
                │  │  (auto scale) │  │
                │  └───────────────┘  │
                └─────────────────────┘
```

## Components

| Layer | Tool | Purpose |
|---|---|---|
| Hypervisor | Proxmox VE | VM host, API for provisioning |
| Kubernetes | RKE2 | Production-grade K8s distro |
| Management UI | Rancher | Cluster visibility, upgrades, node pools |
| Infrastructure | Terraform | VM template & lifecycle management |
| Configuration | Ansible | OS hardening, RKE2 bootstrap |
| Autoscaler | Custom Python controller | Scale nodes via Proxmox + Rancher API |
| GitOps | GitHub Actions + ArgoCD | Automated workflows |

## Cluster Layout

### Management Cluster (static, HA)
- 3× Control plane nodes (RKE2 server)
- Runs: Rancher, ArgoCD, Autoscaler controller
- Node spec: 4 vCPU / 8 GB RAM minimum

### Workload Cluster(s)
- 3× Control plane nodes (RKE2 server, static)
- N× Worker nodes (RKE2 agent, auto-scaled)
- Autoscaler range: configurable `min` / `max` per pool

## Autoscaling Logic

```
Every 30s:
  ┌─ Scale UP conditions (ANY):
  │   • Pending pods > 0 for > 2 min
  │   • Node CPU avg > 80% for > 5 min
  │   • Node Memory avg > 85% for > 5 min
  │
  ├─ Scale DOWN conditions (ALL):
  │   • Node CPU avg < 30% for > 10 min
  │   • Node Memory avg < 40% for > 10 min
  │   • No pods would be evicted (PDB respected)
  │   • Node count > min_nodes
  │
  └─ Scale action:
      UP:   Clone Proxmox template → boot VM → cloud-init joins cluster
      DOWN: Select least-utilized node → drain → delete VM
```

## Automated Workflows

| Workflow | Trigger | Action |
|---|---|---|
| `upgrade-k8s.yml` | Manual dispatch / version bump PR | Rolling RKE2 upgrade via Rancher API |
| `change-node-spec.yml` | Terraform vars PR merge | Rolling node replacement with new CPU/RAM |
| `scale-nodes.yml` | Manual dispatch | Immediate scale to target count |
| `deploy-autoscaler.yml` | Push to `main` | Deploy/update autoscaler controller |
| `validate.yml` | Pull request | Terraform plan, Ansible lint, manifest validation |

## Quick Start

### Prerequisites
- Proxmox VE 8.x with API token
- Ubuntu 22.04 cloud-init template (see [docs/proxmox-template.md](docs/proxmox-template.md))
- `terraform`, `ansible`, `kubectl`, `helm`, `gh` CLI installed

### 1. Bootstrap Management Cluster

```bash
# Configure credentials
cp terraform/management-cluster/terraform.tfvars.example \
   terraform/management-cluster/terraform.tfvars
# Edit with your Proxmox details

# Provision VMs
cd terraform/management-cluster
terraform init && terraform apply

# Bootstrap RKE2
cd ../../ansible
ansible-playbook -i inventory/management.ini playbooks/bootstrap-rke2.yml
```

### 2. Install Rancher

```bash
cd rancher/bootstrap
./install.sh
```

### 3. Provision Workload Cluster via Rancher UI

Follow [docs/workload-cluster.md](docs/workload-cluster.md)

### 4. Deploy Autoscaler

```bash
helm install autoscaler autoscaler/helm/autoscaler \
  --namespace kube-system \
  -f autoscaler/helm/autoscaler/values.yaml
```

## Node Spec Changes

Edit `terraform/workload-cluster/terraform.tfvars`:

```hcl
worker_cpu    = 8    # was 4
worker_memory = 16384  # was 8192 (MB)
```

Push PR → GitHub Actions will show Terraform plan → merge triggers rolling replacement.

## K8s Version Upgrade

1. Go to **Actions → upgrade-k8s**
2. Input target RKE2 version (e.g., `v1.30.4+rke2r1`)
3. Workflow upgrades control plane → workers with automatic health checks

## Directory Structure

```
.
├── terraform/
│   ├── modules/
│   │   ├── proxmox-template/    # Cloud-init VM template
│   │   └── rke2-node/           # Node VM provisioning
│   ├── management-cluster/      # Management cluster infra
│   └── workload-cluster/        # Workload cluster infra
├── ansible/
│   ├── inventory/               # Host inventories
│   ├── playbooks/               # Bootstrap, upgrade, replace
│   └── roles/                   # common, rke2-server, rke2-agent
├── rancher/
│   ├── bootstrap/               # Rancher install scripts
│   └── machine-pools/           # Node pool YAML configs
├── autoscaler/
│   ├── controller/              # Python autoscaler source
│   ├── helm/                    # Helm chart for deployment
│   └── Dockerfile
├── docs/                        # Guides and references
└── .github/workflows/           # All automation workflows
```

## Secrets Required (GitHub → Settings → Secrets)

| Secret | Description |
|---|---|
| `PROXMOX_URL` | `https://proxmox.local:8006` |
| `PROXMOX_TOKEN_ID` | `user@pam!token-name` |
| `PROXMOX_TOKEN_SECRET` | API token secret |
| `RANCHER_URL` | `https://rancher.example.com` |
| `RANCHER_TOKEN` | Rancher API token |
| `KUBECONFIG_MGMT` | Base64-encoded kubeconfig for management cluster |

## License

MIT
