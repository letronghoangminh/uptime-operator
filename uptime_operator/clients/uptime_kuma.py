"""
Uptime Kuma client wrapper for the operator.
"""
from typing import Dict, List, Optional, Any, Set
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
        self._connect()
        self._ensure_cluster_group_exists()
    
    def _connect(self) -> None:
        """Connect to Uptime Kuma API."""
        try:
            self.api = UptimeKumaApi(self.url)
            
            if self.username and self.password:
                try:
                    self.api.login(self.username, self.password)
                    logger.info(f"Connected to Uptime Kuma at {self.url} with authentication")
                except Exception as login_error:
                    logger.warning(f"Login failed, trying without auth: {login_error}")
            else:
                logger.info(f"Connecting to Uptime Kuma at {self.url} without authentication")
        except Exception as e:
            logger.error(f"Failed to connect to Uptime Kuma: {e}")
            raise
    
    def _ensure_cluster_group_exists(self) -> None:
        """Ensure the cluster group exists for monitor tagging."""
        if self.cluster_name and self.api:
            logger.info(f"Cluster group '{self.cluster_name}' will be used for monitor tagging")
    
    def get_monitors_by_crd_uid(self, crd_uid: str) -> List[Dict[str, Any]]:
        """Get all monitors associated with a specific CRD UID."""
        try:            
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
    
    def _get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """Get existing tag or create a new one."""
        try:
            # Get all tags
            tags = self.api.get_tags()
            
            # Look for existing tag
            for tag in tags:
                if tag.get('name') == tag_name:
                    tag_id = tag.get('id') or tag.get('tag_id')
                    return int(tag_id) if tag_id else None
            
            # Create new tag if not found
            logger.debug(f"Creating new tag: '{tag_name}'")
            try:
                result = self.api.add_tag(name=tag_name, color="#007acc")
                logger.debug(f"Tag creation result: {result}")
                
                # Handle different response formats
                tag_id = None
                if isinstance(result, dict):
                    tag_id = result.get('tagID') or result.get('id') or result.get('tag_id')
                elif isinstance(result, (int, str)):
                    tag_id = result
                
                if tag_id:
                    tag_id = int(tag_id)
                    logger.debug(f"Created tag '{tag_name}' with ID {tag_id}")
                    return tag_id
                else:
                    logger.warning(f"Failed to create tag '{tag_name}': No tag ID in response {result}")
                    return None
                    
            except Exception as create_error:
                logger.warning(f"Failed to create tag '{tag_name}': {create_error}")
                return None
            
        except Exception as e:
            logger.warning(f"Failed to get or create tag '{tag_name}': {e}")
            return None
    
    def _add_single_tag_to_monitor(self, monitor_id: int, tag_name: str) -> bool:
        """Add a single tag to a monitor with error handling."""
        tag_id = self._get_or_create_tag(tag_name)
        if not tag_id:
            logger.debug(f"Could not get/create tag '{tag_name}', skipping tag assignment")
            return False
            
        try:
            result = self.api.add_monitor_tag(tag_id=tag_id, monitor_id=monitor_id)
            logger.debug(f"Added tag '{tag_name}' (ID: {tag_id}) to monitor {monitor_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to add tag '{tag_name}' to monitor {monitor_id}: {e}")
            return False
    
    def _prepare_monitor_tags(self, tags: List[str], cluster_name: str) -> Set[str]:
        """Prepare the complete set of tags for a monitor."""
        all_tags = set()
        
        if cluster_name and cluster_name.strip():
            all_tags.add(cluster_name.strip())

        for tag in tags:
            if tag and tag.strip():
                all_tags.add(tag.strip())
        
        return all_tags
    
    def _add_monitor_tags(self, monitor_id: int, tags: List[str], cluster_name: str) -> None:
        """
        Add tags to a monitor, including automatic cluster group assignment.
        
        Args:
            monitor_id: ID of the monitor to tag
            tags: List of custom tags
            cluster_name: Name of the Kubernetes cluster
        """
        try:
            all_tags = self._prepare_monitor_tags(tags, cluster_name)
            
            if not all_tags:
                logger.debug(f"No tags to add to monitor {monitor_id}")
                return
            
            successful_tags = []
            failed_tags = []
            
            for tag_name in all_tags:
                if self._add_single_tag_to_monitor(monitor_id, tag_name):
                    successful_tags.append(tag_name)
                else:
                    failed_tags.append(tag_name)
            
            if successful_tags:
                logger.debug(f"Successfully added {len(successful_tags)} tags to monitor {monitor_id}: {successful_tags}")
            
            if failed_tags:
                logger.debug(f"Failed to add {len(failed_tags)} tags to monitor {monitor_id}: {failed_tags}")
            
            if not successful_tags and failed_tags:
                logger.warning(f"Could not add any tags to monitor {monitor_id} - this may indicate tag API issues")
                
        except Exception as e:
            logger.warning(f"Failed to add tags to monitor {monitor_id}: {e}")
    
    def _add_custom_tags_to_monitor(self, monitor_id: int, tags: List[str]) -> None:
        """
        Add custom tags to a monitor (no automatic group assignment).
        
        Args:
            monitor_id: ID of the monitor to tag
            tags: List of custom tags
        """
        try:
            successful_tags = []
            for tag_name in tags:
                if tag_name and tag_name.strip():
                    if self._add_single_tag_to_monitor(monitor_id, tag_name.strip()):
                        successful_tags.append(tag_name.strip())
            
            if successful_tags:
                logger.debug(f"Added {len(successful_tags)} custom tags to monitor {monitor_id}: {successful_tags}")
            else:
                logger.debug(f"No custom tags were added to monitor {monitor_id}")
                
        except Exception as e:
            logger.error(f"Failed to add custom tags to monitor {monitor_id}: {e}")
    
    def _remove_all_tags_from_monitor(self, monitor_id: int) -> None:
        """Remove all tags from a monitor."""
        try:
            # Get monitor details to find current tags
            monitor = self.api.get_monitor(monitor_id)
            if not monitor:
                logger.warning(f"Monitor {monitor_id} not found")
                return
            
            current_tags = monitor.get('tags', [])
            if not current_tags:
                logger.debug(f"Monitor {monitor_id} has no tags to remove")
                return
            
            removed_count = 0
            for tag in current_tags:
                tag_id = tag.get('tag_id') if isinstance(tag, dict) else tag
                if tag_id:
                    try:
                        self.api.delete_monitor_tag(tag_id=tag_id, monitor_id=monitor_id)
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove tag {tag_id} from monitor {monitor_id}: {e}")
            
            if removed_count > 0:
                logger.debug(f"Removed {removed_count} tags from monitor {monitor_id}")
                
        except Exception as e:
            logger.error(f"Failed to remove tags from monitor {monitor_id}: {e}")
    
    def get_or_create_monitor_group(self, group_name: str) -> Optional[int]:
        """Get existing monitor group or create a new one."""
        try:
            existing_group = self.get_monitor_group_by_name(group_name)
            if existing_group:
                logger.debug(f"Found existing monitor group '{group_name}' with ID {existing_group['id']}")
                return existing_group['id']
            
            logger.info(f"Creating new monitor group: '{group_name}'")
            group_data = {
                "type": MonitorType.GROUP,
                "name": group_name
            }
            
            result = self.api.add_monitor(**group_data)
            group_id = result.get('monitorID')
            
            if group_id:
                logger.info(f"Created monitor group '{group_name}' with ID {group_id}")
                return int(group_id)
            else:
                logger.error(f"Failed to create monitor group '{group_name}': No group ID returned")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get or create monitor group '{group_name}': {e}")
            return None
    
    def get_monitor_group_by_name(self, group_name: str) -> Optional[Dict[str, Any]]:
        """Get a monitor group by name."""
        try:
            all_monitors = self.api.get_monitors()
            
            for monitor in all_monitors:
                if monitor.get('type') == MonitorType.GROUP and monitor.get('name') == group_name:
                    return monitor
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get monitor group '{group_name}': {e}")
            return None

    def create_monitor(self, name: str, url: str, tags: List[str], crd_uid: str, parent_id: Optional[int] = None) -> Optional[int]:
        """Create a new monitor in Uptime Kuma with proper tagging."""
        try:
            monitor_data = {
                "type": MonitorType.HTTP,
                "name": name,
                "url": url,
                "interval": self.config.monitor_interval,
            }
            
            if parent_id:
                monitor_data["parent"] = parent_id
            
            result = self.api.add_monitor(**monitor_data)
            monitor_id = result.get('monitorID')
            
            if monitor_id:
                monitor_id = int(monitor_id)
                
                # Add tags after monitor creation
                all_tags = tags + [f"crd_uid:{crd_uid}"]
                self._add_monitor_tags(monitor_id, all_tags, self.cluster_name)
                
                logger.info(f"Created monitor '{name}' with ID {monitor_id}")
                return monitor_id
            else:
                logger.error(f"Failed to create monitor '{name}': No monitor ID returned")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create monitor '{name}': {e}")
            return None
    
    def update_monitor(self, monitor_id: int, name: str, url: str, tags: List[str], crd_uid: str, parent_id: Optional[int] = None) -> bool:
        """Update an existing monitor in Uptime Kuma with proper tag management."""
        try:
            monitor_data = {
                "id": monitor_id,
                "type": MonitorType.HTTP,
                "name": name,
                "url": url,
                "interval": self.config.monitor_interval
            }
            
            if parent_id:
                monitor_data["parent"] = parent_id
            
            result = self.api.edit_monitor(monitor_id, **monitor_data)
            
            if result:
                # Remove all existing tags and add the new ones
                self._remove_all_tags_from_monitor(monitor_id)
                
                # Add updated tags
                all_tags = tags + [f"crd_uid:{crd_uid}"]
                self._add_monitor_tags(monitor_id, all_tags, self.cluster_name)
                
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
            self.api.get_monitors()
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
