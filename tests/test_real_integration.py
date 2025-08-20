"""Real integration tests using live minikube and Uptime Kuma."""
import os
import pytest
import time
import asyncio
from unittest.mock import patch
from kubernetes import client, config
from kubernetes.client import ApiException

from uptime_operator.handlers.reconciler import UptimeMonitorReconciler
from uptime_operator.utils.config import Config





def create_uptimemonitor(k8s_client, name, spec, namespace="default"):
    """Helper to create UptimeMonitor CR."""
    cr = {
        "apiVersion": "uptime-operator.dev/v1alpha1",
        "kind": "UptimeMonitor",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": spec
    }
    
    return k8s_client.create_namespaced_custom_object(
        group="uptime-operator.dev",
        version="v1alpha1",
        namespace=namespace,
        plural="uptimemonitors",
        body=cr
    )


def get_uptimemonitor(k8s_client, name, namespace="default"):
    """Helper to get UptimeMonitor CR."""
    try:
        return k8s_client.get_namespaced_custom_object(
            group="uptime-operator.dev",
            version="v1alpha1",
            namespace=namespace,
            plural="uptimemonitors",
            name=name
        )
    except ApiException as e:
        if e.status == 404:
            return None
        raise


def delete_uptimemonitor(k8s_client, name, namespace="default"):
    """Helper to delete UptimeMonitor CR."""
    try:
        k8s_client.delete_namespaced_custom_object(
            group="uptime-operator.dev",
            version="v1alpha1",
            namespace=namespace,
            plural="uptimemonitors",
            name=name
        )
    except ApiException as e:
        if e.status != 404:
            raise


