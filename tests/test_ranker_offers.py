"""Tests for multi-dimensional scoring, classification, and offer parsing."""

from src.radar.ranker import (
    compute_composite_priority,
    compute_reliability_score,
    compute_urgency_score,
    compute_value_score,
    extract_offer_details,
    get_verification_label,
    rank_and_classify,
)


def test_compute_urgency_critical_keywords():
    score_critical = compute_urgency_score("Critical Security Patch for Premiere Pro", "Fixes zero-day vulnerability and crash.")
    score_normal = compute_urgency_score("New Interview with Director", "Discussion of color grading choices.")
    assert score_critical >= 9.0
    assert score_normal <= 4.0


def test_reliability_scores():
    assert compute_reliability_score("official") == 10.0
    assert compute_reliability_score("reputable") == 7.5
    assert compute_reliability_score("community") == 5.0
    assert compute_reliability_score("unknown") == 5.0


def test_verification_labels():
    assert get_verification_label("official") == "Official / Confirmed"
    assert get_verification_label("reputable") == "Reputable Reporting"
    assert get_verification_label("community") == "Community / Unverified"


def test_composite_priority_formula():
    # priority = (urgency * 0.35) + (value * 0.25) + (relevance * 0.25) + (reliability * 0.15)
    # e.g.: (10 * 0.35) + (10 * 0.25) + (10 * 0.25) + (10 * 0.15) = 10.0
    score = compute_composite_priority(10.0, 10.0, 10.0, 10.0)
    assert score == 10.0

    score_mid = compute_composite_priority(6.0, 8.0, 8.0, 7.5)
    # (6 * 0.35 = 2.1) + (8 * 0.25 = 2.0) + (8 * 0.25 = 2.0) + (7.5 * 0.15 = 1.125) = 7.225 -> 7.2
    assert score_mid == 7.2


def test_extract_offer_details_complete():
    title = "Autumn Deal: 50% Off Topaz Video AI with Coupon CODE AUTUMN50"
    content = "Special discount for students and creators in North America. Valid until Nov 15, 2026."

    offer = extract_offer_details(title, content)
    assert offer is not None
    assert "50% Off" in offer.discount
    assert offer.coupon_code == "AUTUMN50"
    assert offer.region == "US Only"
    assert "Students" in offer.eligibility
    assert "Nov 15" in (offer.expires_at or "")


def test_rank_and_classify_flags_firmware_and_software():
    raw_item = {
        "id": "firmware-123",
        "title": "Nikon Z8 Firmware 2.0 Released: Major Autofocus Speedup",
        "link": "https://example.com/nikon-z8",
        "canonical_url": "https://example.com/nikon-z8",
        "category": "cameras-lenses-firmware",
        "trust_level": "official",
        "raw_content": "Nikon has released firmware update version 2.0 with improved birds AF tracking.",
        "pub_date_raw": "2026-10-28T09:00:00Z",
    }

    item = rank_and_classify(raw_item)
    assert item.is_official is True
    assert item.is_firmware is True
    assert item.is_software_update is True
    assert item.verification_label == "Official / Confirmed"
    assert item.composite_priority >= 7.0
