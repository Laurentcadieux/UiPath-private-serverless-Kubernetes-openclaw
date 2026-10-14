#!/usr/bin/env bash
# install.sh - Install Kubernetes cluster prerequisites
#
# Usage: bash install.sh
#
# Installs:
#   - KEDA (event-driven scaling)
#   - Creates uipath-runtime namespace
#   - Deploys network policies and service accounts

set -euo pipefail

echo "=== UiPath Private Serverless Kubernetes - Setup ==="

# Check prerequisites
command -v kubectl >/dev/null 2>&1 || { echo "ERROR: kubectl not found"; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "ERROR: helm not found"; exit 1; }

echo ""
echo "1. Creating namespace..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: uipath-runtime
  labels:
    app.kubernetes.io/name: uipath-runtime
    app.kubernetes.io/part-of: uipath-private-serverless
EOF

echo ""
echo "2. Installing KEDA..."
helm repo add kedacore https://kedacore.github.io/charts 2>/dev/null || true
helm repo update
helm upgrade --install keda kedacore/keda --namespace keda --create-namespace

echo ""
echo "3. Applying network policies and service accounts..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
kubectl apply -f "${SCRIPT_DIR}/../OUTPUT_Product/config/networkpolicy.example.yaml"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Create secrets: kubectl create secret generic uipath-config ..."
echo "  2. Create machine keys: kubectl create secret generic uipath-machine-keys ..."
echo "  3. Run: bash init-product.sh"
