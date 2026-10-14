# Setup - Cluster Prerequisites

## Overview

Prepares your Kubernetes cluster to run ephemeral UiPath Robot pods.

## Prerequisites

- Kubernetes 1.24+ with `batch/v1` Jobs API
- `kubectl` configured with cluster admin access
- Helm 3.x installed
- KEDA 2.x installed (for event-driven scaling)

## Install KEDA

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace
```

## Install Runtime Prerequisites

```bash
# Create namespace
kubectl apply -f config/secrets.example.yaml

# Apply network policies
kubectl apply -f config/networkpolicy.example.yaml

# Deploy queue metrics service
kubectl apply -f config/queue-metrics.example.yaml
```

## Configure Secrets

**IMPORTANT**: Never commit real machine keys. Use the example as a template:

```bash
# Create secrets with real values
kubectl create secret generic uipath-config \
  --namespace uipath-runtime \
  --from-literal=orchestrator-url='https://cloud.uipath.com' \
  --from-literal=orchestrator-tenant='your-tenant' \
  --from-literal=client-id='your-client-id' \
  --from-literal=client-secret='your-client-secret'

kubectl create secret generic uipath-machine-keys \
  --namespace uipath-runtime \
  --from-literal=default-template='your-machine-key-here'
```

## Deploy Scaling

```bash
# Enable KEDA queue scaling
kubectl apply -f config/scaledobject.example.yaml
```

## Verify

```bash
# Check KEDA is watching the queue
kubectl get scaledobject -n uipath-runtime

# Watch ephemeral jobs being created
kubectl get jobs -n uipath-runtime -w

# Check completed jobs auto-deleted
kubectl get jobs -n uipath-runtime
```
