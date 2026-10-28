"""Main execution pipeline orchestrating Creative Radar.

Coordinates:
Sources -> Fetching -> Parsing -> Normalizing -> Deduplicating ->
Ranking -> Summarizing -> Merging -> Atomic Storage -> Health -> Telegram Notifications.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from src.radar.config import (
    AI_MODEL,
    DATA_DIR,
    DRY_RUN,
    ENABLE_TELEGRAM,
    GEMINI_API_KEY,
    MAX_ITEMS_PER_FEED,
    SOURCES_FILE,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    setup_logger,
)
from src.radar.deduplicator import deduplicate_batch
from src.radar.fetcher import fetch_feed
from src.radar.health import HealthMonitor
from src.radar.models import RadarItem, RadarPayload, RadarSource
from src.radar.normalizer import normalize_item_dict
from src.radar.parser import parse_feed
from src.radar.ranker import rank_and_classify
from src.radar.storage import load_radar_payload, save_radar_payload
from src.radar.summarizer import generate_item_summary
from src.radar.telegram_notifier import dispatch_alerts_and_briefing

logger = setup_logger("radar.pipeline")


def load_sources_registry(sources_path: Path = SOURCES_FILE) -> list[RadarSource]:
    """Load and validate sources from sources.json."""
    if not sources_path.exists():
        logger.error("Sources registry file '%s' does not exist.", sources_path)
        return []

    try:
        with open(sources_path, "r", encoding="utf-8") as f:
            raw_sources = json.load(f)
        sources = [RadarSource.from_dict(s) for s in raw_sources if isinstance(s, dict)]
        logger.info("Loaded %d sources (%d enabled).", len(sources), sum(1 for s in sources if s.enabled))
        return sources
    except Exception as exc:
        logger.error("Failed to load sources registry: %s", exc)
        return []


def run_pipeline(
    sources_path: Path = SOURCES_FILE,
    dry_run: bool = DRY_RUN,
    limit_per_feed: int = MAX_ITEMS_PER_FEED,
    use_ai: bool = True,
    send_telegram: bool = ENABLE_TELEGRAM,
    dashboard_url: str = "",
) -> RadarPayload:
    """Execute complete end-to-end Creative Radar intelligence run."""
    logger.info("==================================================")
    logger.info("Starting Creative Radar Pipeline run (DRY_RUN=%s)", dry_run)
    logger.info("==================================================")

    sources = load_sources_registry(sources_path)
    enabled_sources = [s for s in sources if s.enabled]
    health = HealthMonitor()

    raw_items_batch: list[dict[str, Any]] = []

    # 1. Fetch & Parse all enabled feeds
    for source in enabled_sources:
        xml_content, status_code, elapsed_ms, err_msg = fetch_feed(source)
        if status_code == 200 and xml_content:
            parsed = parse_feed(xml_content, source)
            # Limit per feed to avoid backlog floods
            parsed_limited = parsed[:limit_per_feed]
            health.record_source(
                source_id=source.id,
                source_name=source.name,
                category=source.category,
                url=source.url,
                status_code=status_code,
                response_time_ms=elapsed_ms,
                items_fetched=len(parsed_limited),
                error_message=None,
            )
            raw_items_batch.extend(parsed_limited)
        else:
            health.record_source(
                source_id=source.id,
                source_name=source.name,
                category=source.category,
                url=source.url,
                status_code=status_code,
                response_time_ms=elapsed_ms,
                items_fetched=0,
                error_message=err_msg,
            )

    logger.info("Fetched %d total candidate items across feeds.", len(raw_items_batch))

    # 2. Normalize items
    normalized_items = [normalize_item_dict(raw) for raw in raw_items_batch]

    # 3. Deduplicate batch (favors official/primary sources)
    unique_items_dict = deduplicate_batch(normalized_items)

    # 4. Rank and classify
    ranked_items: list[RadarItem] = [rank_and_classify(d) for d in unique_items_dict]

    # 5. Summarize (Gemini or extractive fallback)
    has_gemini = bool(GEMINI_API_KEY) and use_ai
    logger.info(
        "Summarizing %d items (Gemini AI active: %s, Model: %s)",
        len(ranked_items),
        has_gemini,
        AI_MODEL if has_gemini else "Heuristic Extractive",
    )

    for item in ranked_items:
        what, why, action = generate_item_summary(item, use_ai=has_gemini, api_key=GEMINI_API_KEY)
        item.summary_what = what
        item.summary_why = why
        item.summary_action = action

    # 6. Merge with existing dataset and handle fallback
    existing_payload = load_radar_payload()
    existing_items = existing_payload.items if existing_payload else []

    if not ranked_items and existing_items:
        logger.warning(
            "Fetch yielded 0 new items (network disruption). Preserving %d existing items.",
            len(existing_items),
        )
        final_items = existing_items
    else:
        # Merge by unique ID
        items_by_id: dict[str, RadarItem] = {item.id: item for item in ranked_items}
        for old_item in existing_items:
            if old_item.id not in items_by_id:
                items_by_id[old_item.id] = old_item

        # Sort: priority descending, published_at descending
        sorted_items = sorted(
            items_by_id.values(),
            key=lambda x: (x.composite_priority, x.published_at),
            reverse=True,
        )
        # Retain top 150 items
        final_items = sorted_items[:150]

    # 7. Category counts & urgent count
    cat_counts: dict[str, int] = {}
    urgent_count = 0
    for item in final_items:
        cat_counts[item.category] = cat_counts.get(item.category, 0) + 1
        if item.urgency_score >= 8.5 or item.composite_priority >= 8.5:
            urgent_count += 1

    # 8. Create published payload
    payload = RadarPayload(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_items=len(final_items),
        is_demo=False,
        is_stale=False,
        gemini_enabled=has_gemini,
        urgent_alerts_count=urgent_count,
        items=final_items,
        top_categories=cat_counts,
    )

    # 9. Save published data & health metrics atomically
    save_radar_payload(payload)
    health.save_report(total_items=len(final_items))

    # 10. Telegram notification delivery (optional, disabled by default for website-first workflow)
    if send_telegram and final_items:
        telegram_res = dispatch_alerts_and_briefing(
            items=final_items,
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID,
            dry_run=dry_run,
            dashboard_url=dashboard_url,
            send_briefing=True,
        )
        logger.info("Telegram dispatch completed: %s", telegram_res)
    else:
        logger.info("Telegram notification skipped (website-first mode; send_telegram=%s).", send_telegram)

    logger.info("Pipeline run finished successfully. %d active items published.", len(final_items))
    return payload
