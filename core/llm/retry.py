"""Retry utility for LLM calls with exponential backoff."""

from __future__ import annotations

import asyncio
import random
from typing import TypeVar, Callable, Awaitable

from loguru import logger

T = TypeVar("T")

# Exceptions worth retrying
RETRYABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    OSError,
)


def _is_rate_limit(exc: Exception) -> bool:
    """Check if exception is a rate-limit error (status 429)."""
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    return status == 429


def _is_retryable(exc: Exception) -> bool:
    """Determine if an exception is worth retrying."""
    if isinstance(exc, RETRYABLE_EXCEPTIONS):
        return True
    if _is_rate_limit(exc):
        return True
    # Server errors (5xx)
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(status, int) and 500 <= status < 600:
        return True
    return False


async def retry_async(
    fn: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    **kwargs,
) -> T:
    """Call an async function with exponential backoff retry.

    Retries on rate-limit (429), server errors (5xx), timeouts, and connection errors.
    JSON parse errors from generate_structured are NOT retried here — they are
    handled at the generate_structured level.
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt == max_retries or not _is_retryable(exc):
                raise

            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.25)
            wait = delay + jitter

            logger.warning(
                "LLM call failed (attempt {}/{}): {} — retrying in {:.1f}s",
                attempt + 1,
                max_retries + 1,
                exc,
                wait,
            )
            await asyncio.sleep(wait)

    raise last_exc  # type: ignore[misc]
