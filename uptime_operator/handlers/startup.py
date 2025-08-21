"""Startup configuration for the operator."""
import kopf
from kubernetes import config
from loguru import logger

from ..utils.config import Config


def configure_operator(settings: kopf.OperatorSettings, **_):
    """Configure the operator on startup."""
    app_config = Config()
    
    settings.posting.level = kopf.config.EVENTS_LOGLEVEL_INFO
    settings.watching.connect_timeout = 1 * 60
    settings.watching.server_timeout = 10 * 60
    
    try:
        if app_config.kubeconfig:
            config.load_kube_config(config_file=app_config.kubeconfig)
            logger.info(f"Loaded Kubernetes configuration from {app_config.kubeconfig}")
        else:
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            except:
                config.load_kube_config()
                logger.info("Loaded local Kubernetes configuration")
    except Exception as e:
        logger.error(f"Failed to load Kubernetes configuration: {e}")
        raise
    
    logger.info(f"Operator configured with cluster: {app_config.cluster_name}")
    logger.info(f"Uptime Kuma URL: {app_config.uptime_kuma_url}")
