"""Tests for URL canonicalization, deduplication, and primary source priority."""

import pytest
from src.radar.deduplicator import deduplicate_batch, title_similarity, tokenize_title
from src.radar.normalizer import canonicalize_url, compute_item_id


def test_canonicalize_url_strips_tracking_params():
    url_with_utm = "https://www.cined.com/sony-a7s-firmware-update/?utm_source=twitter&utm_medium=social&utm_campaign=launch#comments"
    expected = "https://www.cined.com/sony-a7s-firmware-update"
    assert canonicalize_url(url_with_utm) == expected


def test_canonicalize_url_normalizes_trailing_slash_and_domain():
    url = "HTTPS://Blog.Adobe.COM/Premiere-Pro-Update/"
    canonical = canonicalize_url(url)
    assert canonical == "https://blog.adobe.com/premiere-pro-update"


def test_deterministic_item_id():
    url1 = "https://www.cined.com/firmware"
    url2 = "https://www.cined.com/firmware?utm_source=rss"
    id1 = compute_item_id(canonicalize_url(url1), "Firmware Update")
    id2 = compute_item_id(canonicalize_url(url2), "Firmware Update")
    assert id1 == id2
    assert len(id1) == 16


def test_title_similarity_detection():
    title_a = "Sony Releases A7S III Firmware Update 3.02 with Critical Card Bug Fix"
    title_b = "Sony Releases A7S III Firmware Update 3.02 Resolving Card Bug"
    title_c = "Figma Announces New Variable Typography Layout Features"

    sim_ab = title_similarity(title_a, title_b)
    sim_ac = title_similarity(title_a, title_c)

    assert sim_ab > 0.65
    assert sim_ac < 0.2


def test_deduplicate_batch_prioritizes_official_source():
    item_reputable = {
        "id": "item-1",
        "title": "DaVinci Resolve 19.1 Released by Blackmagic Design",
        "canonical_url": "https://www.cined.com/davinci-resolve-19-1-released",
        "category": "davinci-blackmagic",
        "trust_level": "reputable",
        "source_name": "CineD",
        "published_at": "2026-10-28T08:00:00Z",
    }
    item_official = {
        "id": "item-2",
        "title": "DaVinci Resolve 19.1 Released by Blackmagic Design",
        "canonical_url": "https://www.blackmagicdesign.com/media/release/19-1",
        "category": "davinci-blackmagic",
        "trust_level": "official",
        "source_name": "Blackmagic Design Official",
        "published_at": "2026-10-28T08:05:00Z",
    }

    # Even though both report the same story, the official source must win
    batch = [item_reputable, item_official]
    deduped = deduplicate_batch(batch, similarity_threshold=0.65)

    assert len(deduped) == 1
    assert deduped[0]["trust_level"] == "official"
    assert deduped[0]["source_name"] == "Blackmagic Design Official"
