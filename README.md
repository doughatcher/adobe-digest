# Adobe Digest

**Automated security bulletin aggregator for Adobe Commerce, AEM, and related products**

Adobe Digest is an automated system that scrapes, aggregates, and publishes security bulletins and research articles related to Adobe Commerce (Magento), Adobe Experience Manager (AEM), and related technologies. The content is automatically posted to [adobedigest.com](https://adobedigest.com) via Micro.blog.

## Features

- 🔍 **Automated Scraping**: Monitors multiple sources for new security content
- 📰 **Multi-Source Aggregation**: Adobe HelpX bulletins, Sansec research, Akamai blog
- 🤖 **Smart Filtering**: Content filtering for relevant Adobe Commerce/AEM topics
- 📝 **Micro.blog Integration**: Automatic posting via Micropub API
- ⏰ **Scheduled Updates**: Runs every 6 hours via GitHub Actions
- 🔄 **Deduplication**: Tracks posted content to avoid duplicates
- 📊 **Hugo Static Site**: Fast, modern website built with Hugo

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
         │
         v
┌─────────────────┐
│  Post to        │  Via Micropub API
│  Micro.blog     │  
└────────┬────────┘
         │
         v
┌─────────────────┐
│  adobedigest.com│  Hugo static site
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
git clone https://github.com/doughatcher/adobe-digest.git
cd adobe-digest

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
```

### GitHub Secrets

Required secrets for GitHub Actions:
- `MICROBLOG_TOKEN`: Your Micro.blog API token
- `MICROBLOG_MP_DESTINATION`: Your blog URL (e.g., `https://adobedigest.micro.blog/`)

## Workflows

### Scrape and Post (`scrape-and-post.yml`)
- **Schedule**: Every 6 hours
- **Manual**: Via workflow_dispatch
- **Actions**: Scrape sources → Post to Micro.blog → Commit tracking file
- **Note**: Commits use `[skip ci]` to prevent triggering the test workflow

### Test (`test.yml`)
- **Trigger**: Push to main, PRs
- **Actions**: Validate YAML, test scraper imports and initialization, verify Hugo build
- **Note**: Does NOT run the actual scraper to avoid duplicate work

## Project Structure

```
adobe-digest/
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
│       ├── sansec_io.py
│       └── atom_feed.py
└── static/                 # Static assets
```

## Credits

- **Theme**: Forked from [Dougie](https://github.com/doughatcher/micro.blog) theme
- **Hosting**: [Micro.blog](https://micro.blog)
- **Sources**: Adobe, Sansec.io, Akamai

## License

MIT License - See [LICENSE](LICENSE) for details

## Links

- **Website**: [adobedigest.com](https://adobedigest.com)
- **Micro.blog**: [@adobedigest](https://micro.blog/adobedigest)
- **Repository**: [github.com/doughatcher/adobe-digest](https://github.com/doughatcher/adobe-digest)

---

*Automated security intelligence for Adobe Commerce and AEM*
