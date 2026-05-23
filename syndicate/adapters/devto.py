"""
dev.to adapter — full auto-post with canonical URL.

dev.to honors `canonical_url` in the article payload, so SEO juice still
flows to experiencedigest.org. Their API is straightforward; auth is a
single API key from settings → extensions.

API ref: https://developers.forem.com/api/v1#tag/articles/operation/createArticle
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import requests

API_URL = "https://dev.to/api/articles"
TIMEOUT = 30


def _html_to_markdown_ish(html: str) -> str:
    """Cheap fallback when feed only ships HTML. The micro.blog feed usually
    has content_text already, so this rarely runs."""
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _body(item: dict, canonical_url: str) -> str:
    body = item.get("content_text") or _html_to_markdown_ish(item.get("content_html", ""))
    body = body.strip()
    footer = (
        f"\n\n---\n\n*Originally published at "
        f"[experiencedigest.org]({canonical_url}).*"
    )
    return body + footer


def _tags(item: dict) -> list[str]:
    # dev.to accepts up to 4 tags, lowercase, alphanumeric only
    raw = item.get("tags", []) or []
    cleaned = []
    for t in raw:
        t = re.sub(r"[^a-z0-9]", "", t.lower())
        if t and t not in cleaned:
            cleaned.append(t)
        if len(cleaned) == 4:
            break
    return cleaned


def handle(item: dict, dry_run: bool = False) -> dict | None:
    api_key = os.environ.get("DEVTO_API_KEY")
    if not api_key:
        raise RuntimeError("DEVTO_API_KEY not set")

    canonical_url = item.get("url") or item.get("external_url") or ""
    title = (item.get("title") or "").strip()
    if not title or not canonical_url:
        return None

    payload = {
        "article": {
            "title": title,
            "body_markdown": _body(item, canonical_url),
            "canonical_url": canonical_url,
            "published": True,
            "tags": _tags(item),
        }
    }

    if dry_run:
        return {
            "status": "dry-run",
            "canonical_url": canonical_url,
            "tags": payload["article"]["tags"],
        }

    r = requests.post(
        API_URL,
        json=payload,
        headers={"api-key": api_key, "Accept": "application/vnd.forem.api-v1+json"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()

    return {
        "status": "posted",
        "devto_id": data.get("id"),
        "devto_url": data.get("url"),
        "canonical_url": canonical_url,
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }
