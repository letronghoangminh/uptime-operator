"""Configuration management for the operator."""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration settings for the Uptime Operator."""
    
    # Uptime Kuma Configuration
    uptime_kuma_url: str = Field(default="http://localhost:3001", env="UPTIME_KUMA_URL")
    uptime_kuma_username: str = Field(default="admin", env="UPTIME_KUMA_USERNAME")
    uptime_kuma_password: str = Field(default="admin", env="UPTIME_KUMA_PASSWORD")
    
    # Kubernetes Configuration
    cluster_name: str = Field(default="default", env="CLUSTER_NAME")
    kubeconfig: Optional[str] = Field(default=None, env="KUBECONFIG")
    
    # Operator Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    operator_namespace: str = Field(default="default", env="OPERATOR_NAMESPACE")
    
    # Monitor Configuration
    monitor_interval: int = Field(default=60, env="MONITOR_INTERVAL")
    retry_interval: int = Field(default=60, env="RETRY_INTERVAL")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
