"""Integration tests using real Kubernetes (minikube) cluster."""
import pytest
import time
import asyncio
from kubernetes import client
from kubernetes.client import ApiException

from uptime_operator.handlers.reconciler import UptimeMonitorReconciler
from uptime_operator.utils.config import Config


class TestIntegrationCRUD:
    """Integration tests for CRUD operations."""
    
    @pytest.fixture
    def k8s_client(self):
        """Kubernetes client configured for minikube."""
        from kubernetes import config
        config.load_kube_config(config_file="~/.kube/config.minikube")
        return client.CustomObjectsApi()
    
    @pytest.fixture
    def reconciler(self):
        """Real reconciler instance."""
        test_config = Config(kubeconfig="~/.kube/config.minikube")
        return UptimeMonitorReconciler(test_config)
    
    def create_uptimemonitor(self, k8s_client, name, spec, namespace="default"):
        """Helper to create UptimeMonitor CR."""
        cr = {
            "apiVersion": "uptime-operator.psycholog1st.dev/v1alpha1",
            "kind": "UptimeMonitor",
            "metadata": {
                "name": name,
                "namespace": namespace
            },
            "spec": spec
        }
        
        return k8s_client.create_namespaced_custom_object(
            group="uptime-operator.psycholog1st.dev",
            version="v1alpha1",
            namespace=namespace,
            plural="uptimemonitors",
            body=cr
        )
    
    def get_uptimemonitor(self, k8s_client, name, namespace="default"):
        """Helper to get UptimeMonitor CR."""
        try:
            return k8s_client.get_namespaced_custom_object(
                group="uptime-operator.psycholog1st.dev",
                version="v1alpha1",
                namespace=namespace,
                plural="uptimemonitors",
                name=name
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise
    
    def delete_uptimemonitor(self, k8s_client, name, namespace="default"):
        """Helper to delete UptimeMonitor CR."""
        try:
            k8s_client.delete_namespaced_custom_object(
                group="uptime-operator.psycholog1st.dev",
                version="v1alpha1",
                namespace=namespace,
                plural="uptimemonitors",
                name=name
            )
        except ApiException as e:
            if e.status != 404:
                raise
    
    def update_uptimemonitor(self, k8s_client, name, spec, namespace="default"):
        """Helper to update UptimeMonitor CR."""
        # Get current CR
        cr = self.get_uptimemonitor(k8s_client, name, namespace)
        if not cr:
            raise ValueError(f"UptimeMonitor {name} not found")
        
        # Update spec
        cr['spec'] = spec
        
        return k8s_client.replace_namespaced_custom_object(
            group="uptime-operator.psycholog1st.dev",
            version="v1alpha1",
            namespace=namespace,
            plural="uptimemonitors",
            name=name,
            body=cr
        )
    
    @pytest.mark.asyncio
    async def test_create_uptimemonitor(self, k8s_client, reconciler):
        """Test creating a new UptimeMonitor."""
        test_name = "test-create-monitor"
        
        # Clean up any existing resource
        self.delete_uptimemonitor(k8s_client, test_name)
        time.sleep(1)
        
        spec = {
            "enabled": True,
            "tags": "test,create",
            "endpoints": [
                {
                    "name": "httpbin-get",
                    "url": "https://httpbin.org/get"
                }
            ]
        }
        
        try:
            # Create CR
            cr = self.create_uptimemonitor(k8s_client, test_name, spec)
            assert cr['metadata']['name'] == test_name
            
            # Test reconciliation
            meta = {
                'namespace': 'default',
                'name': test_name,
                'uid': cr['metadata']['uid']
            }
            
            status = await reconciler.reconcile(spec, {}, meta, None)
            
            # Verify status
            assert 'conditions' in status
            assert 'monitors' in status
            assert len(status['monitors']) == 1
            assert status['monitors'][0]['name'] == 'httpbin-get'
            assert status['monitors'][0]['url'] == 'https://httpbin.org/get'
            
        finally:
            # Clean up
            self.delete_uptimemonitor(k8s_client, test_name)
    
    @pytest.mark.asyncio
    async def test_update_uptimemonitor_url(self, k8s_client, reconciler):
        """Test updating UptimeMonitor URL."""
        test_name = "test-update-url"
        
        # Clean up any existing resource
        self.delete_uptimemonitor(k8s_client, test_name)
        time.sleep(1)
        
        initial_spec = {
            "enabled": True,
            "tags": "test,update",
            "endpoints": [
                {
                    "name": "httpbin-endpoint",
                    "url": "https://httpbin.org/get"
                }
            ]
        }
        
        updated_spec = {
            "enabled": True,
            "tags": "test,update", 
            "endpoints": [
                {
                    "name": "httpbin-endpoint",
                    "url": "https://httpbin.org/status/200"  # Changed URL
                }
            ]
        }
        
        try:
            # Create CR
            cr = self.create_uptimemonitor(k8s_client, test_name, initial_spec)
            meta = {
                'namespace': 'default',
                'name': test_name,
                'uid': cr['metadata']['uid']
            }
            
            # Initial reconciliation
            await reconciler.reconcile(initial_spec, {}, meta, None)
            
            # Update CR
            updated_cr = self.update_uptimemonitor(k8s_client, test_name, updated_spec)
            
            # Test reconciliation with updated spec
            status = await reconciler.reconcile(updated_spec, {}, meta, None)
            
            # Verify URL was updated
            assert len(status['monitors']) == 1
            assert status['monitors'][0]['url'] == 'https://httpbin.org/status/200'
            
        finally:
            # Clean up
            self.delete_uptimemonitor(k8s_client, test_name)
    
    @pytest.mark.asyncio
    async def test_update_uptimemonitor_tags(self, k8s_client, reconciler):
        """Test updating UptimeMonitor tags."""
        test_name = "test-update-tags"
        
        # Clean up any existing resource
        self.delete_uptimemonitor(k8s_client, test_name)
        time.sleep(1)
        
        initial_spec = {
            "enabled": True,
            "tags": "test,initial",
            "endpoints": [
                {
                    "name": "httpbin-endpoint",
                    "url": "https://httpbin.org/get"
                }
            ]
        }
        
        updated_spec = {
            "enabled": True,
            "tags": "test,updated,new-tag",  # Changed tags
            "endpoints": [
                {
                    "name": "httpbin-endpoint",
                    "url": "https://httpbin.org/get"
                }
            ]
        }
        
        try:
            # Create CR
            cr = self.create_uptimemonitor(k8s_client, test_name, initial_spec)
            meta = {
                'namespace': 'default',
                'name': test_name,
                'uid': cr['metadata']['uid']
            }
            
            # Initial reconciliation
            await reconciler.reconcile(initial_spec, {}, meta, None)
            
            # Update CR
            updated_cr = self.update_uptimemonitor(k8s_client, test_name, updated_spec)
            
            # Test reconciliation with updated spec
            status = await reconciler.reconcile(updated_spec, {}, meta, None)
            
            # Verify the monitor was updated (should show Updated status)
            assert len(status['monitors']) == 1
            # The status should indicate an update occurred
            assert status['monitors'][0]['status'] in ['Updated', 'Ready']
            
        finally:
            # Clean up
            self.delete_uptimemonitor(k8s_client, test_name)
    
    @pytest.mark.asyncio 
    async def test_update_uptimemonitor_add_endpoint(self, k8s_client, reconciler):
        """Test adding an endpoint to UptimeMonitor."""
        test_name = "test-add-endpoint"
        
        # Clean up any existing resource
        self.delete_uptimemonitor(k8s_client, test_name)
        time.sleep(1)
        
        initial_spec = {
            "enabled": True,
            "tags": "test,add",
            "endpoints": [
                {
                    "name": "endpoint1",
                    "url": "https://httpbin.org/get"
                }
            ]
        }
        
        updated_spec = {
            "enabled": True,
            "tags": "test,add",
            "endpoints": [
                {
                    "name": "endpoint1",
                    "url": "https://httpbin.org/get"
                },
                {
                    "name": "endpoint2",  # New endpoint
                    "url": "https://httpbin.org/status/200"
                }
            ]
        }
        
        try:
            # Create CR
            cr = self.create_uptimemonitor(k8s_client, test_name, initial_spec)
            meta = {
                'namespace': 'default',
                'name': test_name,
                'uid': cr['metadata']['uid']
            }
            
            # Initial reconciliation
            initial_status = await reconciler.reconcile(initial_spec, {}, meta, None)
            assert len(initial_status['monitors']) == 1
            
            # Update CR 
            updated_cr = self.update_uptimemonitor(k8s_client, test_name, updated_spec)
            
            # Test reconciliation with updated spec
            status = await reconciler.reconcile(updated_spec, {}, meta, None)
            
            # Verify both endpoints are present
            assert len(status['monitors']) == 2
            monitor_names = [m['name'] for m in status['monitors']]
            assert 'endpoint1' in monitor_names
            assert 'endpoint2' in monitor_names
            
        finally:
            # Clean up
            self.delete_uptimemonitor(k8s_client, test_name)
    
    @pytest.mark.asyncio
    async def test_delete_uptimemonitor(self, k8s_client, reconciler):
        """Test deleting UptimeMonitor."""
        test_name = "test-delete-monitor"
        
        # Clean up any existing resource
        self.delete_uptimemonitor(k8s_client, test_name)
        time.sleep(1)
        
        spec = {
            "enabled": True,
            "tags": "test,delete",
            "endpoints": [
                {
                    "name": "httpbin-endpoint",
                    "url": "https://httpbin.org/get"
                }
            ]
        }
        
        # Create CR
        cr = self.create_uptimemonitor(k8s_client, test_name, spec)
        meta = {
            'namespace': 'default',
            'name': test_name,
            'uid': cr['metadata']['uid']
        }
        
        # Initial reconciliation
        await reconciler.reconcile(spec, {}, meta, None)
        
        # Verify monitors exist in Uptime Kuma
        monitors = reconciler.uptime_client.get_monitors_by_crd_uid(meta['uid'])
        assert len(monitors) > 0
        
        # Test cleanup
        await reconciler._cleanup_monitors(meta['uid'])
        
        # Verify monitors were deleted
        monitors_after = reconciler.uptime_client.get_monitors_by_crd_uid(meta['uid'])
        assert len(monitors_after) == 0
        
        # Delete the CR
        self.delete_uptimemonitor(k8s_client, test_name)
    
    @pytest.mark.asyncio
    async def test_disable_uptimemonitor(self, k8s_client, reconciler):
        """Test disabling UptimeMonitor."""
        test_name = "test-disable-monitor"
        
        # Clean up any existing resource
        self.delete_uptimemonitor(k8s_client, test_name)
        time.sleep(1)
        
        enabled_spec = {
            "enabled": True,
            "tags": "test,disable",
            "endpoints": [
                {
                    "name": "httpbin-endpoint",
                    "url": "https://httpbin.org/get"
                }
            ]
        }
        
        disabled_spec = {
            "enabled": False,  # Disabled
            "tags": "test,disable",
            "endpoints": [
                {
                    "name": "httpbin-endpoint",
                    "url": "https://httpbin.org/get"
                }
            ]
        }
        
        try:
            # Create CR
            cr = self.create_uptimemonitor(k8s_client, test_name, enabled_spec)
            meta = {
                'namespace': 'default',
                'name': test_name,
                'uid': cr['metadata']['uid']
            }
            
            # Initial reconciliation (enabled)
            enabled_status = await reconciler.reconcile(enabled_spec, {}, meta, None)
            assert len(enabled_status['monitors']) == 1
            
            # Update to disabled
            updated_cr = self.update_uptimemonitor(k8s_client, test_name, disabled_spec)
            
            # Test reconciliation with disabled spec
            disabled_status = await reconciler.reconcile(disabled_spec, {}, meta, None)
            
            # Verify monitors are removed and status shows disabled
            assert len(disabled_status['monitors']) == 0
            assert disabled_status['conditions'][0]['reason'] == 'Disabled'
            
            # Verify no monitors exist in Uptime Kuma
            monitors = reconciler.uptime_client.get_monitors_by_crd_uid(meta['uid'])
            assert len(monitors) == 0
            
        finally:
            # Clean up
            self.delete_uptimemonitor(k8s_client, test_name)
