"""Kubernetes client helpers for autoscaler metrics and node management."""
import logging
from dataclasses import dataclass
from typing import Optional

from kubernetes import client, config as k8s_config

logger = logging.getLogger(__name__)


@dataclass
class NodeMetrics:
    name: str
    cpu_usage_cores: float
    mem_usage_bytes: int
    cpu_allocatable_cores: float
    mem_allocatable_bytes: int
    is_ready: bool
    is_schedulable: bool

    @property
    def cpu_percent(self) -> float:
        if self.cpu_allocatable_cores == 0:
            return 0.0
        return (self.cpu_usage_cores / self.cpu_allocatable_cores) * 100

    @property
    def mem_percent(self) -> float:
        if self.mem_allocatable_bytes == 0:
            return 0.0
        return (self.mem_usage_bytes / self.mem_allocatable_bytes) * 100


def _parse_cpu(cpu_str: str) -> float:
    """Parse CPU quantity string to fractional cores."""
    if cpu_str.endswith("n"):
        return int(cpu_str[:-1]) / 1e9
    if cpu_str.endswith("m"):
        return int(cpu_str[:-1]) / 1000
    return float(cpu_str)


def _parse_mem(mem_str: str) -> int:
    """Parse memory quantity string to bytes."""
    units = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3,
             "K": 1000, "M": 1000**2, "G": 1000**3}
    for suffix, mult in units.items():
        if mem_str.endswith(suffix):
            return int(mem_str[:-len(suffix)]) * mult
    return int(mem_str)


class K8sClient:
    def __init__(self, kubeconfig_path: str):
        k8s_config.load_kube_config(config_file=kubeconfig_path)
        self.core = client.CoreV1Api()
        self.custom = client.CustomObjectsApi()

    def get_worker_nodes(self) -> list[client.V1Node]:
        """Return all non-control-plane nodes."""
        nodes = self.core.list_node().items
        return [
            n for n in nodes
            if "node-role.kubernetes.io/control-plane" not in (n.metadata.labels or {})
            and "node-role.kubernetes.io/master" not in (n.metadata.labels or {})
        ]

    def get_node_metrics(self) -> list[NodeMetrics]:
        """Get per-node CPU and memory usage from metrics-server."""
        try:
            raw = self.custom.list_cluster_custom_object(
                "metrics.k8s.io", "v1beta1", "nodes"
            )
        except Exception as e:
            logger.warning("metrics-server unavailable: %s", e)
            return []

        metric_map = {
            item["metadata"]["name"]: item["usage"]
            for item in raw["items"]
        }

        nodes = self.get_worker_nodes()
        result = []
        for node in nodes:
            name = node.metadata.name
            usage = metric_map.get(name, {})
            alloc = node.status.allocatable or {}
            conditions = {c.type: c.status for c in (node.status.conditions or [])}

            result.append(NodeMetrics(
                name=name,
                cpu_usage_cores=_parse_cpu(usage.get("cpu", "0")),
                mem_usage_bytes=_parse_mem(usage.get("memory", "0")),
                cpu_allocatable_cores=_parse_cpu(alloc.get("cpu", "0")),
                mem_allocatable_bytes=_parse_mem(alloc.get("memory", "0")),
                is_ready=conditions.get("Ready") == "True",
                is_schedulable=not node.spec.unschedulable,
            ))
        return result

    def count_pending_pods(self) -> int:
        """Count pods in Pending phase that are not being deleted."""
        pods = self.core.list_pod_for_all_namespaces(field_selector="status.phase=Pending").items
        return sum(
            1 for p in pods
            if p.metadata.deletion_timestamp is None
        )

    def drain_node(self, node_name: str):
        """Cordon and evict all evictable pods from a node."""
        # Cordon
        node = self.core.read_node(node_name)
        node.spec.unschedulable = True
        self.core.patch_node(node_name, node)
        logger.info("Cordoned node %s", node_name)

        # Evict pods
        pods = self.core.list_pod_for_all_namespaces(
            field_selector=f"spec.nodeName={node_name}"
        ).items
        for pod in pods:
            if pod.metadata.owner_references:
                for ref in pod.metadata.owner_references:
                    if ref.kind == "DaemonSet":
                        continue
            try:
                self.core.create_namespaced_pod_eviction(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    body=client.V1Eviction(
                        metadata=client.V1ObjectMeta(
                            name=pod.metadata.name,
                            namespace=pod.metadata.namespace,
                        )
                    ),
                )
            except Exception as e:
                logger.warning("Could not evict pod %s/%s: %s",
                               pod.metadata.namespace, pod.metadata.name, e)

    def delete_node(self, node_name: str):
        self.core.delete_node(node_name)
        logger.info("Deleted node %s from cluster", node_name)

    def find_least_utilized_node(self, metrics: list[NodeMetrics]) -> Optional[NodeMetrics]:
        """Pick the node with the lowest combined CPU+mem utilization."""
        candidates = [m for m in metrics if m.is_schedulable]
        if not candidates:
            return None
        return min(candidates, key=lambda m: m.cpu_percent + m.mem_percent)
