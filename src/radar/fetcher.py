"""Resilient HTTP client for fetching RSS and Atom feeds.

Provides timeouts, retries, SSL resilience, custom user-agent,
and latency measurement without crashing on network or server failures.
"""

from __future__ import annotations

import time
from typing import Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.radar.config import REQUEST_TIMEOUT, setup_logger
from src.radar.models import RadarSource

logger = setup_logger("radar.fetcher")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 "
    "CreativeRadar/1.0 (+https://github.com/creative-industry-radar)"
)


def create_session() -> requests.Session:
    """Create a configured requests session with retry strategy."""
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_feed(
    source: RadarSource,
    timeout: int = REQUEST_TIMEOUT,
    session: requests.Session | None = None,
) -> Tuple[str, int, float, str | None]:
    """Fetch feed content from a source URL.

    Returns:
        (content_str, status_code, elapsed_ms, error_message)
    """
    client = session or create_session()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }

    start_time = time.perf_counter()
    status_code = 0
    error_message: str | None = None
    content = ""

    try:
        response = client.get(source.url, headers=headers, timeout=timeout)
        status_code = response.status_code
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if response.status_code == 200:
            content = response.text
            logger.info(
                "Fetched '%s' (status=%d, size=%d chars, time=%.1fms)",
                source.name,
                status_code,
                len(content),
                elapsed_ms,
            )
            return content, status_code, elapsed_ms, None
        else:
            error_message = f"HTTP {response.status_code} {response.reason}"
            logger.warning(
                "Failed fetching '%s': %s (status=%d)",
                source.name,
                error_message,
                status_code,
            )
            return "", status_code, elapsed_ms, error_message

    except requests.exceptions.Timeout:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        error_message = f"Request timed out after {timeout}s"
        logger.warning("Timeout fetching '%s': %s", source.name, error_message)
        return "", 408, elapsed_ms, error_message

    except requests.exceptions.SSLError as ssl_err:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        error_message = f"SSL Error: {ssl_err}"
        logger.warning("SSL failure for '%s': %s", source.name, error_message)
        return "", 495, elapsed_ms, error_message

    except requests.exceptions.RequestException as req_err:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        error_message = f"Connection error: {req_err}"
        logger.warning("Connection failure for '%s': %s", source.name, error_message)
        return "", 599, elapsed_ms, error_message

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        error_message = f"Unexpected error: {exc}"
        logger.error("Unexpected error fetching '%s': %s", source.name, error_message)
        return "", 500, elapsed_ms, error_message
