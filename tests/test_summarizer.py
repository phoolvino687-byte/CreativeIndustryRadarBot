"""Tests for AI structured summarization, fallback handling, quota exhaustion, and injection defense."""

import json
from unittest.mock import MagicMock, patch
import requests

from src.radar.models import RadarItem
from src.radar.summarizer import (
    extractive_summarize,
    generate_item_summary,
    split_sentences,
    summarize_with_gemini,
)


def create_sample_item(is_firmware=False, is_offer=False) -> RadarItem:
    return RadarItem(
        id="test-item-1",
        title="Sony Announces A7S III Firmware Update 3.02 Resolving CFexpress Lockups",
        link="https://www.cined.com/sony-firmware",
        canonical_url="https://www.cined.com/sony-firmware",
        published_at="2026-10-28T09:00:00Z",
        source_id="cined-gear",
        source_name="CineD",
        category="cameras-lenses-firmware",
        trust_level="reputable",
        summary_what="",
        summary_why="",
        summary_action="",
        is_firmware=is_firmware,
        is_offer=is_offer,
        raw_content=(
            "Sony has released firmware version 3.02 for the A7S III. "
            "This critical update fixes an issue where CFexpress Type A media cards caused random write halts during 4K recording. "
            "It improves overall recording stability and camera responsiveness during extended takes. "
            "Shooters should install the update using a fully charged battery."
        ),
    )


def test_sentence_splitter_preserves_version_numbers():
    text = "Blender 4.3 released with v1.2 compatibility. Next sentence starts here."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert "4.3" in sentences[0]
    assert "v1.2" in sentences[0]


def test_extractive_summarize_returns_valid_three_part_tuple():
    item = create_sample_item(is_firmware=True)
    what, why, action = extractive_summarize(item)

    assert what != ""
    assert why != ""
    assert action != ""
    assert "Sony" in what
    assert "firmware" in action.lower() or "camera" in action.lower()


def test_missing_api_key_gracefully_falls_back_to_extractive():
    item = create_sample_item()
    # Call with empty API key
    what, why, action = generate_item_summary(item, use_ai=True, api_key="")
    assert what != ""
    assert why != ""
    assert action != ""


@patch("requests.post")
def test_quota_exhaustion_429_falls_back_gracefully(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = json.dumps({"error": {"message": "Resource has been exhausted (e.g. check quota)."}})
    mock_post.return_value = mock_resp

    item = create_sample_item()
    result = summarize_with_gemini(item, api_key="dummy_key_12345")

    # summarize_with_gemini returns None on 429, causing generate_item_summary to fallback
    assert result is None

    what, why, action = generate_item_summary(item, use_ai=True, api_key="dummy_key_12345")
    assert what != ""
    assert why != ""
    assert action != ""


@patch("requests.post")
def test_malformed_json_response_falls_back_gracefully(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # Gemini response with malformed candidate text (not JSON)
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Sorry, I am unable to analyze this properly."}]
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    item = create_sample_item()
    what, why, action = generate_item_summary(item, use_ai=True, api_key="dummy_key_12345")
    assert what != ""
    assert why != ""
    assert action != ""


@patch("requests.post")
def test_valid_gemini_json_response_parsed_correctly(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "what_happened": "Sony released firmware 3.02 for the A7S III fixing card write lockups.",
                                "why_it_matters": "Prevents catastrophic clip loss during 4K high-framerate shoots.",
                                "practical_next_steps": "Update immediately via Sony official site using a formatted SD card."
                            })
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    item = create_sample_item()
    what, why, action = generate_item_summary(item, use_ai=True, api_key="dummy_key_12345")
    assert "Sony released firmware 3.02" in what
    assert "Prevents catastrophic clip loss" in why
    assert "Update immediately" in action
