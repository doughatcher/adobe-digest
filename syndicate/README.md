# Syndication

Cross-post Experience Digest articles to dev.to while keeping
experiencedigest.org as the canonical source.

## How it works

```
feed.json  →  syndicate.py  →  adapters/devto.py  →  dev.to (auto-post w/ canonical URL)
```

`syndicated.json` tracks what's been syndicated where so we never double-post.

## Why dev.to

dev.to honors `canonical_url` in the article payload — Google attributes
the content to experiencedigest.org, dev.to gets a copy that surfaces to
their audience. No SEO penalty, audience overlap with the Adobe
Commerce/AEM dev crowd is solid.

Reddit and LinkedIn were considered and dropped: Reddit's automod treats
domain repeat-posters as spam regardless of human-in-the-loop nuance, and
LinkedIn's content rules favor manual posting from a human profile.

## Operation

In CI, `.github/workflows/syndicate.yml` runs twice daily, posts new feed
items to dev.to, and commits tracking back to the repo.

Locally:

```bash
just syndicate-install   # one-time, installs requests + python-dotenv
just syndicate-dry       # see what would happen without posting
just syndicate           # run for real
```

## Secrets

Local: `syndicate/.env` (gitignored, copy from `.env.example`).
CI: GitHub Actions secrets, same variable names.

dev.to API key: https://dev.to/settings/extensions

## Adding a new platform

1. Drop `adapters/<platform>.py` with a `handle(item, dry_run) -> dict | None`
   function. Return None to skip, return a dict to record in tracking.
2. Add the platform to the import switch in `syndicate.py:load_adapter`.
3. Add `"<platform>": {}` to `syndicated.json`.
4. Add credentials to `.env.example` and to the GH workflow's `env:` block.

The adapter contract is intentionally tiny — see `adapters/devto.py` for
the canonical shape. Hashnode and Medium both honor canonical URLs the
same way and would be ~80 lines each if dev.to traction warrants more.
