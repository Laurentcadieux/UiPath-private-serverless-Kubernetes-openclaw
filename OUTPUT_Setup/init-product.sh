#!/usr/bin/env bash
# init-product.sh - Initialize the UiPath runtime product
#
# Usage: bash init-product.sh
#
# Deploys:
#   - Queue metrics service
#   - KEDA ScaledObject (event-driven scaling)
#   - Verifies all components

set -euo pipefail

echo "=== UiPath Private Serverless Kubernetes - Product Init ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PRODUCT_DIR="${SCRIPT_DIR}/../OUTPUT_Product"

# Check that secrets exist
echo "1. Verifying secrets..."
if ! kubectl get secret uipath-config -n uipath-runtime >/dev/null 2>&1; then
  echo "WARNING: uipath-config secret not found. Create it before enabling scaling."
  echo "  kubectl create secret generic uipath-config --namespace uipath-runtime \\"
  echo "    --from-literal=orchestrator-url='...' \\"
  echo "    --from-literal=orchestrator-tenant='...'"
fi

if ! kubectl get secret uipath-machine-keys -n uipath-runtime >/dev/null 2>&1; then
  echo "WARNING: uipath-machine-keys secret not found. Create it before robot pods can start."
  echo "  kubectl create secret generic uipath-machine-keys --namespace uipath-runtime \\"
  echo "    --from-literal=default-template='your-machine-key'"
fi

echo ""
echo "2. Deploying queue metrics service..."
kubectl apply -f "${PRODUCT_DIR}/config/queue-metrics.example.yaml"

echo ""
echo "3. Deploying KEDA ScaledObject..."
kubectl apply -f "${PRODUCT_DIR}/config/scaledobject.example.yaml"

echo ""
echo "4. Verifying deployment..."
echo "   KEDA ScaledObject:"
kubectl get scaledobject -n uipath-runtime 2>/dev/null || echo "   (not found - check KEDA installation)"
echo ""
echo "   Queue Metrics Service:"
kubectl get deployment uipath-queue-metrics -n uipath-runtime
echo ""
echo "   Network Policies:"
kubectl get networkpolicy -n uipath-runtime

echo ""
echo "=== Product Init Complete ==="
echo ""
echo "Your cluster is ready for ephemeral UiPath Robot execution."
echo "Add items to your Orchestrator queue to trigger pod creation."
echo ""
echo "Watch it in action:"
echo "  kubectl get jobs -n uipath-runtime -w"
