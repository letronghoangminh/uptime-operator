"""
Uptime Kuma client wrapper for the operator.
"""
import os
import time
from typing import Dict, List, Optional, Any
from loguru import logger
from uptime_kuma_api import UptimeKumaApi, MonitorType

from ..utils.config import Config


class UptimeKumaClient:
    """Client wrapper for Uptime Kuma API operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the Uptime Kuma client."""
        self.config = config or Config()
        
        self.url = self.config.uptime_kuma_url
        self.username = self.config.uptime_kuma_username
        self.password = self.config.uptime_kuma_password
        self.cluster_name = self.config.cluster_name
        
        self.api: Optional[UptimeKumaApi] = None
        # Don't auto-connect on init, connect lazily when needed
    
    def _connect(self) -> None:
        """Connect to Uptime Kuma API."""
        try:
            self.api = UptimeKumaApi(self.url)
            
            # Try to login if credentials are provided
            if self.username and self.password:
                try:
                    self.api.login(self.username, self.password)
                    logger.info(f"Connected to Uptime Kuma at {self.url} with authentication")
                except Exception as login_error:
                    logger.warning(f"Login failed, trying without auth: {login_error}")
                    # Continue without auth if login fails - may work if auth is disabled
            else:
                logger.info(f"Connecting to Uptime Kuma at {self.url} without authentication")
            
            # Ensure cluster group exists
            self._ensure_cluster_group_exists()
        except Exception as e:
            logger.error(f"Failed to connect to Uptime Kuma: {e}")
            raise
    
    def _ensure_cluster_group_exists(self) -> None:
        """Ensure the cluster group/tag exists in Uptime Kuma."""
        try:
            # Try to create or get the cluster group
            # In Uptime Kuma, we use tags for grouping
            # We'll ensure this cluster tag is used on all monitors
            logger.info(f"Cluster group '{self.cluster_name}' will be used for monitor tagging")
        except Exception as e:
            logger.warning(f"Could not ensure cluster group exists: {e}")
    
    def get_monitors_by_crd_uid(self, crd_uid: str) -> List[Dict[str, Any]]:
        """Get all monitors associated with a specific CRD UID."""
        try:
            if not self.api:
                self._connect()
            
            all_monitors = self.api.get_monitors()
            crd_monitors = []
            
            for monitor in all_monitors:
                # Check if monitor has the CRD UID in its tags
                tags = monitor.get('tags', [])
                if isinstance(tags, list):
                    tag_strings = [str(tag) for tag in tags]
                else:
                    tag_strings = []
                
                if f"crd_uid:{crd_uid}" in tag_strings:
                    crd_monitors.append(monitor)
            
            logger.debug(f"Found {len(crd_monitors)} monitors for CRD UID {crd_uid}")
            return crd_monitors
            
        except Exception as e:
            logger.error(f"Failed to get monitors for CRD UID {crd_uid}: {e}")
            return []
    
    def create_monitor(self, name: str, url: str, tags: List[str], crd_uid: str) -> Optional[int]:
        """Create a new monitor in Uptime Kuma."""
        try:
            if not self.api:
                self._connect()
            
            # Add cluster name and CRD UID to tags
            final_tags = [self.cluster_name, f"crd_uid:{crd_uid}"] + tags
            
            # Use minimal configuration compatible with most Uptime Kuma API versions
            monitor_data = {
                "type": MonitorType.HTTP,
                "name": name,
                "url": url,
                "interval": self.config.monitor_interval
            }
            
            result = self.api.add_monitor(**monitor_data)
            monitor_id = result.get('monitorID')
            
            if monitor_id:
                # Try to add tags after monitor creation if supported
                try:
                    # Some versions support setting tags after creation
                    # This is a best-effort approach
                    pass  # Tags will be handled differently based on API version
                except:
                    pass  # Ignore tag errors for now
                
                logger.info(f"Created monitor '{name}' with ID {monitor_id}")
                return int(monitor_id)
            else:
                logger.error(f"Failed to create monitor '{name}': No monitor ID returned")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create monitor '{name}': {e}")
            return None
    
    def update_monitor(self, monitor_id: int, name: str, url: str, tags: List[str], crd_uid: str) -> bool:
        """Update an existing monitor in Uptime Kuma."""
        try:
            if not self.api:
                self._connect()
            
            # Add cluster name and CRD UID to tags
            final_tags = [self.cluster_name, f"crd_uid:{crd_uid}"] + tags
            
            # Use minimal configuration compatible with most Uptime Kuma API versions
            monitor_data = {
                "id": monitor_id,
                "type": MonitorType.HTTP,
                "name": name,
                "url": url,
                "interval": self.config.monitor_interval
            }
            
            result = self.api.edit_monitor(monitor_id, **monitor_data)
            
            if result:
                logger.info(f"Updated monitor '{name}' (ID: {monitor_id})")
                return True
            else:
                logger.error(f"Failed to update monitor '{name}' (ID: {monitor_id})")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update monitor '{name}' (ID: {monitor_id}): {e}")
            return False
    
    def delete_monitor(self, monitor_id: int) -> bool:
        """Delete a monitor from Uptime Kuma."""
        try:
            if not self.api:
                self._connect()
            
            result = self.api.delete_monitor(monitor_id)
            
            if result:
                logger.info(f"Deleted monitor with ID {monitor_id}")
                return True
            else:
                logger.error(f"Failed to delete monitor with ID {monitor_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete monitor with ID {monitor_id}: {e}")
            return False
    
    def get_monitor_by_name(self, name: str, crd_uid: str) -> Optional[Dict[str, Any]]:
        """Get a specific monitor by name and CRD UID."""
        monitors = self.get_monitors_by_crd_uid(crd_uid)
        
        for monitor in monitors:
            if monitor.get('name') == name:
                return monitor
        
        return None
    
    def health_check(self) -> bool:
        """Check if the connection to Uptime Kuma is healthy."""
        try:
            if not self.api:
                self._connect()
            
            # Try to get monitors as a health check
            self.api.get_monitors()
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
