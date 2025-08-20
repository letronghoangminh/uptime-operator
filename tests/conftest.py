"""Test fixtures for real integration tests."""
import os
import pytest
from kubernetes import client, config

from uptime_operator.utils.config import Config


@pytest.fixture
def k8s_client():
    """Real Kubernetes client using KUBECONFIG env var."""
    kubeconfig_path = os.environ.get('KUBECONFIG')
    if kubeconfig_path:
        config.load_kube_config(config_file=kubeconfig_path)
    else:
        config.load_kube_config()  # Use default config
    return client.CustomObjectsApi()


@pytest.fixture  
def real_config():
    """Real configuration for integration tests using env vars."""
    return Config(
        uptime_kuma_url=os.environ.get('UPTIME_KUMA_URL', 'http://localhost:3001'),
        uptime_kuma_username=os.environ.get('UPTIME_KUMA_USERNAME', ''),
        uptime_kuma_password=os.environ.get('UPTIME_KUMA_PASSWORD', ''),
        cluster_name=os.environ.get('CLUSTER_NAME', 'test-cluster'),
        kubeconfig=os.environ.get('KUBECONFIG')
    )


@pytest.fixture
def sample_uptimemonitor_spec():
    """Sample UptimeMonitor spec for testing."""
    return {
        "enabled": True,
        "tags": "test,integration",
        "monitorGroup": "test-group",
        "endpoints": [
            {
                "name": "httpbin-get",
                "url": "https://httpbin.org/get"
            },
            {
                "name": "httpbin-status",
                "url": "https://httpbin.org/status/200",
                "tagsOverride": "test,status"
            }
        ]
    }
