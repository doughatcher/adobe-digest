# Micro.blog Automated Deployment

This directory contains scripts and configuration for automated deployment of Micro.blog themes via GitHub Actions.

## Overview

Micro.blog doesn't provide traditional API tokens or CI/CD integration. This solution works around that limitation by:

1. **Email-based Authentication**: Uses Micro.blog's "Sign in with email" feature to obtain a session cookie
2. **Session Cookie Caching**: Stores the session cookie (7-day expiry) to avoid re-authentication on every deployment
3. **Theme Reload**: POSTs to `/account/themes/reload` to sync theme files from GitHub
4. **Build Automation**: Visits `/account/logs` to trigger site rebuild
5. **Build Monitoring**: Polls `/posts/check` to monitor build completion

## Architecture

### Why Poll `/posts/check`?

Micro.blog's web interface polls the `/posts/check` endpoint to monitor build progress. Our automation mimics this behavior by:

- Polling every 5 seconds with redirect following
- Monitoring `is_publishing`, `is_processing`, and `publishing_status` fields
- Completing after seeing activity transition to idle (typically 5-10 polls)
- Timing out after 60 seconds if no completion detected

### Authentication Flow

```mermaid
flowchart TD
    A["1. POST /account/signin (multipart form-data)<br/>triggers sign-in email"]
    B["2. Poll Gmail IMAP for sign-in email<br/>FROM help@micro.blog · SUBJECT sign-in<br/>extract magic link from quoted-printable HTML"]
    C["3. Follow magic link<br/>capture rack.session cookie<br/>save to .session-cookie"]
    D["4. Switch to default blog (multi-blog setups)<br/>POST /account/sites/make_default"]
    A --> B --> C --> D
```

### Deployment Flow

```mermaid
flowchart TD
    A["1. Validate session cookie<br/>GET /account/logs<br/>(check for redirect to /signin)"]
    B["2. Reload theme templates from GitHub<br/>POST /account/themes/reload (with theme_id)<br/>302 → /account/themes/{id}/templates?reload=1<br/>(redirected endpoint returns 404 — expected)"]
    C["3. Trigger site rebuild<br/>GET /account/logs"]
    D["4. Poll /posts/check repeatedly<br/>monitors publishing_status<br/>completes when status goes idle<br/>typical: 15–50 s (5–10 polls)"]
    A --> B --> C --> D
```

## Files

### Scripts

- **`microblog_auth.py`**: Handles email-based authentication and session cookie capture
- **`microblog_deploy.py`**: Validates session, triggers rebuild, polls for completion
- **`requirements.txt`**: Python dependencies

### Configuration

- **`.env`**: Local environment variables (see `.env.example`)
- **`.session-cookie`**: Cached session cookie (gitignored, 7-day TTL)
- **`../.github/workflows/deploy-microblog.yml`**: GitHub Actions workflow

## Environment Variables

### Required for Authentication

