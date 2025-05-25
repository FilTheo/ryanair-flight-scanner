import logging
import sys
from lib.config import Config

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,  # Ensure logs go to stdout for Vercel
)

logger = logging.getLogger(__name__)
logger.info("Logging configured for the API.")
