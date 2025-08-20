"""
Main entry point for the Uptime Operator.
"""
import os
import kopf
from loguru import logger
from dotenv import load_dotenv

from uptime_operator.handlers import register_handlers
from uptime_operator.handlers.startup import configure_operator
from uptime_operator.utils.config import Config

# Load environment variables
load_dotenv()

# Initialize configuration
config = Config()

# Configure logging
logger.add("operator.log", rotation="1 day", retention="7 days", level=config.log_level)
logger.info("Starting Uptime Operator")

# Register startup handler
@kopf.on.startup()
def startup(settings: kopf.OperatorSettings, **kwargs):
    """Configure the operator on startup."""
    configure_operator(settings, **kwargs)

# Register all handlers
register_handlers()


if __name__ == "__main__":
    # Run the operator
    logger.info("Running Uptime Operator")
    kopf.run()
