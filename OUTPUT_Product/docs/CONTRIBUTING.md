# Contributing

## Development

### Local Setup
```bash
git clone https://github.com/Laurentcadieux/UiPath-private-serverless-Kubernetes-openclaw.git
cd UiPath-private-serverless-Kubernetes-openclaw
```

### Validate
```bash
make validate
make helm-template
```

### Test
```bash
make e2e-simulate
```

### Build
```bash
make build
```

## Project Structure
```
OUTPUT_Product/
├── config/           # K8s manifest examples
├── docs/             # Architecture & operations docs
├── helm/             # Helm chart
├── operator/         # Custom K8s operator (kopf)
│   ├── crd/          # Custom Resource Definitions
│   └── src/          # Operator controller code
├── scripts/          # Utility scripts
├── src/              # Queue metrics service + Dockerfiles
└── tests/            # E2E simulation tests

OUTPUT_Setup/         # Cluster initialization scripts
.github/workflows/    # CI/CD
```

## Making Changes

1. Create a feature branch
2. Make changes
3. Run `make validate` and `make e2e-simulate`
4. Push and open a PR
5. CI will validate manifests, Helm chart, and run tests

## Architecture Decision Records

When making significant architecture changes, document the decision in `OUTPUT_Product/docs/` with context, decision, and consequences.
