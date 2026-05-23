# Experience Digest

**Automated security bulletin aggregator for Adobe Commerce, AEM, and related products**

Experience Digest is an automated system that scrapes, aggregates, and publishes security bulletins and research articles related to Adobe Commerce (Magento), Adobe Experience Manager (AEM), and related technologies. The content is automatically posted to [experiencedigest.org](https://experiencedigest.org) via Micro.blog.

## Features

- 🔍 **Automated Scraping**: Monitors multiple sources for new security content
- 📰 **Multi-Source Aggregation**: Adobe HelpX bulletins, Sansec research, Akamai blog
- 🤖 **Smart Filtering**: Content filtering for relevant Adobe Commerce/AEM topics
- 📝 **Micro.blog Integration**: Automatic posting via Micropub API
- ⏰ **Scheduled Updates**: Runs every 6 hours via GitHub Actions
- 🔄 **Deduplication**: Tracks posted content to avoid duplicates
- 📊 **Hugo Static Site**: Fast, modern website built with Hugo
- 📡 **RSS Feeds**: Multiple feeds for all bulletins and per-product updates
- 🔔 **Browser Notifications**: Real-time alerts for new security bulletins via browser notifications

## Staying Updated

Get security bulletin updates through your preferred channel:

### Browser Notifications

Enable browser notifications on [experiencedigest.org](https://experiencedigest.org) to receive instant alerts when new security bulletins are posted. Works with Chrome, Firefox, Safari, and Edge.

See [Browser Notifications Documentation](docs/BROWSER_NOTIFICATIONS.md) for details.

## RSS Feeds

Subscribe to stay updated on Adobe security bulletins:

- **[All Bulletins](https://experiencedigest.org/feed.xml)** - Complete firehose of all security bulletins and advisories
- **[Per-Product Feeds](https://experiencedigest.org/products/)** - Individual RSS feeds for specific Adobe products
- **[JSON Feed](https://experiencedigest.org/feed.json)** - JSON Feed format for developers

## Data Sources

1. **Adobe Security Bulletins** (via Adobe HelpX)
   - Adobe Commerce (Magento)
   - Adobe Experience Manager
   - Adobe AEM Forms

2. **Adobe Commerce Release Notes**
   - Official release notes for Adobe Commerce versions
   - Feature updates, security patches, and platform changes

3. **Magento Open Source Release Notes**
   - Official release notes for Magento Open Source versions
   - Community edition updates and releases

4. **Sansec.io Security Research**
   - Magento/Adobe Commerce security research
   - Threat intelligence and malware analysis

5. **Akamai Security Blog** (filtered)
   - Posts mentioning Adobe Commerce, AEM, or related vulnerabilities
   - SessionReaper, CosmicString, and other Adobe-related threats

6. **NIST National Vulnerability Database (NVD)**
   - CVE vulnerability updates for Adobe Commerce, Magento, and AEM
   - Tracks newly published and recently modified CVEs
   - Checks for updates daily across 30-day rolling window
   - Includes CVSS severity scores and reference links

## Architecture

```
┌─────────────────┐
│ GitHub Actions  │  Runs every 6 hours
│  (Scraper)      │  
└────────┬────────┘
         │
         ├──> Scrape Adobe HelpX
         ├──> Scrape Adobe Commerce Releases
         ├──> Scrape Magento Open Source Releases
         ├──> Scrape Sansec.io 
         ├──> Scrape Akamai Blog (filtered)
         ├──> Scrape NIST NVD CVEs (filtered)
         │
         v
┌─────────────────┐
│  Post to        │  Via Micropub API
│  Micro.blog     │  
└────────┬────────┘
         │
         v
┌─────────────────┐
│  experiencedigest.org│  Hugo static site
│  (Micro.blog)   │  Custom theme
└─────────────────┘
```

## Local Development

### Prerequisites

- Python 3.11+
- Hugo 0.152+
- Node.js (for justfile tasks)

### Setup

```bash
# Clone the repository
git clone https://github.com/doughatcher/experience-digest.git
cd experience-digest

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
cd scraper
pip install -r requirements.txt
```

### Running the Scraper Locally

```bash
cd scraper
python3 scraper.py
```

This will:
- Read sources from `data/sources.yaml`
- Scrape new content
- Create markdown files in `content/YYYY/MM/DD/`
- Update `scraped_posts.json` tracking file

### Testing Micro.blog Posting

```bash
# Set environment variables
export MICROBLOG_TOKEN="your-token"
export MICROBLOG_MP_DESTINATION="https://adobedigest.micro.blog/"

# Post up to 5 new items
cd scraper
python3 post_to_microblog.py 5
```

### Building the Site

```bash
# Build with Hugo
hugo

# Serve locally
hugo server
```

## Configuration

### Adding New Sources

Edit `data/sources.yaml`:

```yaml
sources:
  - type: adobe-helpx
    name: source-identifier
    display_name: "Display Name"
    url: https://helpx.adobe.com/security/security-bulletin.html
    section_id: product-section
  
  - type: adobe-release-notes
    name: source-identifier
    display_name: "Display Name"
    url: https://experienceleague.adobe.com/en/docs/commerce-operations/release/versions
    product: adobe-commerce  # or magento-open-source
    categories:
      - releases
    
  - type: atom-feed
    name: source-identifier
    display_name: "Display Name"
    url: https://example.com/feed.xml
    limit: 20
    includes:
      - keyword1
      - keyword2
    categories:
      - category1
  
  - type: nist-nvd
    name: source-identifier
    display_name: "Display Name"
    keywords:
      - Adobe Commerce
      - Magento
    lookback_days: 30
    categories:
      - cve
      - vulnerability
```

### GitHub Secrets and Variables

Required for GitHub Actions:

**Secrets** (Settings → Secrets and variables → Actions → Secrets):
- `GMAIL_APP_PASSWORD`: Gmail App Password (see [DEPLOYMENT.md](DEPLOYMENT.md) for setup)
- `MICROBLOG_TOKEN`: Your Micro.blog API token
- `MICROBLOG_MP_DESTINATION`: Your blog URL (e.g., `https://adobedigest.micro.blog/`)

**Variables** (Settings → Secrets and variables → Actions → Variables):
- `GMAIL_EMAIL`: Gmail address for receiving sign-in emails
- `MICROBLOG_EMAIL`: Micro.blog account email
- `MICROBLOG_SITE_ID`: Your site's numeric ID
- `MICROBLOG_THEME_ID`: Your theme's numeric ID

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed setup instructions.

## Workflows

### Scrape and Post (`scrape-and-post.yml`)
- **Schedule**: Every 6 hours
- **Manual**: Via workflow_dispatch
- **Actions**: Scrape sources → Post to Micro.blog → Commit tracking file

### Deploy to Micro.blog (`deploy-microblog.yml`)
- **Trigger**: Push to main (theme files only)
- **Manual**: Via workflow_dispatch
- **Actions**: Email auth → Reload theme → Rebuild site → Monitor logs
- **Features**: Session caching (7-day TTL), automatic re-authentication

### Test (`test.yml`)
- **Trigger**: Push to main, PRs
- **Actions**: Validate YAML, test scraper, verify Hugo build

## Deployment

### Automated Deployment

Theme changes automatically trigger deployment to Micro.blog when you push to main:
- Changes to `layouts/`, `static/`, `theme.toml`, or `config.json`
- Uses email-based authentication with session caching
- Monitors build logs for completion

### Manual Deployment

```bash
# Full deployment with authentication
just microblog-deploy-all

# Quick deployment (reuses existing session)
just microblog-deploy

# Individual operations
just microblog-auth       # Authenticate and save session
just microblog-reload     # Reload theme only
just microblog-rebuild    # Trigger rebuild only
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete documentation.

## Project Structure

```
experience-digest/
├── .github/
│   └── workflows/          # GitHub Actions workflows
├── content/                # Hugo content (generated by scraper)
│   ├── 2024/
│   ├── 2025/
│   └── bulletins/
├── data/
│   └── sources.yaml        # Scraper source configuration
├── layouts/                # Hugo templates
│   ├── index.html          # Homepage
│   └── _default/
├── scraper/                # Python scraping system
│   ├── scraper.py          # Main scraper
│   ├── post_to_microblog.py # Micropub poster
│   ├── scraped_posts.json  # Tracking file
│   └── scrapers/           # Individual scrapers
│       ├── adobe_helpx.py
│       ├── adobe_releases.py
│       ├── atom_feed.py
│       ├── sansec_io.py
│       └── nist_nvd.py
└── static/                 # Static assets
```

## Documentation

- **[NIST NVD Integration](docs/NIST_NVD_INTEGRATION.md)** - How CVE tracking from NIST works
- **[Deployment Guide](DEPLOYMENT.md)** - Deployment and hosting information
- **[Micro.blog Multi-Blog Setup](docs/MICROBLOG_MULTI_BLOG_SETUP.md)** - Multi-blog configuration

## Credits

- **Theme**: Forked from [Dougie](https://github.com/doughatcher/micro.blog) theme
- **Hosting**: [Micro.blog](https://micro.blog)
- **Sources**: Adobe, Sansec.io, Akamai

## License

MIT License - See [LICENSE](LICENSE) for details

## Links

- **Website**: [experiencedigest.org](https://experiencedigest.org)
- **Micro.blog**: [@adobedigest](https://micro.blog/adobedigest)
- **Repository**: [github.com/doughatcher/experience-digest](https://github.com/doughatcher/experience-digest)

---

*Automated security intelligence for Adobe Commerce and AEM*
