# Architecture - UiPath Private Serverless Kubernetes

## Design Goals

1. **Truly Ephemeral**: Each robot execution runs in a fresh pod that is deleted after completion
2. **Event-Driven**: Scale based on Orchestrator queue depth, not fixed pod counts
3. **Zero-Persistence**: No shared filesystem or sticky containers between executions
4. **Resource-Efficient**: Scale to zero when idle, burst on demand
5. **Secure**: Machine keys in Kubernetes Secrets, no credential leakage

## Component Overview

### 1. Kubernetes Operator (Custom Resource)

**Purpose**: Orchestrates ephemeral robot pods by watching Orchestrator queues

**Components**:
- `UiPathRobotJob` CRD: Represents a robot execution request
- `UiPathMachineTemplate` CRD: Defines machine configuration (image, resources, machine key secret)
- `QueueWatcher` controller: Polls Orchestrator queues, creates `UiPathRobotJob` for pending items

**Flow**:
```
Orchestrator Queue → QueueWatcher → UiPathRobotJob → Kubernetes Job → Robot Pod → Execute → Delete
```

### 2. KEDA Integration

**Purpose**: Event-driven scaling without a custom operator

**Components**:
- `ScaledObject`: Points to Orchestrator queue as scaling trigger
- `Job` template: Defines the ephemeral robot pod

**Flow**:
```
Queue Items → KEDA Scaler → Kubernetes Jobs → Robot Pods → Execute → Complete → Cleanup
```

### 3. Robot Pod Template

**Container Spec**:
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  generateName: uipath-robot-
spec:
  ttlSecondsAfterFinished: 60  # Auto-delete after 1 minute
  template:
    spec:
      containers:
      - name: robot
        image: uipath/coding-robot:latest  # Or your custom robot image
        env:
        - name: UIPATH_ORCHESTRATOR_URL
          valueFrom:
            secretKeyRef:
              name: uipath-config
              key: orchestrator-url
        - name: UIPATH_MACHINE_KEY
          valueFrom:
            secretKeyRef:
              name: uipath-machine-keys
              key: machine-template-1
        - name: UIPATH_JOB_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['uipath-job-id']
        - name: UIPATH_QUEUE_NAME
          value: "your-queue-name"
        - name: UIPATH_RUN_ONCE
          value: "true"  # Exit after single execution
        resources:
          limits:
            cpu: "2"
            memory: "4Gi"
          requests:
            cpu: "1"
            memory: "2Gi"
      restartPolicy: Never
```

### 4. Execution Modes

#### Mode A: KEDA + Jobs (Recommended)
- **Pros**: Simple, managed scaling, no custom controller
- **Cons**: Requires KEDA deployment
- **Use Case**: Most scenarios, event-driven queues

#### Mode B: Custom Operator
- **Pros**: Full control, custom reconciliation logic
- **Cons**: More complex, needs Go/Python operator code
- **Use Case**: Complex orchestration, multi-tenant isolation

#### Mode C: CronJob Polling
- **Pros**: No external dependencies, simple
- **Cons**: Not truly event-driven, polling overhead
- **Use Case**: Backup, low-frequency queues

## Data Flow

### Queue-Driven Execution

```
1. User adds item to UiPath Queue
2. KEDA scaler detects queue depth
3. KEDA creates Kubernetes Job for each item (or batch)
4. Robot pod pulls queue item, executes workflow
5. Robot pod posts result to Orchestrator
6. Job completes, pod is auto-deleted (ttlSecondsAfterFinished)
7. KEDA scales down if queue is empty
```

### Scheduled Execution

```
1. CronJob triggers at schedule
2. Creates Job with specific process/job
3. Robot pod executes scheduled job
4. Completes, pod auto-deleted
```

## Security Model

1. **Machine Keys**: Stored as Kubernetes Secrets, mounted as environment variables
2. **Orchestrator URL**: Secret, injected via environment
3. **Network Policies**: Restrict pod egress to Orchestrator only
3. **Pod Security Standards**: Enforce non-root, read-only root filesystem
4. **RBAC**: Least-privilege service accounts for operator

## Scalability Considerations

- **Pod Startup Time**: Use pre-pulled images, node affinity for faster scheduling
- **Queue Burst Size**: KEDA `replicaCount` limits to prevent runaway scaling
- **Resource Quotas**: Namespace-level limits to prevent resource exhaustion
- **Node Autoscaling**: Cluster Autoscaler or Karpenter for node-level scaling

## Monitoring & Observability

- **Prometheus Metrics**: Export queue depth, pod status, execution time
- **Logs**: Structured JSON logs to cluster logging system
- **Events**: Kubernetes events for job creation/completion/failure

## Next Steps

1. Choose execution mode (KEDA vs custom operator vs CronJob)
2. Define `UiPathMachineTemplate` CRD schema
3. Build operator or KEDA scaler
4. Create Helm charts
5. Add integration tests