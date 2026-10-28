"""Data models for Creative Radar."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OfferDetails:
    """Detailed attributes for deals, discounts, and offers."""

    discount: str = ""
    coupon_code: str = ""
    region: str = "Global"
    eligibility: str = "All users"
    expires_at: str | None = None
    is_expired: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OfferDetails | None:
        if not data:
            return None
        return cls(
            discount=data.get("discount", ""),
            coupon_code=data.get("coupon_code", ""),
            region=data.get("region", "Global"),
            eligibility=data.get("eligibility", "All users"),
            expires_at=data.get("expires_at"),
            is_expired=bool(data.get("is_expired", False)),
        )


@dataclass
class RadarItem:
    """Normalized intelligence item collected by Creative Radar."""

    id: str
    title: str
    link: str
    canonical_url: str
    published_at: str
    source_id: str
    source_name: str
    category: str
    trust_level: str  # 'official' | 'reputable' | 'community'
    summary_what: str
    summary_why: str
    summary_action: str
    relevance_score: float = 5.0
    value_score: float = 5.0
    urgency_score: float = 3.0
    reliability_score: float = 5.0
    composite_priority: float = 5.0
    verification_label: str = "Reputable Reporting"
    is_official: bool = False
    is_offer: bool = False
    is_firmware: bool = False
    is_software_update: bool = False
    tags: list[str] = field(default_factory=list)
    image_url: str | None = None
    raw_content: str = ""
    offer_details: OfferDetails | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.offer_details:
            d["offer_details"] = self.offer_details.to_dict()
        else:
            d["offer_details"] = None
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RadarItem:
        offer_data = data.get("offer_details")
        offer = OfferDetails.from_dict(offer_data) if offer_data else None
        return cls(
            id=data["id"],
            title=data.get("title", ""),
            link=data.get("link", ""),
            canonical_url=data.get("canonical_url", data.get("link", "")),
            published_at=data.get("published_at", datetime.now(timezone.utc).isoformat()),
            source_id=data.get("source_id", "unknown"),
            source_name=data.get("source_name", "Unknown Source"),
            category=data.get("category", "general"),
            trust_level=data.get("trust_level", "reputable"),
            summary_what=data.get("summary_what", ""),
            summary_why=data.get("summary_why", ""),
            summary_action=data.get("summary_action", ""),
            relevance_score=float(data.get("relevance_score", 5.0)),
            value_score=float(data.get("value_score", 5.0)),
            urgency_score=float(data.get("urgency_score", 3.0)),
            reliability_score=float(data.get("reliability_score", 5.0)),
            composite_priority=float(data.get("composite_priority", 5.0)),
            verification_label=data.get("verification_label", "Reputable Reporting"),
            is_official=bool(data.get("is_official", False)),
            is_offer=bool(data.get("is_offer", False)),
            is_firmware=bool(data.get("is_firmware", False)),
            is_software_update=bool(data.get("is_software_update", False)),
            tags=list(data.get("tags", [])),
            image_url=data.get("image_url"),
            raw_content=data.get("raw_content", ""),
            offer_details=offer,
        )


@dataclass
class RadarSource:
    """Feed source registry entry."""

    id: str
    name: str
    category: str
    url: str
    homepage_url: str = ""
    type: str = "rss"  # 'rss' | 'atom'
    trust_level: str = "reputable"  # 'official' | 'reputable' | 'community'
    enabled: bool = True
    description: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RadarSource:
        return cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            url=data["url"],
            homepage_url=data.get("homepage_url", ""),
            type=data.get("type", "rss").lower(),
            trust_level=data.get("trust_level", "reputable").lower(),
            enabled=bool(data.get("enabled", True)),
            description=data.get("description", ""),
            tags=list(data.get("tags", [])),
        )


@dataclass
class SourceHealth:
    """Health status and performance metrics for a feed."""

    source_id: str
    source_name: str
    category: str
    url: str
    status_code: int = 0
    response_time_ms: float = 0.0
    items_fetched: int = 0
    is_healthy: bool = False
    error_message: str | None = None
    last_checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RadarPayload:
    """Root JSON structure published to GitHub Pages."""

    generated_at: str
    total_items: int
    is_demo: bool
    is_stale: bool
    gemini_enabled: bool
    urgent_alerts_count: int
    items: list[RadarItem] = field(default_factory=list)
    top_categories: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_items": self.total_items,
            "is_demo": self.is_demo,
            "is_stale": self.is_stale,
            "gemini_enabled": self.gemini_enabled,
            "urgent_alerts_count": self.urgent_alerts_count,
            "top_categories": self.top_categories,
            "items": [item.to_dict() for item in self.items],
        }
