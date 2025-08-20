# Uptime Operator

A production-ready Kubernetes Operator for managing [Uptime Kuma](https://uptime.kuma.pet/) monitors using Custom Resources.

## Quick Start

```bash
# Setup
cp env.example .env && nano .env
uv sync
docker-compose up -d

# Deploy
kubectl apply -f manifests/crd.yaml
kubectl apply -f examples/simple-monitor.yaml

# Run operator
kopf run main.py
```

## Project Structure

```
uptime-operator/
├── operator/                    # Core operator package
│   ├── handlers/               # Kopf event handlers
│   │   ├── uptimemonitor.py   # Main CR handlers
│   │   ├── reconciler.py      # Reconciliation logic
│   │   └── startup.py         # Operator configuration
│   ├── clients/               # External API clients
│   │   └── uptime_kuma.py     # Uptime Kuma API wrapper
│   ├── models/                # Pydantic data models
│   │   ├── spec.py           # UptimeMonitor spec models
│   │   └── status.py         # Status and condition models
│   └── utils/                 # Utilities and helpers
│       ├── config.py         # Configuration management
│       └── helpers.py        # Helper functions
├── manifests/                 # Kubernetes manifests
│   ├── crd.yaml              # Custom Resource Definition
│   ├── rbac.yaml             # RBAC configuration
│   └── deployment.yaml       # Production deployment
├── examples/                  # Example UptimeMonitor CRs
├── tests/                     # Comprehensive test suite
│   ├── test_models.py        # Unit tests for models
│   ├── test_integration.py   # Integration tests with minikube
│   ├── test_scenarios.yaml   # Test scenarios
│   └── run_tests.py          # Test runner script
└── main.py                   # Operator entry point
```

## Architecture Flow

```
UptimeMonitor CR → Kopf Handler → Reconciler → Uptime Kuma API
                                      ↓
                              Status Updates ← Monitor State
```

### Key Components

- **Handlers**: Process Kubernetes events (create/update/delete)
- **Reconciler**: Core business logic for syncing desired vs actual state
- **Models**: Type-safe data validation with Pydantic
- **Clients**: External API abstractions
- **Config**: Environment-based configuration management

## UptimeMonitor Specification

```yaml
apiVersion: uptime-operator.dev/v1alpha1
kind: UptimeMonitor
metadata:
  name: my-monitors
  namespace: default
spec:
  enabled: true                      # Master enable/disable switch
  tags: "prod,backend"               # Default tags for all monitors
  monitorGroup: "production-services" # Monitor group for organization (optional)
  endpoints:
    - name: "api-health"             # Unique endpoint name
      url: "https://api.com/health"  # URL to monitor
      tagsOverride: "critical"       # Override default tags (optional)
      monitorGroupOverride: "critical-apis" # Override monitor group (optional)
```

## Environment Configuration

```bash
# Uptime Kuma
UPTIME_KUMA_URL=http://localhost:3001
UPTIME_KUMA_USERNAME=admin
UPTIME_KUMA_PASSWORD=admin

# Kubernetes
CLUSTER_NAME=production
KUBECONFIG=~/.kube/config

# Operator
LOG_LEVEL=INFO
```

## Development

### Setup

```bash
# Install dependencies
uv sync --dev

# Start Uptime Kuma locally
docker-compose up -d

# Install CRD
kubectl apply -f manifests/crd.yaml
```

### Testing

```bash
# Run all tests
./tests/run_tests.py

# Unit tests only
pytest tests/test_models.py -v

# Integration tests (requires minikube)
KUBECONFIG=~/.kube/config.minikube pytest tests/test_integration.py -v
```

### Test Scenarios

The test suite covers all CRUD operations:
- **Create**: New UptimeMonitor with multiple endpoints
- **Update**: URL changes, tag modifications, endpoint addition/removal
- **Delete**: Complete cleanup of monitors
- **Edge cases**: Disabled monitors, validation errors

## Operations

### Monitor Naming
Monitors follow the format: `{namespace}/{cr-name}/{endpoint-name}`

### Tagging Strategy
- Cluster tag (from `CLUSTER_NAME`)
- CRD UID tag (`crd_uid:{uid}`) for association
- User-defined tags (default or per-endpoint override)

### Status Reporting
Each UptimeMonitor reports:
- Overall readiness condition
- Individual monitor statuses
- Sync timestamps and error details

## Deployment

### Local Development
```bash
kopf run main.py --namespace=default
```

### Production
```bash
kubectl apply -f manifests/rbac.yaml
kubectl apply -f manifests/deployment.yaml
```

## Troubleshooting

### Common Issues
- **CRD not found**: `kubectl apply -f manifests/crd.yaml`
- **Connection failed**: Check Uptime Kuma URL and credentials
- **Permission denied**: Verify RBAC configuration

### Debug Mode
```bash
LOG_LEVEL=DEBUG kopf run main.py --verbose
```

### Status Checking
```bash
kubectl get uptimemonitors -A
kubectl describe uptimemonitor my-monitors
```

## Best Practices

- Use meaningful endpoint names
- Implement proper tagging for organization
- Monitor operator logs for issues
- Test changes in development first
- Use separate namespaces for different environments
