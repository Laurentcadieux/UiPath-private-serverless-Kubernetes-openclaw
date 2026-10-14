# Operations Guide - UiPath Private Serverless Kubernetes

## Deployment

### Prerequisites
- Kubernetes 1.24+
- Helm 3.x
- KEDA 2.x (for event-driven scaling)
- `uip` CLI authenticated (for queue metrics)

### Install KEDA
```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace
```

### Deploy with Helm
```bash
helm install uipath-runtime ./OUTPUT_Product/helm/uipath-runtime \
  --namespace uipath-runtime --create-namespace \
  --set folderPath="Shared/LinuxRPA" \
  --set machineTemplates.default="your-machine-key" \
  --set keda.queueName="your-queue"
```

### Deploy the Operator (alternative to KEDA)
```bash
# Install CRDs
kubectl apply -f OUTPUT_Product/operator/crd/

# Deploy operator
kubectl apply -f OUTPUT_Product/operator/config/deployment.yaml
```

## Monitoring

### Check KEDA Scaling
```bash
kubectl get scaledobject -n uipath-runtime
kubectl get jobs -n uipath-runtime -w
```

### Check Queue Depth
```bash
# Port-forward the metrics service
kubectl port-forward svc/uipath-queue-metrics -n uipath-runtime 8080:8080

# Query
curl http://localhost:8080/scale?queueName=your-queue
curl http://localhost:8080/queues
```

### Check Ephemeral Jobs
```bash
# List active robot jobs
kubectl get jobs -n uipath-runtime -l app.kubernetes.io/name=uipath-robot

# Watch a specific job
kubectl logs -f job/uipath-robot-xxxxx -n uipath-runtime

# Check job lifecycle (creation → completion → TTL deletion)
kubectl get events -n uipath-runtime --sort-by='.lastTimestamp'
```

## Scaling

### Adjust Concurrency
```bash
helm upgrade uipath-runtime ./OUTPUT_Product/helm/uipath-runtime \
  --set keda.minReplicaCount=0 \
  --set keda.maxReplicaCount=20
```

### Resource Limits
```bash
helm upgrade uipath-runtime ./OUTPUT_Product/helm/uipath-runtime \
  --set robot.resources.limits.cpu=4 \
  --set robot.resources.limits.memory=8Gi
```

## Troubleshooting

### Jobs Not Being Created
1. Check KEDA ScaledObject status: `kubectl describe scaledobject -n uipath-runtime`
2. Check queue metrics service: `curl http://localhost:8080/health`
3. Check uip CLI auth: `uip user`
4. Check machine key secret: `kubectl get secret uipath-machine-keys -n uipath-runtime`

### Jobs Stuck/Failing
1. Check pod logs: `kubectl logs -n uipath-runtime <pod-name>`
2. Check pod events: `kubectl describe pod -n uipath-runtime <pod-name>`
3. Common issues:
   - Machine key invalid → update `uipath-machine-keys` secret
   - Image pull error → check `robot.image` value
   - Resource limits → increase `robot.resources`

### Cleanup Stale Jobs
```bash
# Delete all completed jobs
kubectl delete jobs -n uipath-runtime -l app.kubernetes.io/name=uipath-robot --field-selector status.successful=1
```

## Uninstall
```bash
helm uninstall uipath-runtime --namespace uipath-runtime
kubectl delete namespace uipath-runtime
```
