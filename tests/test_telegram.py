"""Tests for Telegram notification formatting, HTML escaping, anti-duplication, and dry-run delivery."""

from unittest.mock import MagicMock, patch
from src.radar.models import RadarItem
from src.radar.telegram_notifier import (
    dispatch_alerts_and_briefing,
    escape_html,
    format_daily_briefing,
    format_urgent_alert,
    send_telegram_message,
)


def create_sample_radar_item(item_id="item-001", urgency=9.5, priority=9.2) -> RadarItem:
    return RadarItem(
        id=item_id,
        title="Critical Security Patch & Update for DaVinci Resolve <19.0.2>",
        link="https://www.blackmagicdesign.com/support",
        canonical_url="https://www.blackmagicdesign.com/support",
        published_at="2026-10-28T09:00:00Z",
        source_id="blackmagic-official",
        source_name="Blackmagic Design",
        category="davinci-blackmagic",
        trust_level="official",
        verification_label="Official / Confirmed",
        summary_what="Blackmagic released security patch 19.0.2 fixing crash flaw.",
        summary_why="Prevents project database corruption on Windows & Mac.",
        summary_action="Update immediately via official support page.",
        urgency_score=urgency,
        composite_priority=priority,
    )


def test_escape_html_handles_special_characters():
    raw = "Premiere Pro & After Effects <v24.2> \"Update\""
    escaped = escape_html(raw)
    assert "&amp;" in escaped
    assert "&lt;v24.2&gt;" in escaped
    assert "<v24.2>" not in escaped


def test_format_daily_briefing_structure():
    item1 = create_sample_radar_item("item-1", urgency=5.0, priority=8.5)
    item2 = create_sample_radar_item("item-2", urgency=4.0, priority=7.0)

    briefing = format_daily_briefing([item1, item2], top_n=2, dashboard_url="https://example.com/radar")
    assert "CREATIVE RADAR // DAILY BRIEFING" in briefing
    assert "https://example.com/radar" in briefing
    assert "What:" in briefing
    assert "Impact:" in briefing
    assert "Action:" in briefing


def test_format_urgent_alert_structure():
    item = create_sample_radar_item("urgent-1", urgency=9.8, priority=9.5)
    alert = format_urgent_alert(item)
    assert "URGENT CREATIVE RADAR ALERT" in alert
    assert "9.5/10" in alert
    assert "9.8/10" in alert
    assert "What happened:" in alert


def test_dry_run_does_not_call_network():
    # dry_run=True should return True without calling requests
    with patch("requests.post") as mock_post:
        res = send_telegram_message("Test message", dry_run=True)
        assert res is True
        mock_post.assert_not_called()


@patch("src.radar.telegram_notifier.save_state")
@patch("src.radar.telegram_notifier.load_state")
@patch("src.radar.telegram_notifier.send_telegram_message")
def test_anti_duplication_prevents_duplicate_urgent_alerts(mock_send, mock_load, mock_save):
    # State already contains 'urgent-already-sent'
    mock_load.return_value = {
        "sent_telegram_alert_ids": ["urgent-already-sent"],
        "last_briefing_date": "2026-10-27",
    }
    mock_send.return_value = True

    already_sent_item = create_sample_radar_item("urgent-already-sent", urgency=9.5, priority=9.5)
    new_urgent_item = create_sample_radar_item("new-urgent-item", urgency=9.5, priority=9.5)

    res = dispatch_alerts_and_briefing(
        items=[already_sent_item, new_urgent_item],
        bot_token="test_token",
        chat_id="test_chat",
        dry_run=False,
        send_briefing=False,
    )

    # Only 1 new alert should be sent (for 'new-urgent-item')
    assert res["new_urgent_alerts_sent"] == 1
    # Verify save_state was called with both IDs in state
    saved_state = mock_save.call_args[0][0]
    assert "urgent-already-sent" in saved_state["sent_telegram_alert_ids"]
    assert "new-urgent-item" in saved_state["sent_telegram_alert_ids"]


def test_send_telegram_message_error_with_string_status_code_does_not_crash():
    """Regression test: string status codes in error responses must not raise TypeError during logging."""
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = "500"  # string status code
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        # Must return False and not raise TypeError (%d format error)
        result = send_telegram_message(
            "Test message",
            bot_token="test_token_123",
            chat_id="test_chat_456",
            dry_run=False,
        )
        assert result is False
