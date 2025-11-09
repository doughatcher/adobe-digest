# GitHub Actions Workflows

This document explains the GitHub Actions workflows used in Adobe Digest.

## Overview

Adobe Digest uses two main workflows to automate scraping and testing:

1. **scrape-and-post.yml** - Production scraping workflow
2. **test.yml** - CI/CD validation workflow

## scrape-and-post.yml

**Purpose:** Scrape sources and post new content to Micro.blog

**Triggers:**
- Schedule: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
- Manual: Via workflow_dispatch with optional parameters

**What it does:**
1. Checks out the repository
2. Sets up Python and installs dependencies
3. Runs `scraper.py` to scrape all configured sources
4. Runs `post_to_microblog.py` to publish up to 5 new posts
5. Commits the updated `scraped_posts.json` tracking file with `[skip ci]`

**Important notes:**
- Uses `[skip ci]` in commit messages to prevent triggering the test workflow
- Requires secrets: `MICROBLOG_TOKEN` and `MICROBLOG_MP_DESTINATION`
- Only publishes a limited number of posts per run to avoid overwhelming feeds

## test.yml

**Purpose:** Validate configuration and code without running the actual scraper

**Triggers:**
- Push to main branch
- Pull requests to main branch
- Manual: Via workflow_dispatch

**What it does:**
1. Validates `sources.yaml` syntax and structure
2. Tests that scraper modules can be imported
3. Tests that ScraperCoordinator can initialize
4. Validates Hugo can build the site
5. Checks for required fields in source configuration

**Important notes:**
- **Does NOT run the actual scraper** - only validates code and configuration
- This prevents duplicate scraping when commits are pushed to main
- The "Validate scraper can initialize" step only creates a coordinator instance without calling `.run()`

## Why Two Workflows?

Having separate workflows ensures:

1. **Separation of concerns**: Testing validates code, scraping produces content
2. **No duplicate work**: Test runs on every push wouldn't duplicate the scheduled scraping
3. **Fast CI/CD**: Tests run quickly without waiting for scraping
4. **Clear intent**: Each workflow has a single, clear purpose

## Workflow Interaction

```
┌─────────────────────┐
│  Schedule (6 hours) │
│  or Manual Trigger  │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│ scrape-and-post.yml │
│  - Scrape sources   │
│  - Post to blog     │
│  - Commit tracking  │
│    with [skip ci]   │
└──────────┬──────────┘
           │
           │ (commits to main with [skip ci])
           v
    ┌──────────────┐
    │  test.yml    │ <- NOT triggered due to [skip ci]
    │  (skipped)   │
    └──────────────┘

┌─────────────────────┐
│  Push to main or PR │
│  (manual or merge)  │
└──────────┬──────────┘
           │
           v
    ┌──────────────┐
    │  test.yml    │
    │  - Validate  │
    │  - Test code │
    │  (NO scrape) │
    └──────────────┘
```

## Common Issues

### Scraper running twice

**Symptom:** The scraper seems to run on every push
**Cause:** Previously, test.yml ran `python3 scraper.py` which executed the full scraper
**Solution:** Changed to only initialize ScraperCoordinator without calling `.run()`

### Test workflow triggered after scrape-and-post

**Symptom:** Test workflow runs after scheduled scraping
**Cause:** `[skip ci]` not in commit message
**Solution:** Ensure scrape-and-post always commits with `[skip ci]` message

## Troubleshooting

### How to run scraper locally

```bash
cd scraper
python3 scraper.py
```

### How to test scraper initialization only

```bash
cd scraper
python3 -c "from scraper import ScraperCoordinator; ScraperCoordinator()"
```

### How to trigger manual scrape

1. Go to Actions tab in GitHub
2. Select "Scrape and Post to Micro.blog" workflow
3. Click "Run workflow"
4. Optionally set number of posts to publish

### How to debug test failures

1. Check the Actions tab for detailed logs
2. Run the same commands locally
3. Verify `sources.yaml` is valid YAML
4. Ensure all scraper modules can be imported

## Future Enhancements

Potential improvements to workflows:

- Add workflow to check for broken links in published posts
- Add workflow to generate analytics reports
- Add workflow to backup content periodically
- Add dependency update automation (Dependabot)
