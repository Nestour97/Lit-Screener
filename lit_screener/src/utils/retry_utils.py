"""Exponential-backoff retry decorator for API calls."""

import time
import logging
import functools
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator factory: retries a function with exponential backoff."""
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        f"[retry] {fn.__name__} attempt {attempt}/{max_attempts} "
                        f"failed: {exc}. Retrying in {delay:.1f}s…"
                    )
                    time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