class TestRealIntegration:
    """Integration tests with real minikube and Uptime Kuma."""
    
    def test_kubernetes_connection(self, k8s_client):
        """Test that we can connect to minikube."""
        # Try to list namespaces
        core_api = client.CoreV1Api()
        namespaces = core_api.list_namespace()
        assert len(namespaces.items) > 0
        print(f"✅ Connected to Kubernetes, found {len(namespaces.items)} namespaces")
    
    def test_crd_exists(self, k8s_client):
        """Test that the UptimeMonitor CRD exists."""
        api_client = client.ApiextensionsV1Api()
        try:
            crd = api_client.read_custom_resource_definition(
                "uptimemonitors.uptime-operator.dev"
            )
            assert crd.metadata.name == "uptimemonitors.uptime-operator.dev"
            print("✅ UptimeMonitor CRD exists and is accessible")
        except ApiException as e:
            pytest.fail(f"CRD not found: {e}")
    
    def test_create_uptimemonitor_cr(self, k8s_client):
        """Test creating UptimeMonitor CR in Kubernetes."""
        test_name = "test-k8s-integration"
        
        # Clean up any existing resource
        delete_uptimemonitor(k8s_client, test_name)
        time.sleep(1)
        
        spec = {
            "enabled": True,
            "tags": "test,k8s-integration",
            "endpoints": [
                {
                    "name": "httpbin-test",
                    "url": "https://httpbin.org/get"
                }
            ]
        }
        
        try:
            # Create CR
            cr = create_uptimemonitor(k8s_client, test_name, spec)
            assert cr['metadata']['name'] == test_name
            print(f"✅ Created UptimeMonitor CR: {test_name}")
            
            # Verify it exists
            retrieved_cr = get_uptimemonitor(k8s_client, test_name)
            assert retrieved_cr is not None
            assert retrieved_cr['spec']['enabled'] is True
            print("✅ CR can be retrieved and has correct spec")
            
        finally:
            # Cleanup
            delete_uptimemonitor(k8s_client, test_name)
            print("✅ Cleanup completed")
    
    def test_uptime_kuma_connection_attempt(self, real_config):
        """Test connection attempt to Uptime Kuma (may fail if auth required)."""
        from uptime_operator.clients.uptime_kuma import UptimeKumaClient
        
        try:
            client = UptimeKumaClient(real_config)
            # Try to connect (this may fail if auth is required)
            health_status = client.health_check()
            if health_status:
                print("✅ Successfully connected to Uptime Kuma")
            else:
                print("⚠️ Uptime Kuma connection failed (may need proper auth setup)")
        except Exception as e:
            print(f"⚠️ Uptime Kuma connection error: {e}")
            # This is expected if auth is not properly set up
    
    @pytest.mark.asyncio
    async def test_reconciler_with_failed_uptime_kuma(self, k8s_client, real_config):
        """Test reconciler graceful handling when Uptime Kuma is not accessible."""
        # This tests error handling when Uptime Kuma connection fails
        
        # Mock a failing Uptime Kuma client
        with patch('uptime_operator.clients.uptime_kuma.UptimeKumaClient') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.health_check.return_value = False  # Simulate connection failure
            
            reconciler = UptimeMonitorReconciler(real_config)
            
            spec = {
                "enabled": True,
                "tags": "test,reconciler",
                "endpoints": [
                    {"name": "test-endpoint", "url": "https://httpbin.org/get"}
                ]
            }
            
            meta = {
                'namespace': 'default',
                'name': 'test-reconciler',
                'uid': 'test-uid-reconciler'
            }
            
            # This should handle the failed connection gracefully
            from unittest.mock import Mock
            mock_logger = Mock()
            status = await reconciler.reconcile(spec, {}, meta, mock_logger)
            
            # Should return empty status due to connection failure
            assert 'conditions' in status
            assert 'monitors' in status
            assert len(status['monitors']) == 0
            print("✅ Reconciler handles Uptime Kuma connection failure gracefully")
    
    def test_full_cr_lifecycle(self, k8s_client):
        """Test complete CRUD lifecycle of UptimeMonitor CRs."""
        test_name = "test-lifecycle"
        
        # Clean up any existing resource
        delete_uptimemonitor(k8s_client, test_name)
        time.sleep(1)
        
        # Create
        create_spec = {
            "enabled": True,
            "tags": "test,lifecycle",
            "endpoints": [
                {"name": "endpoint1", "url": "https://httpbin.org/get"}
            ]
        }
        
        cr = create_uptimemonitor(k8s_client, test_name, create_spec)
        original_uid = cr['metadata']['uid']
        print("✅ CREATE: UptimeMonitor CR created")
        
        # Read
        retrieved_cr = get_uptimemonitor(k8s_client, test_name)
        assert retrieved_cr['metadata']['uid'] == original_uid
        print("✅ READ: UptimeMonitor CR retrieved successfully")
        
        # Update
        update_spec = {
            "enabled": True,
            "tags": "test,lifecycle,updated",
            "endpoints": [
                {"name": "endpoint1", "url": "https://httpbin.org/get"},
                {"name": "endpoint2", "url": "https://httpbin.org/status/200"}  # Added endpoint
            ]
        }
        
        # Update by replacing the CR
        updated_cr = {
            "apiVersion": "uptime-operator.dev/v1alpha1",
            "kind": "UptimeMonitor",
            "metadata": {
                "name": test_name,
                "namespace": "default",
                "resourceVersion": retrieved_cr['metadata']['resourceVersion']
            },
            "spec": update_spec
        }
        
        updated_result = k8s_client.replace_namespaced_custom_object(
            group="uptime-operator.dev",
            version="v1alpha1",
            namespace="default",
            plural="uptimemonitors",
            name=test_name,
            body=updated_cr
        )
        
        # Verify update
        final_cr = get_uptimemonitor(k8s_client, test_name)
        assert len(final_cr['spec']['endpoints']) == 2
        assert "updated" in final_cr['spec']['tags']
        print("✅ UPDATE: UptimeMonitor CR updated successfully")
        
        # Delete
        delete_uptimemonitor(k8s_client, test_name)
        time.sleep(1)
        
        # Verify deletion
        deleted_cr = get_uptimemonitor(k8s_client, test_name)
        assert deleted_cr is None
        print("✅ DELETE: UptimeMonitor CR deleted successfully")
        
        print("🎉 Full CRUD lifecycle test completed successfully!")


if __name__ == "__main__":
    # Run tests directly
    import os
    os.environ['KUBECONFIG'] = os.path.expanduser('~/.kube/config.minikube')
    pytest.main([__file__, "-v", "-s"])
