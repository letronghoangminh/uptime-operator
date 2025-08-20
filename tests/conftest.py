"""Pytest configuration and fixtures for the test suite."""
import os
import pytest
from unittest.mock import Mock, patch
from kubernetes import client, config

from uptime_operator.utils.config import Config
from uptime_operator.clients.uptime_kuma import UptimeKumaClient


@pytest.fixture
def test_config():
    """Test configuration."""
    return Config(
        uptime_kuma_url="http://localhost:3001",
        uptime_kuma_username="admin",
        uptime_kuma_password="admin",
        cluster_name="test-cluster",
        kubeconfig="~/.kube/config.minikube"
    )


@pytest.fixture
def mock_uptime_client():
    """Mock Uptime Kuma client."""
    with patch('uptime_operator.clients.uptime_kuma.UptimeKumaApi') as mock_api:
        mock_instance = Mock()
        mock_api.return_value = mock_instance
        
        # Mock successful login
        mock_instance.login.return_value = True
        
        # Mock get_monitors to return empty list by default
        mock_instance.get_monitors.return_value = []
        
        # Mock successful monitor creation
        mock_instance.add_monitor.return_value = {'monitorID': 123}
        
        # Mock successful monitor update
        mock_instance.edit_monitor.return_value = True
        
        # Mock successful monitor deletion
        mock_instance.delete_monitor.return_value = True
        
        client = UptimeKumaClient()
        yield client, mock_instance


@pytest.fixture
def kubernetes_client():
    """Real Kubernetes client using minikube config."""
    config.load_kube_config(config_file="~/.kube/config.minikube")
    return client.CustomObjectsApi()


@pytest.fixture
def sample_uptimemonitor_spec():
    """Sample UptimeMonitor specification."""
    return {
        "enabled": True,
        "tags": "test,integration",
        "endpoints": [
            {
                "name": "httpbin-get",
                "url": "https://httpbin.org/get"
            },
            {
                "name": "httpbin-status",
                "url": "https://httpbin.org/status/200",
                "tags_overwrite": "test,status"
            }
        ]
    }


@pytest.fixture
def sample_uptimemonitor_cr(sample_uptimemonitor_spec):
    """Complete UptimeMonitor CR."""
    return {
        "apiVersion": "uptime-operator.psycholog1st.dev/v1alpha1",
        "kind": "UptimeMonitor", 
        "metadata": {
            "name": "test-monitor",
            "namespace": "default"
        },
        "spec": sample_uptimemonitor_spec
    }
