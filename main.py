"""CLI entrypoint for Creative Radar.

Allows running the pipeline, testing notifications, and managing demo data.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.radar.config import (
    DATA_DIR,
    DEMO_JSON_FILE,
    DRY_RUN,
    ENABLE_TELEGRAM,
    RADAR_JSON_FILE,
    SOURCES_FILE,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    setup_logger,
)
from src.radar.pipeline import run_pipeline
from src.radar.storage import load_radar_payload, save_radar_payload
from src.radar.telegram_notifier import send_telegram_message

logger = setup_logger("radar.cli")


def handle_test_telegram() -> None:
    """Send a test message to verify Telegram credentials."""
    logger.info("Sending test notification to Telegram...")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing. Message will only be logged."
        )

    test_msg = (
        "📡 <b>CREATIVE RADAR // TEST DISPATCH</b>\n\n"
        "Your Telegram alert and briefing connection is working properly!\n"
        "• Daily briefings: Scheduled at 03:30 UTC (09:00 IST)\n"
        "• Urgent alerts: Dispatched automatically when high-impact updates appear.\n\n"
        "<i>Creative Radar Automation Engine</i>"
    )
    success = send_telegram_message(test_msg, dry_run=False)
    if success:
        logger.info("Test message sent successfully!")
    else:
        logger.error("Failed to send test message. Check token and chat ID.")


def handle_load_demo() -> None:
    """Load demo dataset into radar.json for offline testing."""
    if not DEMO_JSON_FILE.exists():
        logger.error("Demo file '%s' not found.", DEMO_JSON_FILE)
        sys.exit(1)

    payload = load_radar_payload(DEMO_JSON_FILE)
    if not payload:
        logger.error("Failed to parse demo data.")
        sys.exit(1)

    payload.is_demo = True
    save_radar_payload(payload, RADAR_JSON_FILE)
    logger.info("Successfully loaded demo dataset into '%s'.", RADAR_JSON_FILE)


def main() -> None:
    """Parse command line arguments and execute pipeline."""
    parser = argparse.ArgumentParser(
        description="Creative Radar: Automated Creative Industry Intelligence Platform"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=DRY_RUN,
        help="Simulate run without live Telegram delivery or public writes.",
    )
    parser.add_argument(
        "--sources",
        type=Path,
        default=SOURCES_FILE,
        help="Path to custom sources.json registry.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum items to fetch per feed.",
    )
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip Gemini API calls and strictly use extractive summarization.",
    )
    parser.add_argument(
        "--telegram",
        "--enable-telegram",
        dest="enable_telegram",
        action="store_true",
        default=ENABLE_TELEGRAM,
        help="Enable optional Telegram delivery (disabled by default for website-first workflow).",
    )
    parser.add_argument(
        "--test-telegram",
        action="store_true",
        help="Send a test message to verify Telegram credentials.",
    )
    parser.add_argument(
        "--load-demo",
        action="store_true",
        help="Load labelled demo data into data/radar.json for UI preview.",
    )
    parser.add_argument(
        "--dashboard-url",
        type=str,
        default="",
        help="Public URL for GitHub Pages dashboard to embed in Telegram links.",
    )

    args = parser.parse_args()

    if args.test_telegram:
        handle_test_telegram()
        return

    if args.load_demo:
        handle_load_demo()
        return

    run_pipeline(
        sources_path=args.sources,
        dry_run=args.dry_run,
        limit_per_feed=args.limit,
        use_ai=not args.skip_ai,
        send_telegram=args.enable_telegram,
        dashboard_url=args.dashboard_url,
    )


if __name__ == "__main__":
    main()
