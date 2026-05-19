import os
from dataclasses import dataclass, field


@dataclass
class ScalePolicy:
    min_nodes: int = 2
    max_nodes: int = 10
    # Scale up if ANY condition is true for this many seconds
    scale_up_cpu_threshold: float = 80.0
    scale_up_mem_threshold: float = 85.0
    scale_up_pending_seconds: int = 120    # pods pending > 2 min
    scale_up_cpu_seconds: int = 300        # cpu > threshold for > 5 min
    scale_up_mem_seconds: int = 300
    # Scale down if ALL conditions are true for this many seconds
    scale_down_cpu_threshold: float = 30.0
    scale_down_mem_threshold: float = 40.0
    scale_down_seconds: int = 600          # all below threshold for > 10 min
    # Cooldown between any scaling action
    cooldown_seconds: int = 180


@dataclass
class ProxmoxConfig:
    url: str = ""
    token_id: str = ""
    token_secret: str = ""
    node: str = ""              # Proxmox hypervisor node name
    template_vm_id: int = 9000
    datastore_id: str = "local-lvm"
    snippets_datastore_id: str = "local"
    network_bridge: str = "vmbr0"
    vm_id_start: int = 400      # autoscaler-managed VMs start here
    vm_cpu: int = 4
    vm_memory_mb: int = 8192
    vm_disk_gb: int = 50
    ssh_public_keys: list = field(default_factory=list)
    gateway: str = ""
    dns_servers: list = field(default_factory=lambda: ["1.1.1.1"])


@dataclass
class RKE2Config:
    server_url: str = ""        # https://cluster-vip:9345
    token: str = ""
    version: str = "v1.30.4+rke2r1"


@dataclass
class Config:
    cluster_name: str = "workload-1"
    kubeconfig_path: str = "/etc/autoscaler/kubeconfig"
    loop_interval_seconds: int = 30
    proxmox: ProxmoxConfig = field(default_factory=ProxmoxConfig)
    rke2: RKE2Config = field(default_factory=RKE2Config)
    policy: ScalePolicy = field(default_factory=ScalePolicy)


def load_from_env() -> Config:
    cfg = Config()
    cfg.cluster_name = os.getenv("CLUSTER_NAME", cfg.cluster_name)
    cfg.kubeconfig_path = os.getenv("KUBECONFIG", cfg.kubeconfig_path)
    cfg.loop_interval_seconds = int(os.getenv("LOOP_INTERVAL", cfg.loop_interval_seconds))

    cfg.proxmox.url = os.environ["PROXMOX_URL"]
    cfg.proxmox.token_id = os.environ["PROXMOX_TOKEN_ID"]
    cfg.proxmox.token_secret = os.environ["PROXMOX_TOKEN_SECRET"]
    cfg.proxmox.node = os.environ["PROXMOX_NODE"]
    cfg.proxmox.template_vm_id = int(os.getenv("PROXMOX_TEMPLATE_VM_ID", cfg.proxmox.template_vm_id))
    cfg.proxmox.vm_id_start = int(os.getenv("PROXMOX_VM_ID_START", cfg.proxmox.vm_id_start))
    cfg.proxmox.vm_cpu = int(os.getenv("WORKER_CPU", cfg.proxmox.vm_cpu))
    cfg.proxmox.vm_memory_mb = int(os.getenv("WORKER_MEMORY_MB", cfg.proxmox.vm_memory_mb))
    cfg.proxmox.vm_disk_gb = int(os.getenv("WORKER_DISK_GB", cfg.proxmox.vm_disk_gb))
    cfg.proxmox.gateway = os.getenv("GATEWAY", "")
    cfg.proxmox.datastore_id = os.getenv("DATASTORE_ID", cfg.proxmox.datastore_id)
    cfg.proxmox.snippets_datastore_id = os.getenv("SNIPPETS_DATASTORE_ID", cfg.proxmox.snippets_datastore_id)
    cfg.proxmox.network_bridge = os.getenv("NETWORK_BRIDGE", cfg.proxmox.network_bridge)

    cfg.rke2.server_url = os.environ["RKE2_SERVER_URL"]
    cfg.rke2.token = os.environ["RKE2_TOKEN"]
    cfg.rke2.version = os.getenv("RKE2_VERSION", cfg.rke2.version)

    cfg.policy.min_nodes = int(os.getenv("MIN_NODES", cfg.policy.min_nodes))
    cfg.policy.max_nodes = int(os.getenv("MAX_NODES", cfg.policy.max_nodes))
    cfg.policy.scale_up_cpu_threshold = float(os.getenv("SCALE_UP_CPU", cfg.policy.scale_up_cpu_threshold))
    cfg.policy.scale_up_mem_threshold = float(os.getenv("SCALE_UP_MEM", cfg.policy.scale_up_mem_threshold))
    cfg.policy.scale_down_cpu_threshold = float(os.getenv("SCALE_DOWN_CPU", cfg.policy.scale_down_cpu_threshold))
    cfg.policy.scale_down_mem_threshold = float(os.getenv("SCALE_DOWN_MEM", cfg.policy.scale_down_mem_threshold))
    cfg.policy.cooldown_seconds = int(os.getenv("COOLDOWN_SECONDS", cfg.policy.cooldown_seconds))

    return cfg
