"""Kopf handlers for UptimeMonitor resources."""
import kopf
from loguru import logger

from .reconciler import UptimeMonitorReconciler

# Lazily initialize reconciler when needed
_reconciler = None

def get_reconciler():
    """Get the reconciler instance (lazy initialization)."""
    global _reconciler
    if _reconciler is None:
        _reconciler = UptimeMonitorReconciler()
    return _reconciler


@kopf.on.create('uptime-operator.dev', 'v1alpha1', 'uptimemonitors')
async def on_create(spec, status, meta, logger, **kwargs):
    """Handle UptimeMonitor creation."""
    namespace = meta['namespace']
    name = meta['name']
    
    logger.info(f"Creating UptimeMonitor {namespace}/{name}")
    
    kopf.append_owner_reference(kwargs['body'])
    
    new_status = await get_reconciler().reconcile(spec, status, meta, logger)
    
    logger.info(f"UptimeMonitor {namespace}/{name} created successfully")
    return new_status


@kopf.on.update('uptime-operator.dev', 'v1alpha1', 'uptimemonitors')
async def on_update(spec, status, meta, logger, **kwargs):
    """Handle UptimeMonitor updates."""
    namespace = meta['namespace']
    name = meta['name']
    
    logger.info(f"Updating UptimeMonitor {namespace}/{name}")
    
    new_status = await get_reconciler().reconcile(spec, status, meta, logger)
    
    logger.info(f"UptimeMonitor {namespace}/{name} updated successfully")
    return new_status


@kopf.on.delete('uptime-operator.dev', 'v1alpha1', 'uptimemonitors')
async def on_delete(spec, status, meta, logger, **kwargs):
    """Handle UptimeMonitor deletion."""
    namespace = meta['namespace']
    name = meta['name']
    crd_uid = meta['uid']
    
    logger.info(f"Deleting UptimeMonitor {namespace}/{name}")
    
    try:
        await get_reconciler()._cleanup_monitors(crd_uid)
        logger.info(f"UptimeMonitor {namespace}/{name} cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during cleanup of {namespace}/{name}: {e}")


@kopf.on.field('uptime-operator.dev', 'v1alpha1', 'uptimemonitors', field='spec')
async def on_spec_change(old, new, status, meta, logger, **kwargs):
    """Handle changes to the spec field specifically."""
    namespace = meta['namespace']
    name = meta['name']
    
    logger.info(f"Spec changed for UptimeMonitor {namespace}/{name}")
    
    new_status = await get_reconciler().reconcile(new, status, meta, logger)
    
    return new_status


def register_handlers():
    """Register all handlers. This function is called from main.py."""
    logger.info("UptimeMonitor handlers registered")
