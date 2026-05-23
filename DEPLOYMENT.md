# Deployment Configuration

## Production vs Development URLs

### Production (Micro.blog)
The site is hosted on Micro.blog at `https://experiencedigest.org/`

When deploying to production, the `config.json` should have:
```json
{
  "baseURL": "https://experiencedigest.org/"
}
```

### Local Development
For local development with Hugo server, use:
```json
{
  "baseURL": "/"
}
```

**Note:** The GitHub Action workflow uses the committed `config.json`. If you're switching between local dev and production, consider using Hugo's `--baseURL` flag:

```bash
# Local development
hugo server --baseURL=/

# Production build
hugo --baseURL=https://experiencedigest.org/
```

Or use Hugo environment configuration files:
- `config.json` - production settings
- `config/_default/config.json` - default settings
- `config/development/config.json` - local dev overrides

## Micro.blog Deployment Automation

### Overview

The repository includes automated deployment to Micro.blog that triggers on theme file changes. The system uses email-based authentication to obtain session cookies and then triggers theme reloads and site rebuilds.

### Required GitHub Secrets and Variables

Add these in **Settings → Secrets and variables → Actions**:

#### Secrets (Settings → Secrets and variables → Actions → Secrets)

1. **`GMAIL_APP_PASSWORD`** - Gmail App Password (NOT your regular password)
   - **Setup instructions:**
     1. Go to [Google Account Security](https://myaccount.google.com/security)
     2. Enable **2-Step Verification** (required for App Passwords)
     3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
     4. Select app: **Mail** and device: **Other (Custom name)**
     5. Enter name like "Micro.blog Deployment"
     6. Click **Generate**
     7. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)
     8. **Remove spaces** when adding to GitHub Secrets
   - Example: `abcdabcdabcdabcd`

2. **`MICROBLOG_TOKEN`** - Your Micro.blog API token (already configured for content posting)
   - Get from [micro.blog/account/apps](https://micro.blog/account/apps)

3. **`MICROBLOG_MP_DESTINATION`** - Your blog URL (already configured for multi-blog support)
   - Example: `https://adobedigest.micro.blog/`

#### Variables (Settings → Secrets and variables → Actions → Variables)

4. **`GMAIL_EMAIL`** - Your Gmail address
   - Example: `yourname@gmail.com`

5. **`MICROBLOG_EMAIL`** - Email address for your Micro.blog account
   - This is where the sign-in link will be sent
   - Example: `yourname@example.com`

6. **`MICROBLOG_SITE_ID`** - Your site's numeric ID
   - Find this in the URL when viewing your site settings
   - Example: If URL is `https://micro.blog/account/sites/267908/...`
   - Then `MICROBLOG_SITE_ID=267908`

7. **`MICROBLOG_THEME_ID`** - Your theme's numeric ID
   - Find this in the URL when editing your theme
   - Example: If URL is `https://micro.blog/account/themes/89386/...`
   - Then `MICROBLOG_THEME_ID=89386`

### How It Works

1. **Trigger**: Push to `main` branch with changes to `layouts/`, `static/`, `theme.toml`, or `config.json`
2. **Authentication**: 
   - Checks cache for valid session cookie (daily rotation)
   - If no cache, requests sign-in email from Micro.blog
   - Polls Gmail IMAP for magic link (up to 60 seconds)
   - Follows magic link to obtain session cookie
   - Switches to target blog using site ID
3. **Deployment**:
   - Reloads theme templates
   - Triggers full site rebuild
   - Monitors build logs until completion
4. **Caching**: Session cookie cached for 7 days with daily key rotation

### Manual Deployment

You can manually trigger deployment from the Actions tab:
1. Go to **Actions → Deploy to Micro.blog**
2. Click **Run workflow**
3. Optionally override theme ID
4. Click **Run workflow**

### Local Development

Test deployment locally using the `justfile` commands:

```bash
# Full deployment (authenticate + reload + rebuild + monitor)
just microblog-deploy-all

# Quick deployment (assumes valid session exists)
just microblog-deploy

# Individual steps
just microblog-auth        # Authenticate and save session
just microblog-validate    # Check if session is still valid
just microblog-reload      # Reload theme only
just microblog-rebuild     # Trigger rebuild only
just microblog-monitor     # Monitor build logs
```

**Prerequisites for local development:**
1. Copy `.env.example` to `.env`
2. Fill in all required variables (same as GitHub Secrets)
3. Run `pip install -r scraper/requirements.txt` (deployment scripts use same dependencies)

### Troubleshooting

#### Authentication fails with "GMAIL_APP_PASSWORD not set"
- Ensure you're using an App Password, not your regular Gmail password
- Remove spaces from the 16-character App Password
- Verify 2-Step Verification is enabled on your Google Account

#### "No sign-in email found after 5 retries"
- Check that `MICROBLOG_EMAIL` matches your Micro.blog account email
- Verify the email isn't in spam folder
- Try triggering workflow again (Micro.blog may have rate limits)

#### "Session cookie is invalid or expired"
- Cache may have expired - workflow will re-authenticate automatically
- For local development, run `just microblog-auth` to get fresh session
- Session cookies are valid for approximately 7 days

#### "Theme reload failed: 404"
- Verify `MICROBLOG_THEME_ID` is correct
- Check theme still exists at micro.blog/account/themes/YOUR_ID

#### Build timeout
- Default timeout is 5 minutes
- Large sites may take longer - check logs manually at micro.blog/account/logs
- Workflow will still show status even if monitoring times out

### Security Notes

- Session cookies are cached with 7-day TTL but rotate daily
- Cookies are never committed to the repository
- Gmail App Passwords can be revoked at any time from Google Account settings
- Consider using a dedicated Gmail account for automation

## GitHub Pages Setup (Deprecated)

**Note:** This site is now hosted on Micro.blog, not GitHub Pages.

Previous GitHub Pages configuration:

1. Go to repository Settings → Pages
2. Source: Deploy from a branch
3. Branch: `gh-pages` / `/ (root)`
4. Custom domain: `experiencedigest.org`

## DNS Configuration

Configure DNS to point to Micro.blog's servers (contact Micro.blog support for current IP addresses).

Previous GitHub Pages DNS:
```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```
