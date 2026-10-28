"""Feed source health monitoring and diagnostics for Creative Radar.

Tracks HTTP status codes, latency, yield counts, and error states across all feeds.
Publishes data/health.json for the dashboard health diagnostics modal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.radar.config import HEALTH_JSON_FILE, setup_logger
from src.radar.models import SourceHealth
from src.radar.storage import write_json_atomic

logger = setup_logger("radar.health")


class HealthMonitor:
    """Collects and aggregates per-source health status metrics."""

    def __init__(self) -> None:
        self.metrics: dict[str, SourceHealth] = {}
        self.start_time = datetime.now(timezone.utc)

    def record_source(
        self,
        source_id: str,
        source_name: str,
        category: str,
        url: str,
        status_code: int,
        response_time_ms: float,
        items_fetched: int,
        error_message: str | None = None,
    ) -> SourceHealth:
        """Record the execution outcome of an individual feed fetch."""
        is_healthy = (status_code == 200 and items_fetched >= 0 and error_message is None)
        metric = SourceHealth(
            source_id=source_id,
            source_name=source_name,
            category=category,
            url=url,
            status_code=status_code,
            response_time_ms=round(response_time_ms, 1),
            items_fetched=items_fetched,
            is_healthy=is_healthy,
            error_message=error_message,
            last_checked_at=datetime.now(timezone.utc).isoformat(),
        )
        self.metrics[source_id] = metric
        return metric

    def build_report(self, total_items_active: int = 0) -> dict[str, Any]:
        """Generate full health diagnostic report."""
        sources_list = [m.to_dict() for m in self.metrics.values()]
        healthy_count = sum(1 for m in self.metrics.values() if m.is_healthy)
        failing_count = len(self.metrics) - healthy_count

        return {
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
            "total_sources_monitored": len(self.metrics),
            "healthy_sources": healthy_count,
            "failing_sources": failing_count,
            "total_active_radar_items": total_items_active,
            "overall_system_status": "Operational" if failing_count == 0 else ("Degraded" if healthy_count > 0 else "Down"),
            "sources": sources_list,
        }

    def save_report(self, target_file: Path = HEALTH_JSON_FILE, total_items: int = 0) -> None:
        """Write health metrics report atomically to disk."""
        report = self.build_report(total_items_active=total_items)
        write_json_atomic(target_file, report)
        logger.info(
            "Health report saved: %d/%d sources healthy.",
            report["healthy_sources"],
            report["total_sources_monitored"],
        )
