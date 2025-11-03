# Micro.blog Multi-Blog Configuration

## Summary

Successfully configured the Adobe Digest scraper to post to the correct Micro.blog blog when you have multiple blogs on your account. The system now uses the `mp-destination` parameter to ensure posts go to `adobedigest.com` instead of potentially defaulting to another blog.

## What Changed

### 1. Environment Variables
Added `MICROBLOG_MP_DESTINATION` to explicitly specify which blog to post to:

**File: `content/.env`** (already configured)
```
MICROBLOG_TOKEN=6DFEC382FE2D711EC6FD
MICROBLOG_MP_DESTINATION=https://adobedigest.micro.blog/
```

**File: `content/.env.example`** (new documentation file)
- Documents both required environment variables
- Includes instructions on how to find your mp-destination

### 2. Python Script Updates
**File: `content/post_to_microblog.py`**

- Added `self.mp_destination` to load from environment
- Displays destination on startup: `📍 Posting to: https://adobedigest.micro.blog/`
- Includes `mp-destination` parameter in both create and update requests:
  - For new posts (form-encoded): `data['mp-destination'] = self.mp_destination`
  - For updates (JSON): `update_request['mp-destination'] = self.mp_destination`

### 3. GitHub Actions Workflow
**File: `.github/workflows/scrape-and-post.yml`**

Added `MICROBLOG_MP_DESTINATION` to environment variables:
```yaml
env:
  MICROBLOG_TOKEN: ${{ secrets.MICROBLOG_TOKEN }}
  MICROBLOG_MP_DESTINATION: ${{ secrets.MICROBLOG_MP_DESTINATION }}
  MICROBLOG_API_URL: https://micro.blog/micropub
```

## Next Steps

### Add GitHub Secret
You need to add the `MICROBLOG_MP_DESTINATION` secret to your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `MICROBLOG_MP_DESTINATION`
5. Value: `https://adobedigest.micro.blog/`
6. Click **Add secret**

## How It Works

### Multi-Blog Support
The Micropub API supports multiple blogs per account using the `mp-destination` parameter. When you query the Micropub config endpoint:

```bash
curl -H "Authorization: Bearer $MICROBLOG_TOKEN" \
  "https://micro.blog/micropub?q=config" | python3 -m json.tool
```

You get a list of available destinations:

```json
{
  "destination": [
    {
      "uid": "https://hatcher.micro.blog/",
      "name": "doughatcher.com",
      "microblog-default": false
    },
    {
      "uid": "https://adobedigest.micro.blog/",
      "name": "adobedigest.com",
      "microblog-default": true
    },
    {
      "uid": "https://leaningblue.micro.blog/",
      "name": "leaning.blue",
      "microblog-default": false
    }
  ]
}
```

### Routing Logic
- **Without mp-destination**: Micro.blog uses the token's default blog (which may not be Adobe Digest)
- **With mp-destination**: Posts explicitly go to the specified blog URL

## Testing

### Local Testing
```bash
cd content
/workspaces/adobe-digest/.venv/bin/python post_to_microblog.py 0
```

Expected output:
```
📍 Posting to: https://adobedigest.micro.blog/
🚀 Micro.blog Poster
==================================================
...
```

The 📍 line confirms the destination is loaded correctly.

### Production Testing
After adding the GitHub secret, the next workflow run will use the mp-destination parameter automatically.

## Benefits

1. **Explicit Routing**: Posts always go to Adobe Digest, not another blog
2. **Multi-Account Support**: Works correctly with multi-blog Micro.blog accounts
3. **Backward Compatible**: If `MICROBLOG_MP_DESTINATION` is not set, the script still works (uses default)
4. **Transparent**: Shows destination on every run for verification

## References

- Micropub Spec: https://www.w3.org/TR/micropub/
- Micro.blog API: https://help.micro.blog/t/api-reference/6
- Micropub Config: https://micro.blog/micropub?q=config
