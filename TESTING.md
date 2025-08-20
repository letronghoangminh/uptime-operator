# Testing Guide

This project uses **real integration tests** that connect to actual Kubernetes clusters and Uptime Kuma instances. No mocking or unit tests - only real-world scenarios.

## Environment Configuration

Set these environment variables before running tests:

```bash
# Required: Kubernetes cluster access
export KUBECONFIG=/path/to/your/kubeconfig

# Required: Uptime Kuma instance  
export UPTIME_KUMA_URL=http://localhost:3001

# Optional: Uptime Kuma authentication (if enabled)
export UPTIME_KUMA_USERNAME=admin
export UPTIME_KUMA_PASSWORD=admin

# Optional: Cluster identification
export CLUSTER_NAME=my-cluster
```

## Running Tests

### Option 1: Test Runner Script
```bash
# Set environment and run all tests
export KUBECONFIG=~/.kube/config.minikube
export UPTIME_KUMA_URL=http://localhost:3001
python tests/run_tests.py
```

### Option 2: Direct pytest
```bash
# Run tests directly with pytest
KUBECONFIG=~/.kube/config UPTIME_KUMA_URL=http://localhost:3001 \
  pytest tests/test_real_integration.py -v
```

### Option 3: Local Development
```bash
# Start local Uptime Kuma with docker-compose
docker-compose up -d

# Run tests against local setup
export KUBECONFIG=~/.kube/config.minikube
export UPTIME_KUMA_URL=http://localhost:3001
python tests/run_tests.py
```

## Test Coverage

The integration tests cover:

1. **Kubernetes Connection** - Verifies cluster connectivity
2. **CRD Installation** - Checks UptimeMonitor CRD exists  
3. **CR Lifecycle** - Create, update, delete UptimeMonitor resources
4. **Uptime Kuma Integration** - Real API connections and monitor management
5. **Reconciliation Logic** - End-to-end operator behavior
6. **Error Handling** - Graceful failure scenarios

## Test Structure

```
tests/
├── conftest.py              # Environment-based fixtures
├── test_real_integration.py # 6 integration test cases
├── test_scenarios.yaml      # Sample CR definitions  
└── run_tests.py            # Test runner with setup checks
```

## Prerequisites

- **Kubernetes cluster** with kubectl access
- **Uptime Kuma instance** running and accessible
- **CRD installed** (test runner will install if missing)
- **Python environment** with project dependencies

The tests are designed to be run against real infrastructure to ensure production readiness.
