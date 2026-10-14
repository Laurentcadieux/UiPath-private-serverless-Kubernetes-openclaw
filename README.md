# UiPath Private Serverless - Kubernetes Edition

Ephemeral UiPath Linux Robot runtime on Kubernetes. Each robot execution spins up a fresh pod, runs the job, and gets deleted — no sticky containers.

## Concept

Inspired by [UiPath-private-serverless](https://github.com/Laurentcadieux/UiPath-private-serverless), but adapted for K8s with truly ephemeral workers:

- **Original**: Long-lived Docker containers on VM, scale up/down, reuse containers
- **K8s Edition**: Short-lived pods, one execution per pod, auto-replaced, fully ephemeral

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    UiPath Orchestrator                       │
│                    (Cloud or On-Prem)                         │
└────────────────────┬────────────────────────────────────────┘
                     │ Machine Key / Queue Triggers
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Kubernetes Operator / Controller                │
│  - Polls Orchestrator for pending jobs                       │
│  - Creates ephemeral Jobs/Pods for each execution            │
│  - Monitors completion, reports status back                  │
│  - Cleans up completed/failed pods                           │
└────────────────────┬────────────────────────────────────────┘
                     │ Creates ephemeral pods
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   UiPath Robot Pods                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Robot Pod 1 │  │ Robot Pod 2 │  │ Robot Pod N │          │
│  │ ephemeral   │  │ ephemeral   │  │ ephemeral   │          │
│  │ runs once   │  │ runs once   │  │ runs once   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                     ↓ after completion                         │
│                 Auto-deleted & replaced                        │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

- **Ephemeral Workers**: Each robot execution runs in a fresh pod; pods are deleted after completion
- **KEDA Integration**: Event-driven scaling based on Orchestrator queues
- **Machine Key Management**: Kubernetes Secrets for Orchestrator credentials
- **Resource Isolation**: Per-pod resource limits, no shared runtime state
- **Auto-Replacement**: Failed pods are replaced; scale-to-zero when idle
- **Multi-Tenant Support**: Multiple machine templates, isolation per tenant

## Project Structure

```
UiPath-private-serverless-Kubernetes/
├── README.md                    # This file
├── OUTPUT_Setup/                # Cluster initialization
│   ├── install.sh              # Set up K8s prerequisites
│   ├── init-product.sh         # Initialize operator & CRDs
│   └── README.md               # Setup instructions
├── OUTPUT_Product/              # Runtime components
│   ├── operator/               # Custom Kubernetes operator (Go/Python)
│   ├── helm/                   # Helm charts for deployment
│   ├── config/                 # Configuration models and examples
│   ├── scripts/                # Utility scripts
│   ├── docs/                   # Operational docs
│   └── tests/                  # Tests
└── AI_Project/                  # Development workspace
    ├── .omx/                   # Agent workspace metadata
    ├── memory/                 # Development notes
    └── skills/                 # Reusable skills
```

## Quick Start (TBD)

```bash
# 1. Clone and setup
git clone https://github.com/Laurentcadieux/UiPath-private-serverless-Kubernetes.git
cd UiPath-private-serverless-Kubernetes/UiPath-private-serverless-Kubernetes

# 2. Initialize cluster
kubectl apply -f OUTPUT_Setup/

# 3. Deploy operator
helm install uipath-runtime-operator ./OUTPUT_Product/helm/operator

# 4. Configure machine keys
kubectl create secret generic uipath-machine-keys \
  --from-literal=machine-template-1=your-key-here \
  --from-literal=machine-template-2=another-key-here

# 5. Enable queue scaling
kubectl apply -f OUTPUT_Product/config/scaledobjects/
```

## Current Status

🚧 **In Progress** — Project scaffolding and design phase.

## License

Same as parent project — TBD