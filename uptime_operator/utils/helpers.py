"""Helper utility functions."""
from typing import List, Optional


def build_monitor_name(namespace: str, cr_name: str, endpoint_name: str) -> str:
    """Build monitor name using the required format."""
    return f"{namespace}/{cr_name}/{endpoint_name}"


def parse_tags(tags_str: Optional[str]) -> List[str]:
    """Parse comma-separated tags string into a list."""
    if not tags_str:
        return []
    return [tag.strip() for tag in tags_str.split(',') if tag.strip()]
