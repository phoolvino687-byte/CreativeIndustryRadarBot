"""Data normalization and sanitization for Creative Radar items.

Cleans untrusted HTML/scripts, normalizes dates into UTC ISO 8601,
canonicalizes URLs by removing tracking parameters, and computes deterministic IDs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.radar.config import setup_logger

logger = setup_logger("radar.normalizer")

# Query parameters to strip during canonicalization
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
    "_hsenc",
    "_hsmi",
    "msclkid",
}


def sanitize_text(text: str) -> str:
    """Strip HTML tags, decode entities, and normalize whitespace."""
    if not text:
        return ""
    # Strip script and style blocks first
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    # Decode HTML entities twice to catch nested encodings
    cleaned = html.unescape(html.unescape(cleaned))
    # Replace non-breaking spaces and normalize whitespace
    cleaned = cleaned.replace("\xa0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def canonicalize_url(url: str) -> str:
    """Clean and standardize URLs by removing marketing trackers and fragments."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        # Clean query parameters
        filtered_query = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS
        ]
        new_query = urlencode(filtered_query)
        # Standardize scheme and hostname
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()
        if path.endswith("/") and len(path) > 1:
            path = path[:-1]

        canonical = urlunparse((scheme, netloc, path, parsed.params, new_query, ""))
        return canonical
    except Exception:
        return url.strip()


def compute_item_id(canonical_url: str, title: str = "") -> str:
    """Generate a deterministic 16-character SHA-256 hash ID."""
    key = f"{canonical_url.strip()}|{title.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def parse_to_utc_iso(date_str: str | None) -> str:
    """Parse various RFC-822, RFC-2822, or ISO-8601 date strings to UTC ISO 8601."""
    if not date_str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cleaned = date_str.strip()

    # Try RFC-822 / RFC-2822 (common in RSS 2.0)
    try:
        dt = parsedate_to_datetime(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass

    # Try ISO-8601 (common in Atom)
    iso_clean = cleaned.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass

    # Fallback to current UTC time if format is unrecognized
    logger.debug("Unrecognized date format '%s', falling back to current UTC.", date_str)
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_item_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw parsed dictionary into clean structured item data."""
    clean_title = sanitize_text(raw.get("title", ""))
    raw_link = raw.get("link", "")
    canonical_link = canonicalize_url(raw_link)
    item_id = compute_item_id(canonical_link, clean_title)
    clean_content = sanitize_text(raw.get("raw_content", ""))
    pub_iso = parse_to_utc_iso(raw.get("pub_date_raw"))

    return {
        "id": item_id,
        "title": clean_title,
        "link": raw_link or canonical_link,
        "canonical_url": canonical_link,
        "published_at": pub_iso,
        "raw_content": clean_content,
        "image_url": raw.get("image_url"),
        "source_id": raw.get("source_id", "unknown"),
        "source_name": raw.get("source_name", "Unknown Source"),
        "category": raw.get("category", "general"),
        "trust_level": raw.get("trust_level", "reputable"),
    }
