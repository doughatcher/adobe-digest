# Deduplication Analysis & Solution

## Current Pipeline

### 1. Scraper (`scraper.py`)
- Loads existing posts from **live feed** (`https://adobedigest.com/feed.json`)
- Extracts IDs from feed (APSB IDs and Sansec slugs)
- Passes `existing_posts` set to individual scrapers
- **Limitation**: Feed only returns 20 most recent items (JSON Feed spec)

### 2. Individual Scrapers (`adobe_helpx.py`, `sansec_io.py`)
- Check if bulletin/article ID is in `existing_posts` set
- Skip if found, scrape if not
- **Problem**: Only checking against 20 items from feed

### 3. Post to Micro.blog (`post_to_microblog.py`)
- Also loads from live feed
- Checks both IDs and titles for duplicates
- **Same problem**: Only checking against 20 items

## Root Cause of Duplicates

**The feed.json only returns the 20 most recent posts**, but we have 90+ posts total. This means:
- Posts older than the 20 most recent are not in the deduplication check
- When scraper runs, it thinks posts #21-90 don't exist
- Creates duplicate markdown files
- Tries to post them to Micro.blog (which may create duplicates)

## Solutions

### Option 1: Track IDs in Git (Persistent State File)
**Best for reliability**

Create a `scraped_posts.json` file in the repo to track all scraped IDs:

```json
{
  "apsb_ids": ["APSB25-01", "APSB24-99", ...],
  "sansec_slugs": ["sessionreaper-attacks", "defunct-dat", ...],
  "last_updated": "2025-11-03T12:00:00Z"
}
```

**Pros:**
- Complete history, not limited to feed size
- Works even if feed is unavailable
- Git-tracked for audit trail

**Cons:**
- Requires committing scraped_posts.json after each run
- Slightly more complex workflow

### Option 2: Use Micro.blog's Full Feed
**Best for simplicity**

Query Micro.blog's Micropub source endpoint to get ALL posts:

```python
GET https://micro.blog/micropub?q=source&limit=1000
Authorization: Bearer TOKEN
```

**Pros:**
- No need to track state in git
- Always current with live site
- Simple implementation

**Cons:**
- Depends on Micro.blog API
- May hit rate limits with large datasets
- Need to handle pagination

### Option 3: Check Local Filesystem First
**Quickest fix**

Before scraping, scan local markdown files for existing IDs:

```python
def get_local_ids():
    ids = set()
    for md_file in Path('content').rglob('*.md'):
        # Extract ID from filename or content
        ids.add(extract_id(md_file))
    return ids
```

**Pros:**
- No external dependencies
- Fast
- Works offline

**Cons:**
- Files can be manually deleted
- No verification against live site
- Can get out of sync

### Option 4: Hybrid Approach (RECOMMENDED)
**Best balance of reliability and simplicity**

Combine all sources for deduplication:
1. Check scraped_posts.json (if exists)
2. Check live feed
3. Check local filesystem

Use the union of all three sources as `existing_posts`.

## Implementation Plan

### Immediate Fix (Option 4 - Hybrid)

1. Update `scraper.py` to check multiple sources:
   ```python
   def load_existing_posts(self):
       existing = set()
       
       # Source 1: scraped_posts.json
       if Path('scraped_posts.json').exists():
           existing.update(self.load_from_json())
       
       # Source 2: Live feed (up to 20 items)
       existing.update(self.load_from_feed())
       
       # Source 3: Local markdown files
       existing.update(self.scan_local_files())
       
       return existing
   ```

2. Update `scraped_posts.json` after each scrape:
   ```python
   def save_scraped_ids(self, new_ids):
       data = self.load_scraped_data()
       data['ids'].update(new_ids)
       data['last_updated'] = datetime.now().isoformat()
       with open('scraped_posts.json', 'w') as f:
           json.dump(data, f, indent=2)
   ```

3. Update GitHub Action to commit scraped_posts.json:
   ```yaml
   - name: Commit scraped IDs
     run: |
       cd content
       git add scraped_posts.json
       git commit -m "Update scraped post IDs" || true
       git push || true
   ```

4. Keep `post_to_microblog.py` checking feed for final validation

### Long-term Enhancement

Add a cleanup command to reconcile all sources:
```bash
python3 scraper.py --reconcile
```

This would:
- Query full Micro.blog feed via API
- Compare with local files
- Update scraped_posts.json
- Remove orphaned local files
- Report discrepancies

## Testing Plan

1. Manually create scraped_posts.json with current 90 posts
2. Run scraper locally - should create 0 new files
3. Add a new bulletin to Adobe's page
4. Run scraper - should create exactly 1 file
5. Verify scraped_posts.json updated
6. Run again - should create 0 files (duplicate check working)

## Migration Steps

1. Generate initial scraped_posts.json from current posts
2. Deploy updated scraper.py
3. Deploy updated GitHub Action
4. Test with manual workflow run
5. Monitor for duplicates in next scheduled run
