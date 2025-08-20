"""Tests for Pydantic models."""
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from uptime_operator.models import UptimeMonitorSpec, EndpointSpec, UptimeMonitorStatus, MonitorStatus, Condition


class TestEndpointSpec:
    """Tests for EndpointSpec model."""
    
    def test_valid_endpoint(self):
        """Test valid endpoint creation."""
        endpoint = EndpointSpec(
            name="test-endpoint",
            url="https://example.com/health"
        )
        assert endpoint.name == "test-endpoint"
        assert endpoint.url == "https://example.com/health"
        assert endpoint.tags_overwrite is None
    
    def test_endpoint_with_tags(self):
        """Test endpoint with tags overwrite."""
        endpoint = EndpointSpec(
            name="test-endpoint",
            url="https://example.com/health",
            tags_overwrite="prod,critical"
        )
        assert endpoint.tags_overwrite == "prod,critical"
    
    def test_invalid_url(self):
        """Test invalid URL validation."""
        with pytest.raises(ValidationError):
            EndpointSpec(name="test", url="invalid-url")
    
    def test_empty_name(self):
        """Test empty name validation."""
        with pytest.raises(ValidationError):
            EndpointSpec(name="", url="https://example.com")


class TestUptimeMonitorSpec:
    """Tests for UptimeMonitorSpec model."""
    
    def test_valid_spec(self):
        """Test valid spec creation."""
        spec = UptimeMonitorSpec(
            enabled=True,
            tags="test,integration",
            endpoints=[
                EndpointSpec(name="endpoint1", url="https://example.com"),
                EndpointSpec(name="endpoint2", url="https://test.com")
            ]
        )
        assert spec.enabled is True
        assert spec.tags == "test,integration"
        assert len(spec.endpoints) == 2
    
    def test_empty_endpoints(self):
        """Test validation fails with empty endpoints."""
        with pytest.raises(ValidationError):
            UptimeMonitorSpec(enabled=True, endpoints=[])
    
    def test_duplicate_endpoint_names(self):
        """Test validation fails with duplicate endpoint names."""
        with pytest.raises(ValidationError):
            UptimeMonitorSpec(
                enabled=True,
                endpoints=[
                    EndpointSpec(name="duplicate", url="https://example1.com"),
                    EndpointSpec(name="duplicate", url="https://example2.com")
                ]
            )
    
    def test_parse_default_tags(self):
        """Test parsing default tags."""
        spec = UptimeMonitorSpec(
            enabled=True,
            tags="  tag1,tag2  , tag3  ",
            endpoints=[EndpointSpec(name="test", url="https://example.com")]
        )
        tags = spec.parse_default_tags()
        assert tags == ["tag1", "tag2", "tag3"]
    
    def test_get_endpoint_tags_with_overwrite(self):
        """Test getting endpoint tags with overwrite."""
        endpoint = EndpointSpec(
            name="test",
            url="https://example.com",
            tags_overwrite="override1,override2"
        )
        spec = UptimeMonitorSpec(
            enabled=True,
            tags="default1,default2",
            endpoints=[endpoint]
        )
        
        tags = spec.get_endpoint_tags(endpoint)
        assert tags == ["override1", "override2"]
    
    def test_get_endpoint_tags_without_overwrite(self):
        """Test getting endpoint tags without overwrite."""
        endpoint = EndpointSpec(name="test", url="https://example.com")
        spec = UptimeMonitorSpec(
            enabled=True,
            tags="default1,default2",
            endpoints=[endpoint]
        )
        
        tags = spec.get_endpoint_tags(endpoint)
        assert tags == ["default1", "default2"]


class TestUptimeMonitorStatus:
    """Tests for UptimeMonitorStatus model."""
    
    def test_status_creation(self):
        """Test status creation."""
        now = datetime.now(timezone.utc)
        status = UptimeMonitorStatus(
            conditions=[
                Condition(
                    type="Ready",
                    status="True",
                    lastTransitionTime=now,
                    reason="SyncSuccessful",
                    message="All monitors synced"
                )
            ],
            monitors=[
                MonitorStatus(
                    name="test",
                    url="https://example.com",
                    uptimeKumaId=123,
                    status="Ready",
                    lastSync=now
                )
            ],
            lastSync=now
        )
        
        assert len(status.conditions) == 1
        assert len(status.monitors) == 1
        assert status.is_ready() is True
    
    def test_get_failed_monitors(self):
        """Test getting failed monitors."""
        now = datetime.now(timezone.utc)
        status = UptimeMonitorStatus(
            monitors=[
                MonitorStatus(
                    name="success",
                    url="https://example.com",
                    uptimeKumaId=123,
                    status="Ready",
                    lastSync=now
                ),
                MonitorStatus(
                    name="failed",
                    url="https://bad.com",
                    uptimeKumaId=None,
                    status="CreateFailed",
                    lastSync=now
                )
            ]
        )
        
        failed = status.get_failed_monitors()
        assert len(failed) == 1
        assert failed[0].name == "failed"
