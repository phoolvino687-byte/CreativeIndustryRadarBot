"""Tests for atomic file writing, stale data detection, and failure preservation."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import pytest

from src.radar.models import RadarItem, RadarPayload
from src.radar.storage import (
    is_data_stale,
    load_json_safe,
    load_radar_payload,
    save_radar_payload,
    write_json_atomic,
)


def test_write_json_atomic_creates_valid_file(tmp_path: Path):
    target = tmp_path / "test.json"
    data = {"status": "ok", "items_count": 42}

    write_json_atomic(target, data)

    assert target.exists()
    loaded = load_json_safe(target)
    assert loaded == data


def test_is_data_stale_detection():
    now = datetime.now(timezone.utc)

    fresh_time = (now - timedelta(hours=2)).isoformat()
    assert is_data_stale(fresh_time, max_age_hours=48.0) is False

    stale_time = (now - timedelta(hours=50)).isoformat()
    assert is_data_stale(stale_time, max_age_hours=48.0) is True

    # Empty or unparseable time should be treated as stale
    assert is_data_stale("", max_age_hours=48.0) is True
    assert is_data_stale("invalid-date", max_age_hours=48.0) is True


def test_save_and_load_radar_payload(tmp_path: Path):
    target_file = tmp_path / "radar.json"
    now_iso = datetime.now(timezone.utc).isoformat()

    item = RadarItem(
        id="item-test-1",
        title="Adobe Updates After Effects with GPU Render Boost",
        link="https://blog.adobe.com/ae-update",
        canonical_url="https://blog.adobe.com/ae-update",
        published_at=now_iso,
        source_id="adobe-cc",
        source_name="Adobe Official",
        category="adobe",
        trust_level="official",
        summary_what="Adobe released After Effects update with GPU cache speedups.",
        summary_why="Drastically speeds up preview playback on complex multi-layer compositions.",
        summary_action="Update via Creative Cloud App.",
        relevance_score=9.0,
        composite_priority=8.5,
    )

    payload = RadarPayload(
        generated_at=now_iso,
        total_items=1,
        is_demo=False,
        is_stale=False,
        gemini_enabled=True,
        urgent_alerts_count=1,
        items=[item],
        top_categories={"adobe": 1},
    )

    save_radar_payload(payload, target_file=target_file)
    assert target_file.exists()

    loaded_payload = load_radar_payload(file_path=target_file)
    assert loaded_payload is not None
    assert loaded_payload.total_items == 1
    assert loaded_payload.items[0].id == "item-test-1"
    assert loaded_payload.items[0].category == "adobe"
