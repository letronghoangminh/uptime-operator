"""Reconciliation logic for UptimeMonitor resources."""
from datetime import datetime, timezone
from typing import Dict, Any

import kopf
from loguru import logger

from ..clients import UptimeKumaClient
from ..models import UptimeMonitorSpec, UptimeMonitorStatus, MonitorStatus, Condition
from ..utils import Config, build_monitor_name


class UptimeMonitorReconciler:
    """Handles reconciliation of UptimeMonitor resources."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.uptime_client = UptimeKumaClient(self.config)
    
    async def reconcile(self, spec: Dict, status: Dict, meta: Dict, logger: kopf.Logger) -> Dict[str, Any]:
        """
        Reconcile the desired state (spec) with actual state in Uptime Kuma.
        Returns the new status to be updated.
        """
        namespace = meta['namespace']
        cr_name = meta['name']
        crd_uid = meta['uid']
        
        # Parse spec using Pydantic model
        try:
            spec_model = UptimeMonitorSpec(**spec)
        except Exception as e:
            logger.error(f"Invalid spec for {namespace}/{cr_name}: {e}")
            return self._create_error_status(f"Invalid spec: {str(e)}")
        
        # Initialize new status
        new_status = UptimeMonitorStatus(
            conditions=status.get('conditions', []),
            monitors=[],
            lastSync=datetime.now(timezone.utc)
        )
        
        try:
            # Health check Uptime Kuma connection
            if not self.uptime_client.health_check():
                logger.error("Uptime Kuma connection failed")
                return self._create_error_status("Uptime Kuma connection failed").dict()
            
            # If disabled, remove all monitors
            if not spec_model.enabled:
                logger.info(f"UptimeMonitor {namespace}/{cr_name} is disabled, removing all monitors")
                await self._cleanup_monitors(crd_uid)
                
                new_status.conditions = [Condition(
                    type="Ready",
                    status="False",
                    lastTransitionTime=datetime.now(timezone.utc),
                    reason="Disabled",
                    message="UptimeMonitor is disabled"
                )]
                
                return new_status.dict()
            
            # Get current state from Uptime Kuma
            existing_monitors = self.uptime_client.get_monitors_by_crd_uid(crd_uid)
            existing_by_name = {monitor.get('name'): monitor for monitor in existing_monitors}
            
            processed_names = set()
            
            # Process each desired endpoint
            for endpoint in spec_model.endpoints:
                monitor_name = build_monitor_name(namespace, cr_name, endpoint.name)
                processed_names.add(monitor_name)
                
                # Get tags for this endpoint
                endpoint_tags = spec_model.get_endpoint_tags(endpoint)
                
                existing_monitor = existing_by_name.get(monitor_name)
                
                if existing_monitor:
                    # Update existing monitor if needed
                    monitor_id = int(existing_monitor['id'])
                    current_url = existing_monitor.get('url', '')
                    current_tags = existing_monitor.get('tags', [])
                    
                    # Check if update is needed
                    expected_tags = [self.uptime_client.cluster_name, f"crd_uid:{crd_uid}"] + endpoint_tags
                    
                    needs_update = (
                        current_url != endpoint.url or
                        set(str(tag) for tag in current_tags) != set(expected_tags)
                    )
                    
                    if needs_update:
                        logger.info(f"Updating monitor '{monitor_name}'")
                        success = self.uptime_client.update_monitor(
                            monitor_id, monitor_name, endpoint.url, endpoint_tags, crd_uid
                        )
                        
                        status_value = "Updated" if success else "UpdateFailed"
                    else:
                        # Monitor is up to date
                        status_value = "Ready"
                    
                    new_status.monitors.append(MonitorStatus(
                        name=endpoint.name,
                        url=endpoint.url,
                        uptimeKumaId=monitor_id,
                        status=status_value,
                        lastSync=datetime.now(timezone.utc)
                    ))
                    
                else:
                    # Create new monitor
                    logger.info(f"Creating monitor '{monitor_name}'")
                    monitor_id = self.uptime_client.create_monitor(
                        monitor_name, endpoint.url, endpoint_tags, crd_uid
                    )
                    
                    if monitor_id:
                        new_status.monitors.append(MonitorStatus(
                            name=endpoint.name,
                            url=endpoint.url,
                            uptimeKumaId=monitor_id,
                            status="Created",
                            lastSync=datetime.now(timezone.utc)
                        ))
                    else:
                        new_status.monitors.append(MonitorStatus(
                            name=endpoint.name,
                            url=endpoint.url,
                            uptimeKumaId=None,
                            status="CreateFailed",
                            lastSync=datetime.now(timezone.utc)
                        ))
            
            # Delete monitors that are no longer in the spec
            for monitor_name, monitor in existing_by_name.items():
                if monitor_name not in processed_names:
                    logger.info(f"Deleting monitor '{monitor_name}' (no longer in spec)")
                    monitor_id = int(monitor['id'])
                    self.uptime_client.delete_monitor(monitor_id)
            
            # Update condition based on results
            failed_monitors = new_status.get_failed_monitors()
            if failed_monitors:
                new_status.conditions = [Condition(
                    type="Ready",
                    status="False",
                    lastTransitionTime=datetime.now(timezone.utc),
                    reason="SyncFailed",
                    message=f'{len(failed_monitors)} monitor(s) failed to sync'
                )]
            else:
                new_status.conditions = [Condition(
                    type="Ready",
                    status="True",
                    lastTransitionTime=datetime.now(timezone.utc),
                    reason="SyncSuccessful",
                    message=f'All {len(new_status.monitors)} monitor(s) synced successfully'
                )]
            
        except Exception as e:
            logger.error(f"Reconciliation failed for {namespace}/{cr_name}: {e}")
            return self._create_error_status(f"Reconciliation failed: {str(e)}").dict()
        
        return new_status.dict()
    
    async def _cleanup_monitors(self, crd_uid: str) -> None:
        """Clean up all monitors for a CRD."""
        existing_monitors = self.uptime_client.get_monitors_by_crd_uid(crd_uid)
        
        for monitor in existing_monitors:
            monitor_id = monitor.get('id')
            if monitor_id:
                self.uptime_client.delete_monitor(int(monitor_id))
    
    def _create_error_status(self, message: str) -> UptimeMonitorStatus:
        """Create an error status."""
        return UptimeMonitorStatus(
            conditions=[Condition(
                type="Ready",
                status="False", 
                lastTransitionTime=datetime.now(timezone.utc),
                reason="ReconciliationError",
                message=message
            )],
            monitors=[],
            lastSync=datetime.now(timezone.utc)
        )
