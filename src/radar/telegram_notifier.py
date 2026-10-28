"""Telegram notification delivery for Creative Radar.

Formats and delivers:
1. Daily morning briefing digests (top creative stories grouped by priority)
2. Immediate high-urgency alerts (critical firmware fixes, security patches, flash deals)

Includes anti-duplication tracking via state.json, HTML tag escaping,
and dry-run simulation mode without leaking bot credentials.
"""

from __future__ import annotations

from datetime import datetime, timezone
import html
from typing import Any

import requests

from src.radar.config import (
    DRY_RUN,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    mask_secret,
    setup_logger,
)
from src.radar.models import RadarItem
from src.radar.storage import load_state, save_state

logger = setup_logger("radar.telegram")

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

CATEGORY_EMOJIS = {
    "adobe": "🎨",
    "davinci-blackmagic": "🎞️",
    "cameras-lenses-firmware": "📷",
    "motion-vfx-blender": "🧊",
    "design-fonts-plugins": "✒️",
    "ai-tools-offers": "🤖",
    "photography-filmmaking-freelance": "🎬",
    "general": "📡",
}


def escape_html(text: str | None) -> str:
    """Escape text for Telegram HTML parse mode."""
    if not text:
        return ""
    return html.escape(str(text), quote=False)


def send_telegram_message(
    message_html: str,
    bot_token: str = TELEGRAM_BOT_TOKEN,
    chat_id: str = TELEGRAM_CHAT_ID,
    dry_run: bool = DRY_RUN,
    timeout: int = 15,
) -> bool:
    """Send an HTML-formatted message via the Telegram Bot API."""
    if dry_run or not bot_token or not chat_id:
        logger.info(
            "[DRY-RUN / NO CREDS] Telegram message delivery simulated:\n"
            "--- TELEGRAM PAYLOAD ---\n%s\n-------------------------",
            message_html,
        )
        return True

    url = TELEGRAM_API_URL.format(token=bot_token)
    payload = {
        "chat_id": chat_id,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        if response.status_code == 200:
            logger.info("Telegram message successfully delivered to chat %s.", mask_secret(chat_id))
            return True
        else:
            logger.error(
                "Telegram API error HTTP %s: %s",
                response.status_code,
                response.text,
            )
            return False
    except Exception as exc:
        logger.error("Failed to deliver Telegram message: %s", exc)
        return False


def format_daily_briefing(
    items: list[RadarItem],
    top_n: int = 5,
    dashboard_url: str = "",
) -> str:
    """Build the daily morning briefing HTML message."""
    top_items = sorted(items, key=lambda x: x.composite_priority, reverse=True)[:top_n]
    date_str = datetime.now(timezone.utc).strftime("%d %b %Y • %H:%M UTC")

    lines = [
        "📡 <b>CREATIVE RADAR // DAILY BRIEFING</b>",
        f"<i>{escape_html(date_str)}</i>",
        "",
        f"⚡ <b>Top {len(top_items)} Verified Updates:</b>",
        "",
    ]

    for idx, item in enumerate(top_items, start=1):
        emoji = CATEGORY_EMOJIS.get(item.category, "📌")
        title_esc = escape_html(item.title)
        link = item.link or item.canonical_url
        what = escape_html(item.summary_what or item.title)
        why = escape_html(item.summary_why or "")
        action = escape_html(item.summary_action or "")

        lines.append(f"<b>{idx}. {emoji} <a href=\"{link}\">{title_esc}</a></b>")
        lines.append(f"   🏷️ {escape_html(item.category)} • 🛡️ {escape_html(item.verification_label)} • ⚡ <b>{item.composite_priority}/10</b>")
        lines.append(f"   • <b>What:</b> {what}")
        if why:
            lines.append(f"   • <b>Impact:</b> {why}")
        if action:
            lines.append(f"   • <b>Action:</b> {action}")
        lines.append("")

    if dashboard_url:
        lines.append(f"🌐 <a href=\"{dashboard_url}\">Open Full Interactive Dashboard</a>")
    else:
        lines.append("🌐 <i>Interactive dashboard updated.</i>")

    return "\n".join(lines)


def format_urgent_alert(item: RadarItem) -> str:
    """Build an urgent alert message for critical firmware, zero-days, or flash deals."""
    title_esc = escape_html(item.title)
    link = item.link or item.canonical_url
    what = escape_html(item.summary_what or item.title)
    why = escape_html(item.summary_why or "")
    action = escape_html(item.summary_action or "")

    lines = [
        "🚨 <b>URGENT CREATIVE RADAR ALERT</b>",
        "",
        f"<b><a href=\"{link}\">{title_esc}</a></b>",
        f"🏷️ Category: <b>{escape_html(item.category)}</b>",
        f"🛡️ Trust: <b>{escape_html(item.verification_label)}</b>",
        f"⚡ Priority: <b>{item.composite_priority}/10</b> | Urgency: <b>{item.urgency_score}/10</b>",
        "",
        f"• <b>What happened:</b> {what}",
    ]

    if why:
        lines.append(f"• <b>Why it matters:</b> {why}")
    if action:
        lines.append(f"• <b>Immediate Action:</b> {action}")

    lines.append("")
    lines.append(f"🔗 <a href=\"{link}\">View Original Announcement</a>")

    return "\n".join(lines)


def dispatch_alerts_and_briefing(
    items: list[RadarItem],
    bot_token: str = TELEGRAM_BOT_TOKEN,
    chat_id: str = TELEGRAM_CHAT_ID,
    dry_run: bool = DRY_RUN,
    dashboard_url: str = "",
    send_briefing: bool = True,
    urgency_threshold: float = 8.5,
) -> dict[str, Any]:
    """Process anti-duplication state, dispatch urgent alerts, and send daily briefing."""
    state = load_state()
    sent_alert_ids = set(state.get("sent_telegram_alert_ids", []))
    new_alerts_sent = 0

    # 1. Dispatch any unnotified urgent alerts
    for item in items:
        if (item.urgency_score >= urgency_threshold or item.composite_priority >= urgency_threshold):
            if item.id not in sent_alert_ids:
                alert_html = format_urgent_alert(item)
                success = send_telegram_message(
                    alert_html,
                    bot_token=bot_token,
                    chat_id=chat_id,
                    dry_run=dry_run,
                )
                if success:
                    sent_alert_ids.add(item.id)
                    new_alerts_sent += 1

    # 2. Dispatch daily briefing if requested
    briefing_sent = False
    if send_briefing and items:
        briefing_html = format_daily_briefing(
            items,
            top_n=5,
            dashboard_url=dashboard_url,
        )
        briefing_sent = send_telegram_message(
            briefing_html,
            bot_token=bot_token,
            chat_id=chat_id,
            dry_run=dry_run,
        )

    # Persist updated alert IDs
    state["sent_telegram_alert_ids"] = list(sent_alert_ids)
    state["last_briefing_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    return {
        "new_urgent_alerts_sent": new_alerts_sent,
        "briefing_sent": briefing_sent,
        "total_historical_alerts": len(sent_alert_ids),
    }
