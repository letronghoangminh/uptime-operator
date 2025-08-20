"""Data models for the Uptime Operator."""
from .spec import UptimeMonitorSpec, EndpointSpec
from .status import UptimeMonitorStatus, MonitorStatus, Condition

__all__ = [
    "UptimeMonitorSpec",
    "EndpointSpec", 
    "UptimeMonitorStatus",
    "MonitorStatus",
    "Condition"
]
