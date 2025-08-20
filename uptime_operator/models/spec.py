"""Pydantic models for UptimeMonitor specifications."""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class EndpointSpec(BaseModel):
    """Specification for a single endpoint to monitor."""
    
    name: str = Field(..., description="Unique name for the endpoint within this CR")
    url: str = Field(..., description="Full URL to monitor")
    tags_overwrite: Optional[str] = Field(None, description="Comma-separated tags to replace default tags")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()


class UptimeMonitorSpec(BaseModel):
    """Specification for UptimeMonitor custom resource."""
    
    enabled: bool = Field(..., description="Master switch to enable/disable monitoring")
    tags: Optional[str] = Field(None, description="Comma-separated default tags for all monitors")
    endpoints: List[EndpointSpec] = Field(..., description="List of endpoints to monitor")
    
    @field_validator('endpoints')
    @classmethod
    def validate_endpoints(cls, v):
        if not v:
            raise ValueError('At least one endpoint must be specified')
        
        # Check for duplicate names
        names = [endpoint.name for endpoint in v]
        if len(names) != len(set(names)):
            raise ValueError('Endpoint names must be unique within a UptimeMonitor')
        
        return v
    
    def parse_default_tags(self) -> List[str]:
        """Parse default tags string into a list."""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def get_endpoint_tags(self, endpoint: EndpointSpec) -> List[str]:
        """Get the final tags for a specific endpoint."""
        if endpoint.tags_overwrite:
            return [tag.strip() for tag in endpoint.tags_overwrite.split(',') if tag.strip()]
        return self.parse_default_tags()
