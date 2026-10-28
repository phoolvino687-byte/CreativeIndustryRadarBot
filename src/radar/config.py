"""Configuration and environment management for Creative Radar.

Handles loading environment variables, defining default paths, and
providing secret masking to ensure no sensitive tokens leak into logs or JSON.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

# Load .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
SOURCES_FILE = Path(os.getenv("SOURCES_FILE", str(CONFIG_DIR / "sources.json")))
STATE_FILE = DATA_DIR / "state.json"
RADAR_JSON_FILE = DATA_DIR / "radar.json"
HEALTH_JSON_FILE = DATA_DIR / "health.json"
DEMO_JSON_FILE = DATA_DIR / "demo_radar.json"

# API and credentials
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Telegram configuration (optional, disabled by default for website-first workflow)
ENABLE_TELEGRAM: bool = os.getenv("ENABLE_TELEGRAM", "false").lower() in ("true", "1", "yes")

# Pipeline configuration
DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")
RADAR_ENV: str = os.getenv("RADAR_ENV", "development").lower()
MAX_ITEMS_PER_FEED: int = int(os.getenv("MAX_ITEMS_PER_FEED", "15"))
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
AI_MODEL: str = os.getenv("AI_MODEL", "gemini-2.5-flash").strip()

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


def mask_secret(secret: str | None, visible_prefix: int = 3, visible_suffix: int = 3) -> str:
    """Mask sensitive tokens for safe logging and status reporting.

    Example: '123456789:ABCdefGhI' -> '123***GhI'
    """
    if not secret:
        return "[NOT CONFIGURED]"
    s = str(secret).strip()
    if len(s) <= (visible_prefix + visible_suffix):
        return "***"
    return f"{s[:visible_prefix]}***{s[-visible_suffix:]}"


class SecretFilter(logging.Filter):
    """Logging filter that scrubs known secret values from all log records."""

    def __init__(self, secrets_to_mask: list[str] | None = None) -> None:
        super().__init__()
        self.secrets: list[str] = [
            s for s in (secrets_to_mask or [GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID])
            if s and len(s) > 4
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.secrets:
            return True
        msg = str(record.msg)
        for s in self.secrets:
            if s in msg:
                msg = msg.replace(s, "[REDACTED_SECRET]")
        record.msg = msg
        if record.args:
            if isinstance(record.args, dict):
                cleaned_dict: dict[Any, Any] = {}
                for k, v in record.args.items():
                    if isinstance(v, str):
                        for s in self.secrets:
                            v = v.replace(s, "[REDACTED_SECRET]")
                    cleaned_dict[k] = v
                record.args = cleaned_dict
            elif isinstance(record.args, (tuple, list)):
                cleaned_args: list[Any] = []
                for arg in record.args:
                    if isinstance(arg, str):
                        for s in self.secrets:
                            arg = arg.replace(s, "[REDACTED_SECRET]")
                        cleaned_args.append(arg)
                    else:
                        cleaned_args.append(arg)
                record.args = tuple(cleaned_args)
        return True


def setup_logger(name: str = "creative_radar", level: int = logging.INFO) -> logging.Logger:
    """Configure a logger equipped with secret-scrubbing filters."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretFilter())
        logger.addHandler(handler)
    return logger
