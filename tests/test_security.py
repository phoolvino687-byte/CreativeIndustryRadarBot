"""Security audits and secret leakage prevention tests for Creative Radar.

Verifies:
1. Payloads containing secret tokens are blocked before disk write
2. Logger filters scrub secret tokens from stdout and log records
3. Public repository files (sources.json, demo_radar.json, index.html) contain zero secrets
"""

import json
import logging
from pathlib import Path
import pytest

from src.radar.config import SecretFilter, mask_secret
from src.radar.storage import check_for_secret_leak


def test_mask_secret_helper():
    assert mask_secret("123456789:ABCdefGhI_SecretToken") == "123***ken"
    assert mask_secret(None) == "[NOT CONFIGURED]"
    assert mask_secret("") == "[NOT CONFIGURED]"
    assert mask_secret("short") == "***"


def test_check_for_secret_leak_raises_on_leak():
    secret_token = "SUPER_SECRET_GEMINI_KEY_99999"
    compromised_data = {
        "title": "Clean Title",
        "description": f"Here is my secret {secret_token} by accident.",
    }

    with pytest.raises(ValueError, match="SECURITY VIOLATION"):
        check_for_secret_leak(compromised_data, secrets=[secret_token])


def test_check_for_secret_leak_passes_on_clean_data():
    secret_token = "SUPER_SECRET_GEMINI_KEY_99999"
    clean_data = {
        "title": "Clean Title",
        "description": "Public creative industry report without sensitive tokens.",
    }
    # Should not raise any exception
    check_for_secret_leak(clean_data, secrets=[secret_token])


def test_secret_filter_scrubs_log_records():
    secret_token = "BOT_TOKEN_1234567890_XYZ"
    log_filter = SecretFilter(secrets_to_mask=[secret_token])

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=f"Dispatching notification with token {secret_token}",
        args=(),
        exc_info=None,
    )

    log_filter.filter(record)
    assert secret_token not in record.msg
    assert "[REDACTED_SECRET]" in record.msg


def test_public_files_contain_no_secrets():
    base_dir = Path(__file__).resolve().parent.parent

    files_to_check = [
        base_dir / "config" / "sources.json",
        base_dir / "data" / "demo_radar.json",
        base_dir / "index.html",
        base_dir / "styles.css",
        base_dir / "app.js",
    ]

    suspicious_patterns = [
        "AIzaSy",  # Standard Google API Key prefix
        "ghp_",    # GitHub personal access token prefix
        "bot[0-9]{8,}:", # Telegram bot prefix
    ]

    for file_path in files_to_check:
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            for pattern in suspicious_patterns:
                assert pattern not in content, f"Potential secret pattern '{pattern}' found in '{file_path.name}'"
