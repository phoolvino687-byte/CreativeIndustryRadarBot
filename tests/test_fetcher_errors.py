from unittest.mock import MagicMock, patch
import requests
from src.radar.fetcher import fetch_feed
from src.radar.models import RadarSource
from src.radar.parser import parse_feed


def create_test_source(url="https://example.com/feed.xml") -> RadarSource:
    return RadarSource(
        id="test-source",
        name="Test News",
        category="cameras-lenses-firmware",
        url=url,
        trust_level="reputable",
        enabled=True,
    )


def test_fetch_feed_handles_404_cleanly():
    source = create_test_source()
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.reason = "Not Found"
    mock_session.get.return_value = mock_response

    content, status_code, elapsed_ms, error = fetch_feed(source, session=mock_session)

    assert status_code == 404
    assert content == ""
    assert error is not None
    assert "404" in error


def test_fetch_feed_handles_500_cleanly():
    source = create_test_source()
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.reason = "Internal Server Error"
    mock_session.get.return_value = mock_response

    content, status_code, elapsed_ms, error = fetch_feed(source, session=mock_session)

    assert status_code == 500
    assert content == ""
    assert "500" in error


def test_fetch_feed_handles_timeout():
    source = create_test_source()
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.Timeout("Connection timed out")

    content, status_code, elapsed_ms, error = fetch_feed(source, session=mock_session)

    assert status_code == 408
    assert content == ""
    assert "timed out" in error.lower()


def test_parse_feed_handles_malformed_xml_via_fallback():
    source = create_test_source()
    # Malformed XML missing root close tag or unescaped ampersand
    malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Malformed Feed & Unescaped</title>
        <item>
          <title>Canon EOS R5 Update & Bugfix</title>
          <link>https://example.com/canon-update</link>
          <pubDate>Mon, 28 Oct 2026 08:00:00 GMT</pubDate>
          <description>Firmware fix for R5 & R6 cameras.</description>
        </item>
    """  # Intentionally truncated XML

    items = parse_feed(malformed_xml, source)
    assert len(items) == 1
    assert "Canon EOS R5" in items[0]["title"]
    assert items[0]["link"] == "https://example.com/canon-update"


def test_parse_feed_returns_empty_on_garbage():
    source = create_test_source()
    items = parse_feed("NOT XML AT ALL 12345", source)
    assert items == []
