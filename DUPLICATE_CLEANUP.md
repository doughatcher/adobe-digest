# Duplicate Cleanup Guide

## Problem
When the scraper created posts, some duplicates were generated on Micro.blog because:
1. The deduplication system wasn't checking all sources
2. Multiple posts were created with random hex IDs (e.g., `23e5ac.html`, `7fad15.html`)
3. These duplicates exist on the live site but not in local markdown files

## Solution Options

### Option 1: Automated Cleanup via API (Recommended for Tech Users)

Use the `cleanup_duplicates.py` script:

```bash
# 1. Dry run to see what would be deleted (feed only, ~20 recent posts)
cd content
python3 cleanup_duplicates.py

# 2. Dry run with full API access (up to 1000 posts)
python3 cleanup_duplicates.py --api

# 3. Actually delete duplicates (USE WITH CAUTION)
python3 cleanup_duplicates.py --api --delete

# 4. See detailed help
python3 cleanup_duplicates.py --help-guide
```

**How it works:**
- Fetches posts from Micro.blog (via feed or API)
- Groups posts by title to find duplicates
- Keeps the OLDEST post (first published)
- Deletes newer duplicates via Micropub API

**Pros:**
- ✅ Automated and fast
- ✅ Can handle many duplicates at once
- ✅ Dry-run mode for safety

**Cons:**
- ⚠️ Cannot undo deletions
- ⚠️ Requires API access
- ⚠️ Feed method only sees 20 recent posts

### Option 2: Manual Cleanup via Web UI (Safest)

Delete duplicates manually through Micro.blog's interface:

1. Go to https://micro.blog/posts
2. Find posts with duplicate titles
3. For each duplicate:
   - Click into the post
   - Click the "..." menu
   - Select "Delete"
4. Keep the version with the clean URL (e.g., `found-defunctdat-on-your-site.html`)
5. Delete versions with random IDs (e.g., `23e5ac.html`, `7fad15.html`)

**Pros:**
- ✅ Full control over what gets deleted
- ✅ Can preview each post before deleting
- ✅ Can undo if you delete by mistake (sometimes)

**Cons:**
- ⏱️ Time-consuming for many duplicates
- 🖱️ Manual clicking required

### Option 3: Leave Them (Do Nothing)

The duplicates are now prevented going forward by the new deduplication system:
- `scraped_posts.json` tracks all scraped IDs
- Scraper checks 3 sources (tracking file, feed, local files)
- Won't create new duplicates

**Pros:**
- ✅ Zero risk
- ✅ No work required
- ✅ Old posts eventually fall off feed

**Cons:**
- ⚠️ Duplicates remain visible on site
- ⚠️ Confusing for visitors
- ⚠️ Wastes space

## Current State

From the most recent feed (20 posts), found:
- **1 title with duplicates**: "Found defunct.dat on your site? You've got a problem"
- **5 total copies**, 4 would be deleted
- URLs with random IDs: `000000.html`, `23e5ac.html`, `7fad15.html`, `f07193.html`
- Clean URL: `found-defunctdat-on-your-site.html`

**Note:** This is only from the 20 most recent posts in the feed. There may be more duplicates in older posts.

## Recommended Action Plan

### Step 1: Assess the Scope
```bash
python3 cleanup_duplicates.py --api
```
This will show ALL duplicates across up to 1000 posts.

### Step 2: Review the List
Carefully review what would be deleted. The tool keeps the oldest post for each title.

### Step 3: Choose Your Method

**If comfortable with API and <50 duplicates:**
```bash
python3 cleanup_duplicates.py --api --delete
```

**If you want manual control or >50 duplicates:**
Use the web UI method described above.

**If duplicates are minimal:**
Leave them - they'll naturally fall off the feed over time.

### Step 4: Verify
After cleanup, check:
- https://adobedigest.com/ - Homepage should show no duplicates
- https://adobedigest.com/feed.json - Feed should have unique titles
- https://micro.blog/posts - Your posts list should be clean

## Prevention (Already Implemented ✅)

The new system prevents future duplicates:

1. **Tracking File** (`scraped_posts.json`)
   - Stores all scraped IDs in git
   - Committed after each scraper run
   - Complete history, not limited to feed size

2. **Hybrid Deduplication**
   - Checks tracking file (all IDs)
   - Checks live feed (verification)
   - Checks local files (backup)
   - Takes union of all sources

3. **Sansec ID Handling**
   - Tracks both slug and filename formats
   - Handles backwards compatibility

4. **GitHub Action**
   - Automatically commits tracking file
   - Uses `[skip ci]` to avoid recursive builds

## Troubleshooting

### "Could not load existing posts from feed"
- Check internet connection
- Verify https://adobedigest.com/feed.json is accessible
- May need to wait a few minutes after posting

### "MICROBLOG_TOKEN not set"
- Ensure `.env` file exists in `content/` directory
- Check token is valid: https://micro.blog/account/apps

### "Failed to delete: 403 Forbidden"
- Token may not have delete permissions
- Try regenerating token at https://micro.blog/account/apps
- Ensure token is for the correct account

### Deletions not showing immediately
- Micro.blog may cache for a few minutes
- Wait 5-10 minutes and refresh
- Check both .com and .micro.blog URLs

## API Limitations

- **Micropub source query**: Limited to 1000 posts max
- **Rate limiting**: May hit limits with >100 rapid requests
- **JSON Feed**: Limited to ~20 most recent items
- **Pagination**: Not yet implemented (would need multiple API calls)

If you have >1000 posts, you'll need to:
1. Run cleanup multiple times as older posts rotate into the 1000-item window
2. Or use manual web UI cleanup
3. Or contact Micro.blog support for bulk operations
