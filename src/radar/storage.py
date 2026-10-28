"""Atomic storage and persistence engine for Creative Radar.

Guarantees atomic file writes to prevent data corruption, preserves
historical data across fetch failures, tracks deduplication/alert state,
and audits output payloads to guarantee zero secret leakage.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from src.radar.config import (
    GEMINI_API_KEY,
    HEALTH_JSON_FILE,
    RADAR_JSON_FILE,
    STATE_FILE,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    setup_logger,
)
from src.radar.models import RadarItem, RadarPayload

logger = setup_logger("radar.storage")


def check_for_secret_leak(data: Any, secrets: list[str] | None = None) -> None:
    """Recursively verify that no secret strings exist in the published data."""
    active_secrets = [
        s for s in (secrets or [GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID])
        if s and len(s) > 5
    ]
    if not active_secrets:
        return

    serialized = json.dumps(data) if not isinstance(data, str) else data
    for secret in active_secrets:
        if secret in serialized:
            raise ValueError(
                "SECURITY VIOLATION: Detected sensitive credential within JSON payload! Write aborted."
            )


def write_json_atomic(target_path: Path, data: Any, indent: int = 2) -> None:
    """Atomically write JSON data using a temporary swap file."""
    # Ensure target directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Security check: Ensure no secrets are in the data
    check_for_secret_leak(data)

    tmp_path = target_path.with_suffix(f"{target_path.suffix}.tmp")

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    # Atomic rename/replace
    os.replace(tmp_path, target_path)
    logger.debug("Atomically wrote '%s'.", target_path.name)


def load_json_safe(file_path: Path) -> dict[str, Any] | list[Any] | None:
    """Safely read and parse a JSON file, returning None on error."""
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Error reading JSON '%s': %s", file_path.name, exc)
        return None


def is_data_stale(generated_at_iso: str, max_age_hours: float = 48.0) -> bool:
    """Check if existing data exceeds maximum age threshold."""
    if not generated_at_iso:
        return True
    try:
        dt = datetime.fromisoformat(generated_at_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_hours = (now - dt).total_seconds() / 3600.0
        return age_hours > max_age_hours
    except Exception:
        return True


def save_radar_payload(payload: RadarPayload, target_file: Path = RADAR_JSON_FILE) -> None:
    """Save full radar dataset to radar.json atomically."""
    data = payload.to_dict()
    write_json_atomic(target_file, data)
    logger.info("Saved %d radar items to '%s'.", len(payload.items), target_file.name)


def load_radar_payload(file_path: Path = RADAR_JSON_FILE) -> RadarPayload | None:
    """Load existing radar payload from disk."""
    raw = load_json_safe(file_path)
    if not raw or not isinstance(raw, dict):
        return None

    items_data = raw.get("items", [])
    items = [RadarItem.from_dict(d) for d in items_data if isinstance(d, dict)]
    gen_at = raw.get("generated_at", "")
    stale = is_data_stale(gen_at)

    return RadarPayload(
        generated_at=gen_at,
        total_items=len(items),
        is_demo=bool(raw.get("is_demo", False)),
        is_stale=stale,
        gemini_enabled=bool(raw.get("gemini_enabled", False)),
        urgent_alerts_count=int(raw.get("urgent_alerts_count", 0)),
        items=items,
        top_categories=dict(raw.get("top_categories", {})),
    )


def load_state(state_file: Path = STATE_FILE) -> dict[str, Any]:
    """Load persistent pipeline state (alert tracking, deduplication history)."""
    raw = load_json_safe(state_file)
    if raw and isinstance(raw, dict):
        return raw
    return {
        "sent_telegram_alert_ids": [],
        "last_briefing_date": "",
        "last_run_timestamp": "",
    }


def save_state(state: dict[str, Any], state_file: Path = STATE_FILE) -> None:
    """Persist pipeline state atomically."""
    write_json_atomic(state_file, state)