| Variable | Type | Description |
|----------|------|-------------|
| `GMAIL_EMAIL` | Variable | Gmail address for receiving sign-in emails |
| `GMAIL_APP_PASSWORD` | **Secret** | Gmail app password for IMAP access ([setup guide](https://support.google.com/accounts/answer/185833)) |
| `MICROBLOG_EMAIL` | Variable | Micro.blog account email address |
| `MICROBLOG_SITE_ID` | Variable | Your Micro.blog site ID (see below) |

### Required for Deployment

| Variable | Type | Description |
|----------|------|-------------|
| `MICROBLOG_THEME_ID` | Variable | Your theme ID (see below) |

### Finding Your IDs

**Site ID:**
1. Go to your Micro.blog account settings
2. Inspect network requests or page source
3. Look for URLs like `/account/sites/{SITE_ID}`

**Theme ID:**
1. Go to Design → Edit Custom Themes
2. Click on your theme
3. URL will be `/account/themes/{THEME_ID}/info`

## Local Setup

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Configure Environment

Create `.env` in your project root:

```bash
# Gmail for receiving sign-in emails
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password

# Micro.blog account
MICROBLOG_EMAIL=your-microblog@email.com
MICROBLOG_SITE_ID=12345
MICROBLOG_THEME_ID=67890
```

### 3. Authenticate

Run once to capture session cookie:

```bash
python3 .github/deploy/microblog_auth.py
```

This will:
- Request a sign-in email from Micro.blog
- Poll your Gmail inbox for the magic link
- Follow the link and capture the session cookie
- Save it to `.session-cookie` (valid for 7 days)

### 4. Deploy

Trigger a deployment manually:

```bash
# Full deployment (reload + rebuild + monitor)
python3 .github/deploy/microblog_deploy.py --all

# Individual operations
python3 .github/deploy/microblog_deploy.py --reload      # Reload theme
python3 .github/deploy/microblog_deploy.py --rebuild     # Rebuild site
python3 .github/deploy/microblog_deploy.py --monitor     # Monitor only

# Validate session without deploying
python3 .github/deploy/microblog_deploy.py --validate-only
```

## GitHub Actions Setup

### 1. Configure Secrets

In your GitHub repository settings → Secrets and variables → Actions:

**Secrets** (encrypted):
- `GMAIL_APP_PASSWORD`: Your Gmail app password

**Variables** (plaintext configuration):
- `GMAIL_EMAIL`: Your Gmail address
- `MICROBLOG_EMAIL`: Your Micro.blog email
- `MICROBLOG_SITE_ID`: Your site ID
- `MICROBLOG_THEME_ID`: Your theme ID

### 2. Workflow Configuration

The workflow (`.github/workflows/deploy-microblog.yml`) automatically:

- **Triggers on theme file changes**: `layouts/**`, `static/**`, `theme.toml`, `config.json`
- **Caches session cookie**: 7-day TTL, rotates daily
- **Re-authenticates when needed**: Automatically re-runs authentication if session expires
- **Deploys changes**: Reloads theme, rebuilds site, monitors completion

### 3. Workflow Execution

The workflow runs on every push to `main` that modifies theme files:

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'layouts/**'
      - 'static/**'
      - 'theme.toml'
      - 'config.json'
```

You can also manually trigger it via the Actions tab in GitHub.

## Using Just Commands

If you have [Just](https://github.com/casey/just) installed, use these convenience commands:

```bash
# Authentication
just microblog-auth          # Authenticate and save session cookie

# Deployment
just microblog-deploy-all    # Full deployment
just microblog-reload        # Reload theme only
just microblog-rebuild       # Rebuild site only
just microblog-monitor       # Monitor existing build

# Validation
just microblog-validate      # Test session cookie validity
```

## Troubleshooting

### Session Cookie Expired

**Symptoms**: Deployment fails with "Session validation failed"

**Solution**: Re-authenticate
```bash
python3 .github/deploy/microblog_auth.py
```

### Gmail Authentication Issues

**Symptoms**: "IMAP authentication failed" or "Username and Password not accepted"

**Solution**: 
1. Enable 2-factor authentication on your Google account
2. Generate an [app password](https://support.google.com/accounts/answer/185833)
3. Use the app password (not your regular password) in `GMAIL_APP_PASSWORD`

### No Sign-in Email Received

**Symptoms**: Script times out waiting for sign-in email

**Solution**:
1. Check your Gmail spam folder
2. Verify `MICROBLOG_EMAIL` matches your Micro.blog account
3. Try requesting sign-in email manually at micro.blog/account/signin
4. Increase wait time: modify `max_wait=60` in `microblog_auth.py`

### Build Times Out

**Symptoms**: "Timeout reached (60s) after N polls"

**Solution**:
1. Typical builds complete in 15-50 seconds
2. If timing out consistently, check build logs at micro.blog/account/logs
3. Look for actual errors in the build logs
4. Note: timeout may indicate build started successfully but monitoring ended early

### Wrong Blog Being Updated

**Symptoms**: Changes deploy to wrong blog in multi-blog setup

**Solution**:
1. Verify `MICROBLOG_SITE_ID` is correct
2. The script calls `/account/sites/make_default` during authentication
3. Check which blog is marked as default in your account settings

## How It Works: Technical Details

### Email Polling

The authentication script polls Gmail IMAP every 12 seconds for up to 60 seconds:

```python
search_criteria = '(FROM "help@micro.blog" SUBJECT "sign-in")'
```

It extracts the magic link from quoted-printable HTML encoding:
```python
# Matches: https://micro.blog/account/signin?auth=HEXCODE
pattern = r'https://micro\.blog/account/signin\?auth=3D([a-f0-9]+)'
```

### Session Cookie Format

The `rack.session` cookie is Base64-encoded and URL-safe:
```
rack.session=BAh7CkkiD3Nlc3Npb25faWQGOgZFVG86HVJhY2s6OlNlc3Npb246...
```

Valid for 7 days from authentication.

### Build Polling Response

The `/posts/check` endpoint returns JSON:

```json
{
  "count": 0,
  "check_seconds": 20,
  "is_publishing": false,
  "is_processing": false,
  "publishing_progress": 1.0,
  "publishing_status": "Syncing files to server",
  "latest_url": null,
  "markers": {
    "timeline": {
      "id": "79093439",
      "date_marked": "2025-12-01 17:12:55 +0000",
      "time_published": 1764598106
    }
  }
}
```

The script polls until:
- Status transitions from active to idle (3+ polls after seeing activity)
- Maximum 10 polls reached (50 seconds)
- Timeout is reached (default 60s)

### GitHub Actions Caching Strategy

Session cookies are cached with a composite key:

```yaml
cache-key: microblog-session-${{ github.repository }}-${{ steps.cache-key.outputs.date_prefix }}
```

Where `date_prefix` is `YYYY-MM-DD`, ensuring:
- Daily rotation (prevents stale cache)
- Repository isolation (multi-repo support)
- 7-day maximum age (matches cookie expiry)

## Security Considerations

### Secrets Management

- **Never commit** `.env` or `.session-cookie` files
- Use GitHub Secrets for `GMAIL_APP_PASSWORD`
- Use GitHub Variables for non-sensitive config (emails, IDs)
- Session cookies grant full account access - protect them

### Gmail App Passwords

- App passwords are account-specific, not user-specific
- Revoke app passwords when no longer needed
- Don't reuse app passwords across services
- Consider using a dedicated Gmail account for automation

### Session Cookie Risks

- Session cookies have full account privileges
- 7-day expiry reduces risk window
- Cached in GitHub Actions (encrypted at rest)
- Regenerated automatically on expiry

## Limitations

1. **Email-based auth only**: Requires Gmail IMAP access
2. **7-day session limit**: Requires weekly re-authentication
3. **Single blog per repo**: Designed for one theme → one blog workflow
4. **Theme reload requires theme_id**: Must be a custom theme, not a built-in theme
5. **Build monitoring is approximate**: Completion detection based on status polling

## Future Improvements

Potential enhancements (PRs welcome!):

- [ ] Support for other email providers (Outlook, ProtonMail)
- [ ] Webhook-based triggers instead of path filters
- [ ] Build artifact caching
- [ ] Deployment rollback on failure
- [ ] Multi-blog deployment from single repo
- [ ] Slack/Discord notifications on deployment status

## Credits

Created by [@hatcher](https://micro.blog/hatcher) for the Micro.blog community.

Inspired by the need for Hugo theme development workflows with automated deployment.

## License

MIT License - feel free to adapt for your own Micro.blog themes!

## Support

Questions or issues? Post in the [Micro.blog help forum](https://help.micro.blog) or open an issue on GitHub.
