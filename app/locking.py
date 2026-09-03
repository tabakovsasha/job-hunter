"""Inter-process locking mechanism"""

import fcntl
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from app.config import DATA_DIR

logger = logging.getLogger(__name__)

LOCK_FILE = DATA_DIR / "check.lock"


class CheckLock:
    """File-based lock for preventing concurrent vacancy checks"""
    
    def __init__(self, lock_file: Path = LOCK_FILE):
        self.lock_file = lock_file
        self.lock_fd: Optional[int] = None
    
    def acquire(self, non_blocking: bool = False) -> bool:
        """
        Acquire the lock.
        
        Args:
            non_blocking: If True, return False immediately if lock is held.
                         If False, block until lock is available.
        
        Returns:
            True if lock acquired, False if non_blocking and lock is held.
        """
        try:
            # Open or create lock file
            self.lock_fd = open(self.lock_file, 'w')
            
            # Try to acquire exclusive lock
            flags = fcntl.LOCK_EX
            if non_blocking:
                flags |= fcntl.LOCK_NB
            
            fcntl.flock(self.lock_fd, flags)
            logger.debug(f"Lock acquired: {self.lock_file}")
            return True
            
        except BlockingIOError:
            # Lock is held by another process
            if self.lock_fd:
                self.lock_fd.close()
                self.lock_fd = None
            logger.debug(f"Lock is held by another process: {self.lock_file}")
            return False
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            if self.lock_fd:
                self.lock_fd.close()
                self.lock_fd = None
            raise
    
    def release(self):
        """Release the lock"""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
                logger.debug(f"Lock released: {self.lock_file}")
            except Exception as e:
                logger.error(f"Failed to release lock: {e}")
            finally:
                self.lock_fd = None
    
    def __enter__(self):
        """Context manager entry"""
        self.acquire(non_blocking=False)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
        return False


@contextmanager
def check_lock(non_blocking: bool = False):
    """
    Context manager for check lock.
    
    Args:
        non_blocking: If True, raise LockHeldError if lock is held.
    
    Raises:
        LockHeldError: If non_blocking=True and lock is held.
    
    Example:
        with check_lock():
            # perform check
            pass
    """
    lock = CheckLock()
    acquired = lock.acquire(non_blocking=non_blocking)
    
    if not acquired:
        raise LockHeldError("Vacancy check is already in progress")
    
    try:
        yield lock
    finally:
        lock.release()


class LockHeldError(Exception):
    """Raised when trying to acquire a lock that is already held"""
    pass
