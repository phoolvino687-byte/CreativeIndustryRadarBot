"""Robust XML parser for RSS 2.0 and Atom 1.0 feeds.

Supports standard RSS channels and Atom feeds, media thumbnails,
namespace handling, and graceful regex fallbacks for slightly malformed XML.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from src.radar.config import setup_logger
from src.radar.models import RadarSource

logger = setup_logger("radar.parser")

# Common XML namespaces
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def _clean_xml_string(xml_text: str) -> str:
    """Strip illegal control characters and normalize XML string."""
    if not xml_text:
        return ""
    # Remove control characters except standard whitespace
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", xml_text)
    return cleaned.strip()


def _extract_image_from_html(html_text: str) -> str | None:
    """Extract first high-quality image URL from HTML content."""
    if not html_text:
        return None
    match = re.search(
        r'<img[^>]+src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp|avif))["\']',
        html_text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    return None


def parse_feed(xml_text: str, source: RadarSource) -> list[dict[str, Any]]:
    """Parse RSS or Atom XML string into a list of raw item dictionaries."""
    cleaned_xml = _clean_xml_string(xml_text)
    if not cleaned_xml:
        return []

    try:
        root = ET.fromstring(cleaned_xml)
    except ET.ParseError as err:
        logger.warning(
            "ET ParseError for '%s': %s. Attempting fallback regex parser.",
            source.name,
            err,
        )
        return _fallback_regex_parse(cleaned_xml, source)

    # Determine feed type: Atom has root tag ending with 'feed', RSS has 'rss'
    root_tag = root.tag.lower()
    if root_tag.endswith("feed"):
        return _parse_atom(root, source)
    else:
        return _parse_rss(root, source)


def _parse_rss(root: ET.Element, source: RadarSource) -> list[dict[str, Any]]:
    """Parse standard RSS 2.0 items."""
    items: list[dict[str, Any]] = []
    channel = root.find("channel")
    item_nodes = root.findall(".//item") if channel is None else channel.findall("item")

    for node in item_nodes:
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        pub_date = (node.findtext("pubDate") or "").strip()
        guid = (node.findtext("guid") or link).strip()

        # Description / Content
        desc = (node.findtext("description") or "").strip()
        content = ""
        for tag in ["{http://purl.org/rss/1.0/modules/content/}encoded", "content"]:
            c_node = node.find(tag)
            if c_node is not None and c_node.text:
                content = c_node.text.strip()
                break

        full_body = content or desc

        # Thumbnail / Image discovery
        image_url = None
        # Media thumbnail
        for media_tag in [
            "{http://search.yahoo.com/mrss/}thumbnail",
            "{http://search.yahoo.com/mrss/}content",
            "enclosure",
        ]:
            m_node = node.find(media_tag)
            if m_node is not None:
                m_url = m_node.get("url") or m_node.get("href")
                m_type = m_node.get("type", "")
                if m_url and ("image" in m_type or not m_type or m_url.endswith((".jpg", ".png", ".webp"))):
                    image_url = m_url
                    break

        if not image_url:
            image_url = _extract_image_from_html(full_body)

        if title and (link or guid):
            items.append({
                "title": title,
                "link": link or guid,
                "guid": guid,
                "pub_date_raw": pub_date,
                "raw_content": full_body,
                "image_url": image_url,
                "source_id": source.id,
                "source_name": source.name,
                "category": source.category,
                "trust_level": source.trust_level,
            })

    return items


def _find_first(node: ET.Element, tags: list[str]) -> ET.Element | None:
    """Find the first matching child element among alternative tag names."""
    for tag in tags:
        el = node.find(tag)
        if el is not None:
            return el
    return None


def _parse_atom(root: ET.Element, source: RadarSource) -> list[dict[str, Any]]:
    """Parse Atom 1.0 entries (including YouTube channel feeds)."""
    items: list[dict[str, Any]] = []
    # Atom tags may be namespaced or unnamespaced
    entry_nodes = root.findall("{http://www.w3.org/2005/Atom}entry")
    if not entry_nodes:
        entry_nodes = root.findall("entry")

    for node in entry_nodes:
        title_el = _find_first(node, ["{http://www.w3.org/2005/Atom}title", "title"])
        title = (title_el.text or "").strip() if title_el is not None else ""

        # Link: find alternate or default link href
        link = ""
        for link_el in node.findall("{http://www.w3.org/2005/Atom}link") + node.findall("link"):
            rel = link_el.get("rel", "alternate")
            if rel in ("alternate", "") and link_el.get("href"):
                link = link_el.get("href", "").strip()
                break
        if not link:
            id_el = _find_first(node, ["{http://www.w3.org/2005/Atom}id", "id"])
            if id_el is not None and id_el.text and id_el.text.startswith("http"):
                link = id_el.text.strip()

        # Dates: published or updated
        pub_date = ""
        for date_tag in ["{http://www.w3.org/2005/Atom}published", "published", "{http://www.w3.org/2005/Atom}updated", "updated"]:
            d_el = node.find(date_tag)
            if d_el is not None and d_el.text:
                pub_date = d_el.text.strip()
                break

        # Content / Summary
        body = ""
        for body_tag in [
            "{http://www.w3.org/2005/Atom}content",
            "content",
            "{http://www.w3.org/2005/Atom}summary",
            "summary",
            "{http://search.yahoo.com/mrss/}group",
        ]:
            b_el = node.find(body_tag)
            if b_el is not None:
                if body_tag.endswith("group"):
                    desc_el = b_el.find("{http://search.yahoo.com/mrss/}description")
                    if desc_el is not None and desc_el.text:
                        body = desc_el.text.strip()
                        break
                elif b_el.text:
                    body = b_el.text.strip()
                    break

        # Thumbnail
        image_url = None
        for thumb_tag in [
            "{http://search.yahoo.com/mrss/}thumbnail",
            "{http://search.yahoo.com/mrss/}group/{http://search.yahoo.com/mrss/}thumbnail",
        ]:
            t_el = node.find(thumb_tag)
            if t_el is not None and t_el.get("url"):
                image_url = t_el.get("url")
                break

        if not image_url:
            image_url = _extract_image_from_html(body)

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "guid": link,
                "pub_date_raw": pub_date,
                "raw_content": body,
                "image_url": image_url,
                "source_id": source.id,
                "source_name": source.name,
                "category": source.category,
                "trust_level": source.trust_level,
            })

    return items


def _fallback_regex_parse(xml_text: str, source: RadarSource) -> list[dict[str, Any]]:
    """Emergency regex parser if ElementTree fails due to unescaped entities."""
    items: list[dict[str, Any]] = []
    item_blocks = re.findall(r"<(?:item|entry)[\s>](.*?)</(?:item|entry)>", xml_text, re.DOTALL | re.IGNORECASE)

    for block in item_blocks:
        title_match = re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL | re.IGNORECASE)
        link_match = re.search(r"<link[^>]*href=[\"']([^\"']+)[\"']", block, re.IGNORECASE)
        if not link_match:
            link_match = re.search(r"<link[^>]*>(?:<!\[CDATA\[)?(https?://[^<]+)(?:\]\]>)?</link>", block, re.IGNORECASE)
        date_match = re.search(r"<(?:pubDate|published|updated)[^>]*>(.*?)</(?:pubDate|published|updated)>", block, re.IGNORECASE)
        desc_match = re.search(r"<(?:description|summary|content)[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</(?:description|summary|content)>", block, re.DOTALL | re.IGNORECASE)

        title = title_match.group(1).strip() if title_match else ""
        link = link_match.group(1).strip() if link_match else ""
        pub_date = date_match.group(1).strip() if date_match else ""
        raw_content = desc_match.group(1).strip() if desc_match else ""

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "guid": link,
                "pub_date_raw": pub_date,
                "raw_content": raw_content,
                "image_url": _extract_image_from_html(raw_content),
                "source_id": source.id,
                "source_name": source.name,
                "category": source.category,
                "trust_level": source.trust_level,
            })

    return items
