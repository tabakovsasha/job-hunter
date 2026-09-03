"""Main application logic"""

import logging
import sys

from app.storage import VacancyStorage
from app.telegram import TelegramNotifier
from app.monitor import run_check
from app.locking import check_lock, LockHeldError
from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main application entry point"""
    setup_logging()
    
    logger.info("Starting vacancy check")
    
    # Validate Telegram configuration
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured. Notifications will be skipped.")
        logger.warning("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file")
    
    # Initialize components
    storage = VacancyStorage()
    notifier = TelegramNotifier()
    
    # Acquire lock and run check
    try:
        with check_lock(non_blocking=True):
            result = run_check(storage, notifier)
            
            if result.has_errors:
                logger.warning("Check completed with errors")
                sys.exit(1)
            
    except LockHeldError:
        logger.error("Another check is already in progress. Exiting.")
        sys.exit(1)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Check failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
