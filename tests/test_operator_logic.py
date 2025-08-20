"""Test operator logic without requiring live Kubernetes cluster."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from uptime_operator.handlers.reconciler import UptimeMonitorReconciler
from uptime_operator.models import UptimeMonitorSpec, EndpointSpec
from uptime_operator.utils.config import Config


class TestOperatorLogic:
    """Test core operator reconciliation logic."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        return Config(
            uptime_kuma_url="http://localhost:3001",
            uptime_kuma_username="admin",
            uptime_kuma_password="admin",
            cluster_name="test-cluster",
        )
    
    @pytest.fixture
    def mock_uptime_client(self):
        """Mock Uptime Kuma client."""
        client = Mock()
        client.health_check.return_value = True
        client.cluster_name = "test-cluster"
        client.get_monitors_by_crd_uid.return_value = []
        client.create_monitor.return_value = 123
        client.update_monitor.return_value = True
        client.delete_monitor.return_value = True
        return client
    
    @pytest.fixture
    def reconciler(self, mock_config):
        """Reconciler with mocked dependencies."""
        with patch('uptime_operator.handlers.reconciler.UptimeKumaClient') as mock_client_class:
            reconciler = UptimeMonitorReconciler(mock_config)
            reconciler.uptime_client = Mock()
            reconciler.uptime_client.health_check.return_value = True
            reconciler.uptime_client.cluster_name = "test-cluster"
            reconciler.uptime_client.get_monitors_by_crd_uid.return_value = []
            reconciler.uptime_client.create_monitor.return_value = 123
            reconciler.uptime_client.update_monitor.return_value = True
            reconciler.uptime_client.delete_monitor.return_value = True
            yield reconciler
    
    @pytest.mark.asyncio
    async def test_create_monitor_scenario(self, reconciler):
        """Test creating new monitors."""
        spec = {
            "enabled": True,
            "tags": "test,integration",
            "endpoints": [
                {"name": "httpbin-get", "url": "https://httpbin.org/get"},
                {"name": "httpbin-status", "url": "https://httpbin.org/status/200"}
            ]
        }
        
        meta = {
            'namespace': 'default',
            'name': 'test-monitor',
            'uid': 'test-uid-123'
        }
        
        status = await reconciler.reconcile(spec, {}, meta, Mock())
        
        # Verify status
        assert 'conditions' in status
        assert 'monitors' in status
        assert len(status['monitors']) == 2
        
        # Check individual monitors
        monitor_names = [m['name'] for m in status['monitors']]
        assert 'httpbin-get' in monitor_names
        assert 'httpbin-status' in monitor_names
        
        # Verify calls were made
        assert reconciler.uptime_client.create_monitor.call_count == 2
    
    @pytest.mark.asyncio
    async def test_update_url_scenario(self, reconciler):
        """Test updating monitor URLs."""
        # Mock existing monitor
        existing_monitor = {
            'id': 123,
            'name': 'default/test-monitor/httpbin-get',
            'url': 'https://httpbin.org/get',
            'tags': ['test-cluster', 'crd_uid:test-uid-123', 'test']
        }
        reconciler.uptime_client.get_monitors_by_crd_uid.return_value = [existing_monitor]
        
        spec = {
            "enabled": True,
            "tags": "test,updated",
            "endpoints": [
                {"name": "httpbin-get", "url": "https://httpbin.org/status/200"}  # Changed URL
            ]
        }
        
        meta = {
            'namespace': 'default',
            'name': 'test-monitor',
            'uid': 'test-uid-123'
        }
        
        status = await reconciler.reconcile(spec, {}, meta, Mock())
        
        # Verify update was called
        reconciler.uptime_client.update_monitor.assert_called_once()
        
        # Check status reflects update
        assert len(status['monitors']) == 1
        assert status['monitors'][0]['status'] == 'Updated'
        assert status['monitors'][0]['url'] == 'https://httpbin.org/status/200'
    
    @pytest.mark.asyncio
    async def test_add_endpoint_scenario(self, reconciler):
        """Test adding new endpoints to existing monitor."""
        # Mock existing monitor
        existing_monitor = {
            'id': 123,
            'name': 'default/test-monitor/endpoint1',
            'url': 'https://httpbin.org/get',
            'tags': ['test-cluster', 'crd_uid:test-uid-123', 'test']
        }
        reconciler.uptime_client.get_monitors_by_crd_uid.return_value = [existing_monitor]
        
        spec = {
            "enabled": True,
            "tags": "test",
            "endpoints": [
                {"name": "endpoint1", "url": "https://httpbin.org/get"},
                {"name": "endpoint2", "url": "https://httpbin.org/status/200"}  # New endpoint
            ]
        }
        
        meta = {
            'namespace': 'default',
            'name': 'test-monitor',
            'uid': 'test-uid-123'
        }
        
        status = await reconciler.reconcile(spec, {}, meta, Mock())
        
        # Should create one new monitor
        reconciler.uptime_client.create_monitor.assert_called_once()
        
        # Check status has both monitors
        assert len(status['monitors']) == 2
        monitor_names = [m['name'] for m in status['monitors']]
        assert 'endpoint1' in monitor_names
        assert 'endpoint2' in monitor_names
    
    @pytest.mark.asyncio
    async def test_disable_monitoring_scenario(self, reconciler):
        """Test disabling monitoring (enabled: false)."""
        # Mock existing monitors
        existing_monitors = [
            {
                'id': 123,
                'name': 'default/test-monitor/endpoint1',
                'url': 'https://httpbin.org/get',
                'tags': ['test-cluster', 'crd_uid:test-uid-123', 'test']
            },
            {
                'id': 124,
                'name': 'default/test-monitor/endpoint2',
                'url': 'https://httpbin.org/status/200',
                'tags': ['test-cluster', 'crd_uid:test-uid-123', 'test']
            }
        ]
        reconciler.uptime_client.get_monitors_by_crd_uid.return_value = existing_monitors
        
        spec = {
            "enabled": False,  # Disabled
            "tags": "test",
            "endpoints": [
                {"name": "endpoint1", "url": "https://httpbin.org/get"},
                {"name": "endpoint2", "url": "https://httpbin.org/status/200"}
            ]
        }
        
        meta = {
            'namespace': 'default',
            'name': 'test-monitor',
            'uid': 'test-uid-123'
        }
        
        status = await reconciler.reconcile(spec, {}, meta, Mock())
        
        # Should delete both existing monitors
        assert reconciler.uptime_client.delete_monitor.call_count == 2
        
        # Status should show disabled
        assert len(status['monitors']) == 0
        assert status['conditions'][0]['reason'] == 'Disabled'
        assert status['conditions'][0]['status'] == 'False'
    
    @pytest.mark.asyncio
    async def test_tags_override_scenario(self, reconciler):
        """Test per-endpoint tag overrides."""
        spec = {
            "enabled": True,
            "tags": "default,tag",
            "endpoints": [
                {"name": "normal", "url": "https://httpbin.org/get"},
                {"name": "critical", "url": "https://httpbin.org/status/200", 
                 "tags_overwrite": "critical,override"}
            ]
        }
        
        meta = {
            'namespace': 'default',
            'name': 'test-monitor',
            'uid': 'test-uid-123'
        }
        
        status = await reconciler.reconcile(spec, {}, meta, Mock())
        
        # Verify both monitors created with different tags
        assert reconciler.uptime_client.create_monitor.call_count == 2
        
        calls = reconciler.uptime_client.create_monitor.call_args_list
        
        # First call (normal endpoint) should use default tags
        normal_call = calls[0]
        assert normal_call[0][2] == ['default', 'tag']  # tags parameter
        
        # Second call (critical endpoint) should use overridden tags
        critical_call = calls[1]
        assert critical_call[0][2] == ['critical', 'override']  # tags parameter
    
    @pytest.mark.asyncio
    async def test_delete_scenario(self, reconciler):
        """Test cleanup when monitors are deleted."""
        # Mock existing monitors
        existing_monitors = [
            {'id': 123, 'name': 'monitor1'},
            {'id': 124, 'name': 'monitor2'}
        ]
        reconciler.uptime_client.get_monitors_by_crd_uid.return_value = existing_monitors
        
        crd_uid = 'test-uid-123'
        
        # Test cleanup
        await reconciler._cleanup_monitors(crd_uid)
        
        # Should delete both monitors
        assert reconciler.uptime_client.delete_monitor.call_count == 2
        reconciler.uptime_client.delete_monitor.assert_any_call(123)
        reconciler.uptime_client.delete_monitor.assert_any_call(124)
    
    @pytest.mark.asyncio
    async def test_error_handling_scenario(self, reconciler):
        """Test error handling in reconciliation."""
        # Mock client failure
        reconciler.uptime_client.health_check.return_value = False
        
        spec = {
            "enabled": True,
            "endpoints": [{"name": "test", "url": "https://httpbin.org/get"}]
        }
        
        meta = {'namespace': 'default', 'name': 'test', 'uid': 'test-uid'}
        
        status = await reconciler.reconcile(spec, {}, meta, Mock())
        
        # Should return empty status due to health check failure
        assert len(status['monitors']) == 0
    
    def test_spec_validation(self):
        """Test spec validation with various scenarios."""
        # Valid spec
        valid_spec = UptimeMonitorSpec(
            enabled=True,
            tags="test,validation",
            endpoints=[
                EndpointSpec(name="test", url="https://httpbin.org/get")
            ]
        )
        assert valid_spec.enabled is True
        assert len(valid_spec.endpoints) == 1
        
        # Test tag parsing
        assert valid_spec.parse_default_tags() == ["test", "validation"]
        
        # Test endpoint tag overrides
        endpoint_with_override = EndpointSpec(
            name="override-test",
            url="https://httpbin.org/get",
            tags_overwrite="override,tags"
        )
        
        override_spec = UptimeMonitorSpec(
            enabled=True,
            tags="default,tags",
            endpoints=[endpoint_with_override]
        )
        
        # Should return overridden tags
        tags = override_spec.get_endpoint_tags(endpoint_with_override)
        assert tags == ["override", "tags"]
