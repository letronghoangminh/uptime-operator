"""Pydantic models for UptimeMonitor status."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Condition(BaseModel):
    """Condition represents the current state of the UptimeMonitor."""
    
    type: str = Field(..., description="Type of condition")
    status: str = Field(..., description="Status of condition (True/False/Unknown)")
    lastTransitionTime: datetime = Field(..., description="Last time condition transitioned")
    reason: str = Field(..., description="Machine-readable reason for condition")
    message: str = Field(..., description="Human-readable message for condition")


class MonitorStatus(BaseModel):
    """Status of an individual monitor."""
    
    name: str = Field(..., description="Name of the endpoint")
    url: str = Field(..., description="URL being monitored")
    uptimeKumaId: Optional[int] = Field(None, description="ID in Uptime Kuma")
    status: str = Field(..., description="Current status of the monitor")
    lastSync: datetime = Field(..., description="Last synchronization time")


class UptimeMonitorStatus(BaseModel):
    """Status of UptimeMonitor custom resource."""
    
    conditions: List[Condition] = Field(default_factory=list, description="Current conditions")
    monitors: List[MonitorStatus] = Field(default_factory=list, description="Individual monitor statuses")
    lastSync: Optional[datetime] = Field(None, description="Last synchronization time")
    
    def get_ready_condition(self) -> Optional[Condition]:
        """Get the Ready condition if it exists."""
        for condition in self.conditions:
            if condition.type == "Ready":
                return condition
        return None
    
    def is_ready(self) -> bool:
        """Check if the UptimeMonitor is ready."""
        condition = self.get_ready_condition()
        return condition is not None and condition.status == "True"
    
    def get_failed_monitors(self) -> List[MonitorStatus]:
        """Get list of monitors that failed to sync."""
        return [m for m in self.monitors if 'Failed' in m.status]
