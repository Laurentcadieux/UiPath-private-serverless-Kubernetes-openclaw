# uipath-runtime Helm Chart

Ephemeral UiPath Linux Robot runtime on Kubernetes with KEDA event-driven scaling.

## Quick Install

```bash
# Add KEDA (required for event-driven scaling)
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace

# Install uipath-runtime
helm install uipath-runtime ./helm/uipath-runtime \
  --namespace uipath-runtime \
  --set orchestrator.url="https://cloud.uipath.com" \
  --set orchestrator.tenant="your-tenant" \
  --set auth.clientId="your-client-id" \
  --set auth.clientSecret="your-client-secret" \
  --set machineTemplates.default="your-machine-key" \
  --set keda.queueName="your-queue-name"
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `orchestrator.url` | UiPath Orchestrator URL | `https://cloud.uipath.com` |
| `orchestrator.tenant` | Orchestrator tenant | `default` |
| `auth.clientId` | OAuth client ID | `""` |
| `auth.clientSecret` | OAuth client secret | `""` |
| `machineTemplates` | Map of template name → machine key | `{default: ""}` |
| `robot.image` | Robot container image | `uipath/robot:latest` |
| `robot.defaultMachineTemplate` | Default template name | `default` |
| `robot.defaultQueueName` | Default queue name | `""` |
| `robot.runOnce` | Exit after one execution | `true` |
| `robot.ttlSecondsAfterFinished` | Auto-delete Job after N seconds | `60` |
| `robot.resources` | Pod resource limits/requests | cpu 1-2, mem 2-4Gi |
| `keda.enabled` | Enable KEDA scaling | `true` |
| `keda.minReplicaCount` | Min concurrent pods (0 = scale-to-zero) | `0` |
| `keda.maxReplicaCount` | Max concurrent pods | `10` |
| `keda.pollingInterval` | Queue check interval (seconds) | `10` |
| `keda.queueName` | Queue to monitor | `""` |
| `queueMetrics.image` | Metrics service image | `uipath-queue-metrics:latest` |
| `queueMetrics.pollInterval` | Orchestrator poll cache (seconds) | `5` |
| `networkPolicy.enabled` | Enable egress lockdown | `true` |
| `networkPolicy.orchestratorCidr` | Allowed Orchestrator CIDR | `0.0.0.0/0` |
| `namespace` | Target namespace | `uipath-runtime` |

## Examples

### Scale-to-zero with 10 max pods
```bash
helm install uipath-runtime ./helm/uipath-runtime \
  --set keda.minReplicaCount=0 \
  --set keda.maxReplicaCount=10
```

### Disable KEDA (use manual Jobs)
```bash
helm install uipath-runtime ./helm/uipath-runtime \
  --set keda.enabled=false
```

### Multiple machine templates
```bash
helm install uipath-runtime ./helm/uipath-runtime \
  --set machineTemplates.default="key-abc123" \
  --set machineTemplates.highcpu="key-def456" \
  --set robot.defaultMachineTemplate="highcpu"
```

## Uninstall

```bash
helm uninstall uipath-runtime --namespace uipath-runtime
```
