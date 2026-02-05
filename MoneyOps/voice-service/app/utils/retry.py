"""""
Retry logic for external service calls
"""
from tenacity import(
    retry, 
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

import httpx
from app.utils.logger import get_logger

logger = get_logger(__name__)

def retry_on_http_error(max_attempts: int = 3):
    """Retry decoder for http calls"""

    return retry(
        stop = stop_after_attempt(max_attempts),
        wait = wait_exponential(multiplier=1, min=1, max=10),
        retry = retry_if_exception_type((
            httpx.TimeoutException,
            httpx.NetworkError,
         )),

         before_sleep = lambda retry_state : logger.warning(
            "Retrying http call",
            attempt = retry_state.attempt_number,
    ),
    )