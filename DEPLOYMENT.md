# Deployment Configuration

## Production vs Development URLs

### Production (GitHub Pages)
When deploying to production, the `config.json` should have:
```json
{
  "baseURL": "https://adobedigest.com/"
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
hugo --baseURL=https://adobedigest.com/
```

Or use Hugo environment configuration files:
- `config.json` - production settings
- `config/_default/config.json` - default settings
- `config/development/config.json` - local dev overrides

## GitHub Pages Setup

1. Go to repository Settings → Pages
2. Source: Deploy from a branch
3. Branch: `gh-pages` / `/ (root)`
4. Custom domain: `adobedigest.com`

## DNS Configuration

Add CNAME record pointing to:
```
doughatcher.github.io
```

Or use A records pointing to GitHub Pages IPs:
```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```
