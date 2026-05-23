# RSS Feed Configuration

## Overview

Experience Digest uses micro.blog's canonical JSON feed as the single source of truth for RSS subscriptions. This simplifies feed management and ensures reliable delivery since micro.blog handles feed generation on its own schedule.

## Primary Feed

**URL**: `https://experiencedigest.org/feed.json`

This is the only internal feed advertised to subscribers. It is automatically generated and maintained by micro.blog.

## Feed Discovery

The following `<link>` tag is included in the HTML `<head>` for feed auto-discovery:

```html
<link href="https://experiencedigest.org/feed.json" rel="alternate" type="application/json" title="Experience Digest" />
```

## External Data Sources

The homepage references these external feeds for transparency about data sourcing (these are **not** Experience Digest feeds—they are third-party sources we monitor):

| Source | Feed URL | Purpose |
|--------|----------|---------|
| Sansec Research | `https://sansec.io/atom.xml` | Security research articles |
| Akamai Blog | `https://feeds.feedburner.com/akamai/blog` | Filtered for Adobe topics |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    micro.blog                           │
│  (automatically generates and hosts feed.json)          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│           https://experiencedigest.org/feed.json             │
│                  (canonical feed URL)                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                RSS Readers / Subscribers                │
└─────────────────────────────────────────────────────────┘
```

## Why Not Hugo-Generated Feeds?

Hugo can generate RSS/JSON feeds, but micro.blog builds the site on its own schedule and doesn't reliably regenerate XML outputs. Using micro.blog's canonical `feed.json` ensures:

1. **Reliable updates** — micro.blog manages feed generation automatically
2. **No stale feeds** — Avoids empty or outdated XML files from Hugo builds
3. **Simpler maintenance** — No custom RSS templates to maintain
4. **Micro.blog compatibility** — Works seamlessly with the platform's feed infrastructure

## Cleanup Completed (February 2026)

The following legacy files were removed:

- `/static/adobe-security.xml` — Outdated static RSS feed
- `/static/feeds/*.xml` — 39 product-specific XML files that were broken/unused
- `/layouts/feeds/list.html` — Undiscoverable feeds listing page with broken links

## Future Considerations

If product-specific feeds are needed in the future, consider:

1. Using micro.blog's category feeds (`/categories/{name}/feed.json`)
2. Building a separate feed generation pipeline outside of Hugo
3. Re-evaluating Hugo RSS templates if micro.blog's build behavior changes
