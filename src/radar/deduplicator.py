"""Deduplication and primary-source prioritization for Creative Radar.

Deduplicates items by canonical URL, deterministic ID, and title similarity.
When duplicate stories are found across multiple outlets, primary/official sources
are strictly prioritized over aggregators and community blogs.
"""

from __future__ import annotations

import re
from typing import Any

from src.radar.config import setup_logger

logger = setup_logger("radar.deduplicator")

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "of", "at", "by",
    "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up",
    "down", "in", "out", "on", "off", "over", "under", "again", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "shall", "should", "can", "could", "this", "that",
}

TRUST_WEIGHTS = {
    "official": 3,
    "reputable": 2,
    "community": 1,
}


def tokenize_title(title: str) -> set[str]:
    """Extract significant lowercase alphanumeric tokens from title."""
    words = re.findall(r"\b[a-zA-Z0-9]{2,}\b", title.lower())
    return {w for w in words if w not in STOPWORDS}


def title_similarity(title_a: str, title_b: str) -> float:
    """Compute Jaccard token similarity between two titles."""
    tokens_a = tokenize_title(title_a)
    tokens_b = tokenize_title(title_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)


def _is_better_source(candidate: dict[str, Any], existing: dict[str, Any]) -> bool:
    """Return True if candidate has higher trust level or earlier publication date."""
    cand_weight = TRUST_WEIGHTS.get(candidate.get("trust_level", "community"), 1)
    exist_weight = TRUST_WEIGHTS.get(existing.get("trust_level", "community"), 1)

    if cand_weight > exist_weight:
        return True
    if cand_weight < exist_weight:
        return False

    # If trust is equal, prefer the earlier publication date
    return candidate.get("published_at", "") < existing.get("published_at", "")


def deduplicate_batch(items: list[dict[str, Any]], similarity_threshold: float = 0.70) -> list[dict[str, Any]]:
    """Deduplicate a list of items, favoring primary and higher-trust sources.

    Checks:
    1. Exact canonical URL match
    2. Exact item ID match
    3. Title semantic Jaccard similarity (>= threshold)
    """
    by_url: dict[str, dict[str, Any]] = {}

    for item in items:
        canon_url = item.get("canonical_url", "")
        item_id = item.get("id", "")
        key = canon_url or item_id

        if not key:
            continue

        if key in by_url:
            if _is_better_source(item, by_url[key]):
                logger.debug(
                    "Replacing duplicate '%s' (%s) with higher-trust source '%s' (%s)",
                    by_url[key].get("title"),
                    by_url[key].get("source_name"),
                    item.get("title"),
                    item.get("source_name"),
                )
                by_url[key] = item
        else:
            by_url[key] = item

    # Second pass: Semantic title similarity across different URLs
    unique_items: list[dict[str, Any]] = []
    for item in by_url.values():
        is_duplicate = False
        for idx, existing in enumerate(unique_items):
            # Check if same category and similar title
            if item.get("category") == existing.get("category"):
                sim = title_similarity(item.get("title", ""), existing.get("title", ""))
                if sim >= similarity_threshold:
                    is_duplicate = True
                    if _is_better_source(item, existing):
                        logger.debug(
                            "Similarity collision (%.2f): keeping primary source '%s' over '%s'",
                            sim,
                            item.get("source_name"),
                            existing.get("source_name"),
                        )
                        unique_items[idx] = item
                    break

        if not is_duplicate:
            unique_items.append(item)

    logger.info("Deduplication: reduced %d items to %d unique items.", len(items), len(unique_items))
    return unique_items
