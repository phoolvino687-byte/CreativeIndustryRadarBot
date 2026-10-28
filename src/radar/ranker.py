"""Multi-dimensional scoring, classification, and offer verification for Creative Radar.

Scores each item across four independent dimensions:
- Relevance: Utility to professional creators and editors
- Value: Workflow impact, cost savings, performance breakthroughs
- Urgency: Time-criticality (security patches, critical firmware, flash deals)
- Reliability: Source trust level (Official vs Reputable vs Community)

Calculates a composite priority score and parses verified offers (region, eligibility, expiry).
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from src.radar.models import OfferDetails, RadarItem

# Keyword dictionaries for scoring
URGENT_CRITICAL_KEYWORDS = {
    "critical", "security patch", "vulnerability", "zero-day", "hotfix",
    "crash", "corrupt", "bug fix", "exploit", "data loss", "recalled",
    "bricked", "downgrade", "safety advisory",
}

URGENT_TIMED_KEYWORDS = {
    "limited time", "flash deal", "ends today", "expires soon", "24 hours",
    "last chance", "deal of the day", "giveaway ends", "valid until",
}

VALUE_BOOST_KEYWORDS = {
    "free download", "open-source", "open source", "speedup", "accelerated",
    "major release", "new engine", "performance increase", "completely free",
    "breakthrough", "grant", "funding", "100% off", "generative fill",
    "neural", "revolutionary", "game-changer",
}

FIRMWARE_KEYWORDS = {
    "firmware", "firmware update", "firmware version", "system software",
    "lens firmware", "camera firmware",
}

SOFTWARE_UPDATE_KEYWORDS = {
    "released", "version", "update", "patch", "beta", "hotfix", "rollout",
    "v1", "v2", "v3", "v4", "v5", "v19", "v20", "v24", "v25",
}

OFFER_KEYWORDS = {
    "deal", "discount", "sale", "% off", "coupon", "save $", "free download",
    "giveaway", "free for limited time", "promotional", "bundle",
}


def compute_relevance_score(title: str, content: str, category: str) -> float:
    """Calculate relevance to creative professionals on a scale of 1.0 to 10.0."""
    text = f"{title} {content}".lower()
    score = 5.0

    category_boosts = {
        "adobe": ["premiere", "after effects", "photoshop", "illustrator", "creative cloud", "substance", "lightroom"],
        "davinci-blackmagic": ["davinci", "resolve", "blackmagic", "fusion", "fairlight", "braw", "atem", "colorist"],
        "cameras-lenses-firmware": ["camera", "lens", "firmware", "sensor", "mirrorless", "autofocus", "mount", "cinema", "nikon", "sony", "canon", "fujifilm", "panasonic", "lumix", "red"],
        "motion-vfx-blender": ["blender", "vfx", "motion design", "geometry nodes", "cycles", "eevee", "3d", "animation"],
        "design-fonts-plugins": ["typography", "font", "figma", "plugin", "vector", "branding", "layout", "typeface"],
        "ai-tools-offers": ["diffusion", "sora", "gpt", "model", "imagen", "veo", "weights", "generative ai", "lora"],
        "photography-filmmaking-freelance": ["cinematography", "lighting", "client", "freelance", "rate", "contract", "commercial"],
    }

    keywords = category_boosts.get(category, [])
    matches = sum(1 for kw in keywords if kw in text)

    score += min(matches * 0.8, 4.5)
    return round(min(max(score, 1.0), 10.0), 1)


def compute_value_score(title: str, content: str) -> float:
    """Calculate creator value score based on utility, performance, and savings."""
    text = f"{title} {content}".lower()
    score = 5.0

    for kw in VALUE_BOOST_KEYWORDS:
        if kw in text:
            score += 1.0

    # Version bump detection (e.g. 19.0, 4.2, v2.0)
    if re.search(r"\b(?:v\d+(\.\d+)?|\d+\.\d+)\b", text):
        score += 0.8

    return round(min(max(score, 1.0), 10.0), 1)


def compute_urgency_score(title: str, content: str) -> float:
    """Calculate urgency score based on time sensitivity and safety advisories."""
    text = f"{title} {content}".lower()

    for kw in URGENT_CRITICAL_KEYWORDS:
        if kw in text:
            return 9.2

    for kw in URGENT_TIMED_KEYWORDS:
        if kw in text:
            return 8.0

    if any(k in text for k in ["released today", "now available", "immediate", "firmware update", "released"]):
        return 6.0

    return 3.0


def compute_reliability_score(trust_level: str) -> float:
    """Map source trust level to a 1.0 - 10.0 reliability score."""
    mapping = {
        "official": 10.0,
        "reputable": 7.5,
        "community": 5.0,
    }
    return mapping.get(trust_level.lower(), 5.0)


def compute_composite_priority(
    urgency: float,
    value: float,
    relevance: float,
    reliability: float,
) -> float:
    """Calculate composite priority score with transparent weighted formula."""
    composite = (urgency * 0.35) + (value * 0.25) + (relevance * 0.25) + (reliability * 0.15)
    return round(min(max(composite, 1.0), 10.0), 1)


def get_verification_label(trust_level: str) -> str:
    """Generate human-readable trust and verification label."""
    mapping = {
        "official": "Official / Confirmed",
        "reputable": "Reputable Reporting",
        "community": "Community / Unverified",
    }
    return mapping.get(trust_level.lower(), "Reputable Reporting")


def extract_offer_details(title: str, content: str) -> OfferDetails | None:
    """Detect and parse deal discount, region, eligibility, and expiration."""
    combined = f"{title} {content}".lower()

    if not any(kw in combined for kw in OFFER_KEYWORDS):
        return None

    # Discount detection
    discount_match = re.search(r"(\d{1,2}%\s*(?:off|discount)|free\b|100%\s*off|\$\d+\s*off)", combined)
    discount = discount_match.group(1).title() if discount_match else "Verified Deal"

    # Coupon code: look for words like "coupon code XYZ" or "promo code XYZ" or "code: XYZ"
    coupon_match = re.search(r"\b(?:coupon|promo)?\s*code[:\s]+([A-Z0-9_\-]{4,15})\b", combined, re.IGNORECASE)
    if not coupon_match:
        coupon_match = re.search(r"\b(?:coupon|promo)[:\s]+([A-Z0-9_\-]{4,15})\b", combined, re.IGNORECASE)

    raw_code = coupon_match.group(1) if coupon_match else ""
    coupon_code = raw_code.upper() if raw_code.lower() != "code" else ""

    # Region
    region = "Global"
    if "us only" in combined or "north america" in combined:
        region = "US Only"
    elif "eu only" in combined:
        region = "EU Only"

    # Eligibility
    eligibility = "All users"
    if "student" in combined:
        eligibility = "Students & Educators"
    elif "new customer" in combined or "new subscriber" in combined:
        eligibility = "New Subscribers"

    # Expiry detection (e.g., ends nov 3, expires 2026-11-15)
    expires_at = None
    is_expired = False
    expiry_match = re.search(r"(?:ends|expires|valid until)\s+([A-Za-z]{3,9}\s+\d{1,2}(?:,\s*\d{4})?)", combined)
    if expiry_match:
        expires_at = expiry_match.group(1).title()

    return OfferDetails(
        discount=discount,
        coupon_code=coupon_code,
        region=region,
        eligibility=eligibility,
        expires_at=expires_at,
        is_expired=is_expired,
    )


def rank_and_classify(item_dict: dict[str, Any]) -> RadarItem:
    """Perform multi-dimensional ranking and create a structured RadarItem."""
    title = item_dict.get("title", "")
    content = item_dict.get("raw_content", "")
    category = item_dict.get("category", "general")
    trust_level = item_dict.get("trust_level", "reputable")

    relevance = compute_relevance_score(title, content, category)
    value = compute_value_score(title, content)
    urgency = compute_urgency_score(title, content)
    reliability = compute_reliability_score(trust_level)
    composite = compute_composite_priority(urgency, value, relevance, reliability)
    label = get_verification_label(trust_level)

    text_lower = f"{title} {content}".lower()
    is_firmware = any(k in text_lower for k in FIRMWARE_KEYWORDS)
    is_software = any(k in text_lower for k in SOFTWARE_UPDATE_KEYWORDS)
    offer = extract_offer_details(title, content)
    is_offer = offer is not None or category == "ai-tools-offers" and any(k in text_lower for k in OFFER_KEYWORDS)

    return RadarItem(
        id=item_dict["id"],
        title=title,
        link=item_dict.get("link", ""),
        canonical_url=item_dict.get("canonical_url", item_dict.get("link", "")),
        published_at=item_dict.get("published_at", datetime.now(timezone.utc).isoformat()),
        source_id=item_dict.get("source_id", "unknown"),
        source_name=item_dict.get("source_name", "Unknown Source"),
        category=category,
        trust_level=trust_level,
        summary_what="",
        summary_why="",
        summary_action="",
        relevance_score=relevance,
        value_score=value,
        urgency_score=urgency,
        reliability_score=reliability,
        composite_priority=composite,
        verification_label=label,
        is_official=(trust_level == "official"),
        is_offer=is_offer,
        is_firmware=is_firmware,
        is_software_update=is_software,
        tags=list(item_dict.get("tags", [])),
        image_url=item_dict.get("image_url"),
        raw_content=content,
        offer_details=offer,
    )
