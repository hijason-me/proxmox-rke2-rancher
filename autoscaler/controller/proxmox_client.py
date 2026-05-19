"""Proxmox VE API client for VM lifecycle management."""
import logging
import time
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


class ProxmoxClient:
    def __init__(self, url: str, token_id: str, token_secret: str, verify_ssl: bool = False):
        self.base = url.rstrip("/") + "/api2/json"
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"PVEAPIToken={token_id}={token_secret}"
        self.session.verify = verify_ssl

    def _get(self, path: str) -> dict:
        r = self.session.get(f"{self.base}{path}")
        r.raise_for_status()
        return r.json()["data"]

    def _post(self, path: str, data: dict = None) -> dict:
        r = self.session.post(f"{self.base}{path}", json=data or {})
        r.raise_for_status()
        return r.json()["data"]

    def _delete(self, path: str) -> dict:
        r = self.session.delete(f"{self.base}{path}")
        r.raise_for_status()
        return r.json().get("data")

    def get_next_vm_id(self) -> int:
        return self._get("/cluster/nextid")

    def clone_vm(self, node: str, template_vm_id: int, new_vm_id: int,
                 name: str, full: bool = True, target_node: str = None) -> str:
        """Clone template VM. Returns task UPID."""
        payload = {
            "newid": new_vm_id,
            "name": name,
            "full": 1 if full else 0,
        }
        if target_node:
            payload["target"] = target_node
        return self._post(f"/nodes/{node}/qemu/{template_vm_id}/clone", payload)

    def configure_vm(self, node: str, vm_id: int, cpu: int, memory_mb: int,
                     snippet_storage: str, cloud_init_snippet: str):
        """Set CPU, memory, and attach cloud-init snippet."""
        self.session.put(f"{self.base}/nodes/{node}/qemu/{vm_id}/config", json={
            "cores": cpu,
            "memory": memory_mb,
            "cicustom": f"user={snippet_storage}:snippets/{cloud_init_snippet}",
        }).raise_for_status()

    def upload_snippet(self, node: str, storage: str, filename: str, content: str):
        """Upload a cloud-init snippet to Proxmox storage."""
        r = self.session.post(
            f"{self.base}/nodes/{node}/storage/{storage}/upload",
            data={"content": "snippets", "filename": filename},
            files={"file": (filename, content.encode(), "text/plain")},
        )
        r.raise_for_status()

    def start_vm(self, node: str, vm_id: int) -> str:
        return self._post(f"/nodes/{node}/qemu/{vm_id}/status/start")

    def stop_vm(self, node: str, vm_id: int) -> str:
        return self._post(f"/nodes/{node}/qemu/{vm_id}/status/stop")

    def delete_vm(self, node: str, vm_id: int) -> str:
        return self._delete(f"/nodes/{node}/qemu/{vm_id}?purge=1&destroy-unreferenced-disks=1")

    def get_task_status(self, node: str, upid: str) -> dict:
        return self._get(f"/nodes/{node}/tasks/{upid}/status")

    def wait_for_task(self, node: str, upid: str, timeout: int = 300) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.get_task_status(node, upid)
            if status["status"] == "stopped":
                return status.get("exitstatus") == "OK"
            time.sleep(5)
        raise TimeoutError(f"Task {upid} did not complete within {timeout}s")

    def list_vms_by_tag(self, node: str, tag: str) -> list[dict]:
        """List VMs that have a specific tag."""
        vms = self._get(f"/nodes/{node}/qemu")
        return [vm for vm in vms if tag in (vm.get("tags") or "").split(";")]
