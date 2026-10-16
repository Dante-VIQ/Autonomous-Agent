# src/utils/lock.py
"""Non-blocking per-brand cycle lock so overlapping runs cannot act twice."""

import fcntl
import os
import tempfile
from contextlib import contextmanager


def _lock_path(brand_id: int) -> str:
    base = os.getenv("AGENT_LOCK_DIR", tempfile.gettempdir())
    return os.path.join(base, f"vumbi-agent-brand-{brand_id}.lock")


@contextmanager
def cycle_lock(brand_id: int):
    """Yield True if the lock was acquired, False if another cycle holds it."""
    fd = os.open(_lock_path(brand_id), os.O_CREAT | os.O_RDWR, 0o644)
    acquired = False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError:
            acquired = False
        yield acquired
    finally:
        if acquired:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
