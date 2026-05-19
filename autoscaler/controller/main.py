"""
Proxmox RKE2 Node Autoscaler

Scale-up:  pending pods OR high CPU/mem → clone Proxmox VM → joins cluster via cloud-init
Scale-down: low utilization → drain node → delete VM
"""
import logging
import time
import textwrap
from datetime import datetime, timedelta

from config import Config, load_from_env
from proxmox_client import ProxmoxClient
from k8s_client import K8sClient, NodeMetrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("autoscaler")

AUTOSCALER_TAG = "autoscaler-managed"


class Autoscaler:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.proxmox = ProxmoxClient(
            url=cfg.proxmox.url,
            token_id=cfg.proxmox.token_id,
            token_secret=cfg.proxmox.token_secret,
        )
        self.k8s = K8sClient(cfg.kubeconfig_path)

        # Timestamps tracking when conditions were first observed
        self._pending_pods_since: datetime | None = None
        self._high_cpu_since: datetime | None = None
        self._high_mem_since: datetime | None = None
        self._low_util_since: datetime | None = None
        self._last_scale_action: datetime = datetime.min

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        logger.info("Autoscaler started — cluster=%s interval=%ds",
                    self.cfg.cluster_name, self.cfg.loop_interval_seconds)
        while True:
            try:
                self._tick()
            except Exception:
                logger.exception("Unhandled error in autoscaler tick")
            time.sleep(self.cfg.loop_interval_seconds)

    def _tick(self):
        policy = self.cfg.policy
        now = datetime.utcnow()

        metrics = self.k8s.get_node_metrics()
        pending = self.k8s.count_pending_pods()
        worker_count = len(self.k8s.get_worker_nodes())

        avg_cpu = (sum(m.cpu_percent for m in metrics) / len(metrics)) if metrics else 0.0
        avg_mem = (sum(m.mem_percent for m in metrics) / len(metrics)) if metrics else 0.0

        logger.info(
            "nodes=%d  pending_pods=%d  cpu_avg=%.1f%%  mem_avg=%.1f%%",
            worker_count, pending, avg_cpu, avg_mem,
        )

        # ── Track condition windows ───────────────────────────────────────────
        self._pending_pods_since = now if pending > 0 else None
        self._high_cpu_since     = self._high_cpu_since if avg_cpu > policy.scale_up_cpu_threshold else None
        self._high_mem_since     = self._high_mem_since if avg_mem > policy.scale_up_mem_threshold else None

        if avg_cpu > policy.scale_up_cpu_threshold and self._high_cpu_since is None:
            self._high_cpu_since = now
        if avg_mem > policy.scale_up_mem_threshold and self._high_mem_since is None:
            self._high_mem_since = now

        low_util = (avg_cpu < policy.scale_down_cpu_threshold and
                    avg_mem < policy.scale_down_mem_threshold)
        if low_util:
            self._low_util_since = self._low_util_since or now
        else:
            self._low_util_since = None

        in_cooldown = (now - self._last_scale_action).total_seconds() < policy.cooldown_seconds

        # ── Scale up? ────────────────────────────────────────────────────────
        if not in_cooldown and worker_count < policy.max_nodes:
            scale_up = False
            if self._pending_pods_since and \
               (now - self._pending_pods_since).total_seconds() >= policy.scale_up_pending_seconds:
                logger.info("Scale-up trigger: pending pods for %ds", policy.scale_up_pending_seconds)
                scale_up = True
            if self._high_cpu_since and \
               (now - self._high_cpu_since).total_seconds() >= policy.scale_up_cpu_seconds:
                logger.info("Scale-up trigger: cpu>%.0f%% for %ds",
                            policy.scale_up_cpu_threshold, policy.scale_up_cpu_seconds)
                scale_up = True
            if self._high_mem_since and \
               (now - self._high_mem_since).total_seconds() >= policy.scale_up_mem_seconds:
                logger.info("Scale-up trigger: mem>%.0f%% for %ds",
                            policy.scale_up_mem_threshold, policy.scale_up_mem_seconds)
                scale_up = True

            if scale_up:
                self._scale_up()
                self._last_scale_action = datetime.utcnow()
                self._pending_pods_since = None
                self._high_cpu_since = None
                self._high_mem_since = None
                return

        # ── Scale down? ──────────────────────────────────────────────────────
        if not in_cooldown and worker_count > policy.min_nodes:
            if self._low_util_since and \
               (now - self._low_util_since).total_seconds() >= policy.scale_down_seconds:
                logger.info("Scale-down trigger: low utilization for %ds", policy.scale_down_seconds)
                victim = self.k8s.find_least_utilized_node(metrics)
                if victim:
                    self._scale_down(victim)
                    self._last_scale_action = datetime.utcnow()
                    self._low_util_since = None

    # ── Scale actions ─────────────────────────────────────────────────────────

    def _scale_up(self):
        node_name = self._next_node_name()
        vm_id = self._next_vm_id()
        logger.info("Scaling up: creating node %s (vmid=%d)", node_name, vm_id)

        snippet_content = self._render_cloud_init(node_name)
        snippet_name = f"{node_name}-ci.yaml"

        pxcfg = self.cfg.proxmox
        rke2cfg = self.cfg.rke2

        # Upload cloud-init snippet
        self.proxmox.upload_snippet(
            node=pxcfg.node,
            storage=pxcfg.snippets_datastore_id,
            filename=snippet_name,
            content=snippet_content,
        )

        # Clone template
        upid = self.proxmox.clone_vm(
            node=pxcfg.node,
            template_vm_id=pxcfg.template_vm_id,
            new_vm_id=vm_id,
            name=node_name,
        )
        self.proxmox.wait_for_task(pxcfg.node, upid)

        # Configure specs and cloud-init
        self.proxmox.configure_vm(
            node=pxcfg.node,
            vm_id=vm_id,
            cpu=pxcfg.vm_cpu,
            memory_mb=pxcfg.vm_memory_mb,
            snippet_storage=pxcfg.snippets_datastore_id,
            cloud_init_snippet=snippet_name,
        )

        # Tag VM so we can track autoscaler-managed nodes
        self.proxmox.session.put(
            f"{self.proxmox.base}/nodes/{pxcfg.node}/qemu/{vm_id}/config",
            json={"tags": AUTOSCALER_TAG},
        ).raise_for_status()

        # Boot
        upid = self.proxmox.start_vm(pxcfg.node, vm_id)
        self.proxmox.wait_for_task(pxcfg.node, upid)

        logger.info("Node %s booting — will join cluster via cloud-init", node_name)

    def _scale_down(self, victim: NodeMetrics):
        node_name = victim.name
        logger.info("Scaling down: draining and removing node %s", node_name)

        self.k8s.drain_node(node_name)
        time.sleep(30)  # grace period for pods to terminate
        self.k8s.delete_node(node_name)

        # Find and delete the Proxmox VM by name
        pxcfg = self.cfg.proxmox
        vms = self.proxmox.list_vms_by_tag(pxcfg.node, AUTOSCALER_TAG)
        for vm in vms:
            if vm.get("name") == node_name:
                upid = self.proxmox.stop_vm(pxcfg.node, vm["vmid"])
                self.proxmox.wait_for_task(pxcfg.node, upid, timeout=120)
                self.proxmox.delete_vm(pxcfg.node, vm["vmid"])
                logger.info("Deleted VM %d (%s)", vm["vmid"], node_name)
                break
        else:
            logger.warning("No Proxmox VM found for node %s", node_name)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _next_node_name(self) -> str:
        existing = {n.name for n in self.k8s.get_worker_nodes()}
        i = 1
        while True:
            name = f"{self.cfg.cluster_name}-auto-{i}"
            if name not in existing:
                return name
            i += 1

    def _next_vm_id(self) -> int:
        pxcfg = self.cfg.proxmox
        vms = self.proxmox.list_vms_by_tag(pxcfg.node, AUTOSCALER_TAG)
        used = {vm["vmid"] for vm in vms}
        vm_id = pxcfg.vm_id_start
        while vm_id in used:
            vm_id += 1
        return vm_id

    def _render_cloud_init(self, hostname: str) -> str:
        rke2 = self.cfg.rke2
        return textwrap.dedent(f"""\
            #cloud-config
            hostname: {hostname}
            package_update: false
            runcmd:
              - mkdir -p /etc/rancher/rke2
              - |
                cat > /etc/rancher/rke2/config.yaml << 'EOF'
                token: {rke2.token}
                server: {rke2.server_url}
                node-label:
                  - "node-role=worker"
                  - "managed-by=autoscaler"
                EOF
              - curl -sfL https://get.rke2.io | INSTALL_RKE2_VERSION="{rke2.version}" INSTALL_RKE2_TYPE="agent" sh -
              - systemctl enable --now rke2-agent
        """)


if __name__ == "__main__":
    cfg = load_from_env()
    Autoscaler(cfg).run()
