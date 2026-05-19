#!/usr/bin/env bash
# Bootstrap Rancher on the management cluster
# Run this after the management cluster is up and kubeconfig is fetched.
set -euo pipefail

RANCHER_HOSTNAME="${RANCHER_HOSTNAME:-rancher.example.com}"
RANCHER_VERSION="${RANCHER_VERSION:-2.9.3}"
CERT_MANAGER_VERSION="${CERT_MANAGER_VERSION:-v1.15.3}"
BOOTSTRAP_PASSWORD="${RANCHER_BOOTSTRAP_PASSWORD:-admin}"
KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

echo "==> Installing cert-manager ${CERT_MANAGER_VERSION}"
kubectl apply -f \
  "https://github.com/cert-manager/cert-manager/releases/download/${CERT_MANAGER_VERSION}/cert-manager.crds.yaml"

helm repo add jetstack https://charts.jetstack.io --force-update
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version "${CERT_MANAGER_VERSION}" \
  --wait

echo "==> Waiting for cert-manager to be ready..."
kubectl -n cert-manager rollout status deployment/cert-manager --timeout=120s
kubectl -n cert-manager rollout status deployment/cert-manager-webhook --timeout=120s

echo "==> Installing Rancher ${RANCHER_VERSION}"
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable --force-update
helm upgrade --install rancher rancher-stable/rancher \
  --namespace cattle-system \
  --create-namespace \
  --version "${RANCHER_VERSION}" \
  --set hostname="${RANCHER_HOSTNAME}" \
  --set bootstrapPassword="${BOOTSTRAP_PASSWORD}" \
  --set ingress.tls.source=letsEncrypt \
  --set letsEncrypt.email="${LETSENCRYPT_EMAIL:-admin@example.com}" \
  --set letsEncrypt.ingress.class=nginx \
  --set replicas=3 \
  --wait \
  --timeout 10m

echo ""
echo "==> Rancher installed!"
echo "    URL:      https://${RANCHER_HOSTNAME}"
echo "    Password: ${BOOTSTRAP_PASSWORD} (change immediately after first login)"
echo ""
echo "==> Next: Install kube-vip for VIP management"
echo "    See docs/kube-vip.md"
