# Micro.blog Integration

This repository automatically posts Adobe security bulletins to Micro.blog using the Micropub API.

## Setup

### 1. Get Your Micro.blog App Token

1. Log in to [Micro.blog](https://micro.blog/)
2. Go to [Account → App tokens](https://micro.blog/account/apps)
3. Click "Generate App Token"
4. Give it a name like "Adobe Digest Scraper"
5. Copy the token

### 2. Add GitHub Secret

1. Go to your repository's Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `MICROBLOG_TOKEN`
4. Value: Paste your app token
5. Click "Add secret"

### 3. Configure baseURL (if needed)

Make sure your `config.json` has the correct `baseURL`:

```json
{
  "baseURL": "https://adobedigest.com/"
}
```

## How It Works

### Automated Workflow

The GitHub Action (`.github/workflows/scrape-and-post.yml`) runs daily and:

1. **Scrapes** Adobe security bulletins from helpx.adobe.com
2. **Commits** any new bulletins to the repository
3. **Builds** the Hugo site with the new content
4. **Deploys** to GitHub Pages (adobedigest.com)
5. **Waits** 30 seconds for deployment to complete
6. **Posts** new bulletins to Micro.blog (max 5 per run by default)

### State Tracking

The scraper uses your published `feed.json` at `https://adobedigest.com/feed.json` to track which bulletins have already been posted. This means:

- ✅ No separate state file needed
- ✅ Idempotent - safe to run multiple times
- ✅ Can manually trigger to catch up
- ✅ Resilient to workflow failures

### Manual Triggering

You can manually trigger the workflow:

1. Go to Actions → "Scrape and Post to Micro.blog"
2. Click "Run workflow"
3. Optionally set the limit (default is 5 posts)
4. Click "Run workflow"

## Local Development

### Setup Environment

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Micro.blog token:
   ```bash
   MICROBLOG_TOKEN=your_app_token_here
   ```

### Install Dependencies

```bash
cd content
pip install -r requirements.txt
```

### Run Scraper

```bash
cd content
python3 scraper.py
```

### Test Posting to Micro.blog

```bash
cd content
python3 post_to_microblog.py
```

Limit the number of posts:
```bash
python3 post_to_microblog.py 3  # Post max 3 bulletins
```

## Micropub API

The poster uses Micro.blog's [Micropub API](https://help.micro.blog/t/posting-api/96) which is a W3C standard for posting to your blog.

### Post Format

Each bulletin is posted with:
- **Title**: APSB ID and product name
- **Content**: Full bulletin details including:
  - Summary
  - Bulletin information (ID, date, priority, severity)
  - Affected versions
  - Solution
  - Vulnerability details
  - CVE identifiers
  - Link to full bulletin

### Rate Limiting

The workflow posts a maximum of 5 bulletins per run by default to avoid rate limiting. If there are more than 5 new bulletins, they will be posted in the next scheduled run.

## Troubleshooting

### Posts not appearing on Micro.blog

1. Check that your `MICROBLOG_TOKEN` is correct
2. Verify the token has posting permissions
3. Check the Actions logs for error messages
4. Try manually running the workflow

### Duplicate posts

This shouldn't happen because the scraper checks the published feed, but if it does:
- Delete the duplicate from Micro.blog
- Wait for the feed to update (may take a few minutes)
- Re-run the workflow

### Missing posts

If posts were scraped but not posted to Micro.blog:
- Check that GitHub Pages deployed successfully
- Verify `adobedigest.com/feed.json` is accessible
- Manually trigger the workflow

## Configuration

### Change posting schedule

Edit `.github/workflows/scrape-and-post.yml`:

```yaml
on:
  schedule:
    - cron: '0 14 * * *'  # Daily at 2 PM UTC
```

### Change post limit

Edit the default in the workflow file or pass it when manually triggering.

### Customize post format

Edit `content/post_to_microblog.py` in the `post_to_microblog()` method to change how posts are formatted.
