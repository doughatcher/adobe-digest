#!/usr/bin/env python3
"""
Experience Digest syndication dispatcher.

Reads the canonical feed.json, identifies posts that haven't been syndicated
to each enabled platform, and dispatches to per-platform adapters.

Run with: just syndicate
Or directly: python3 syndicate.py [--dry-run] [--platforms devto] [--limit N]
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")
load_dotenv(HERE.parent / ".env")

FEED_URL = os.getenv("SYNDICATE_FEED_URL", "https://experiencedigest.org/feed.json")
TRACKING_FILE = HERE / "syndicated.json"


def load_tracking() -> dict:
    if not TRACKING_FILE.exists():
        return {"devto": {}}
    return json.loads(TRACKING_FILE.read_text())


def save_tracking(tracking: dict) -> None:
    TRACKING_FILE.write_text(json.dumps(tracking, indent=2, sort_keys=True) + "\n")


def fetch_feed() -> list[dict]:
    r = requests.get(FEED_URL, timeout=30)
    r.raise_for_status()
    return r.json().get("items", [])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--platforms", default="devto",
                   help="Comma-separated list of platforms to dispatch to")
    p.add_argument("--limit", type=int, default=5,
                   help="Max posts to consider per platform per run")
    p.add_argument("--dry-run", action="store_true",
                   help="Don't write tracking file or send anything")
    args = p.parse_args()

    platforms = [s.strip() for s in args.platforms.split(",") if s.strip()]
    tracking = load_tracking()

    print(f"Fetching {FEED_URL}")
    items = fetch_feed()
    print(f"  {len(items)} items in feed")

    for platform in platforms:
        print(f"\n=== Dispatching to {platform} ===")
        adapter = load_adapter(platform)
        if not adapter:
            print(f"  no adapter for {platform}, skipping")
            continue

        platform_tracking = tracking.setdefault(platform, {})
        unsynd = [it for it in items if it.get("id") not in platform_tracking][:args.limit]

        if not unsynd:
            print(f"  nothing new to syndicate")
            continue

        print(f"  {len(unsynd)} candidates")
        for item in unsynd:
            try:
                result = adapter.handle(item, dry_run=args.dry_run)
            except Exception as e:
                print(f"  ! {item.get('id', '?')}: {type(e).__name__}: {e}")
                continue
            if result is None:
                print(f"  - {item.get('title', '?')[:60]}: skipped (not relevant)")
                continue
            print(f"  + {item.get('title', '?')[:60]}: {result.get('status', '?')}")
            if not args.dry_run:
                platform_tracking[item["id"]] = result

    if not args.dry_run:
        save_tracking(tracking)
        print(f"\nTracking saved to {TRACKING_FILE}")
    return 0


def load_adapter(platform: str):
    try:
        if platform == "devto":
            from adapters import devto
            return devto
    except ImportError as e:
        print(f"  adapter import failed: {e}")
    return None


if __name__ == "__main__":
    sys.exit(main())
