# NIST NVD CVE Integration

## Overview

Adobe Digest now integrates with the [NIST National Vulnerability Database (NVD)](https://nvd.nist.gov/) to automatically track and publish CVE (Common Vulnerabilities and Exposures) updates related to Adobe Commerce, Magento, and Adobe Experience Manager.

## How It Works

### Data Source

The scraper queries the [NVD API 2.0](https://nvd.nist.gov/developers/vulnerabilities) to search for CVEs matching specific keywords:
- Adobe Commerce
- Magento
- Adobe Experience Manager

### Incremental Updates

Instead of downloading the entire CVE database, the scraper uses incremental updates:
- **Rolling Window**: Checks the last 30 days by default (configurable)
- **Last Modified Date**: Uses `lastModStartDate` and `lastModEndDate` parameters to fetch only CVEs that have been modified recently
- **Update Detection**: Catches both newly published CVEs and updates to existing CVEs

### Filtering

The scraper applies multi-level filtering:
1. **Keyword Search**: Initial API query filters by keywords
2. **Description Filter**: Further filters CVEs to ensure they actually mention Adobe products in the description
3. **Deduplication**: Tracks already-posted CVEs to avoid duplicates

### Rate Limiting

The NIST NVD API has rate limits:
- **Without API Key**: 5 requests per 30 seconds
- **With API Key**: 50 requests per 30 seconds

The scraper implements a 6-second delay between requests to stay within limits without requiring an API key.

## Example Use Case

When CVE-2022-24086 (mentioned in the original issue) gets updated:
1. NIST modifies the CVE record (e.g., on 2025-10-23)
2. During the next scraper run, the NIST NVD scraper queries for CVEs modified in the last 30 days
3. The scraper finds CVE-2022-24086 in the results
4. Since it mentions "Adobe Commerce" in the description, it passes the filter
5. A markdown post is generated with:
   - CVE ID and CVSS score
   - Severity level (CRITICAL, HIGH, MEDIUM, LOW)
   - Full description
   - Published and last modified dates
   - Reference links
   - Link to the full CVE on NVD

## Post Format

Generated posts include:
- **Title**: CVE ID with severity and CVSS score
- **Severity Badge**: Visual indicator (🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, 🟢 LOW)
- **Description**: Full CVE description from NVD
- **Dates**: Both published date and last modified date (with warning if recently updated)
- **References**: Links to additional information
- **NVD Link**: Direct link to the CVE details on nvd.nist.gov

## Configuration

In `data/sources.yaml`:

```yaml
- type: nist-nvd
  name: nist-nvd
  display_name: NIST NVD
  description: CVE vulnerability updates from NIST National Vulnerability Database
  keywords:
    - Adobe Commerce
    - Magento
    - Adobe Experience Manager
  lookback_days: 30
  categories:
    - cve
    - vulnerability
```

### Configuration Options

- **keywords**: List of keywords to search for in CVE descriptions
- **lookback_days**: Number of days to look back for modified CVEs (default: 30)
- **categories**: Hugo categories/tags to apply to generated posts

## Running the Scraper

The NIST NVD scraper runs automatically as part of the regular scraping workflow:

```bash
cd scraper
python3 scraper.py
```

To run with force mode (ignore existing posts):
```bash
python3 scraper.py --force
```

## API Documentation

For more information about the NVD API:
- [NVD API Documentation](https://nvd.nist.gov/developers/vulnerabilities)
- [API 2.0 Transition Guide](https://nvd.nist.gov/General/News/api-20-announcements)

## Future Enhancements

Potential improvements:
1. **API Key Support**: Add optional API key configuration for higher rate limits
2. **Severity Filtering**: Only post CVEs above a certain severity threshold
3. **Product CPE Matching**: Use CPE (Common Platform Enumeration) names for more precise matching
4. **Webhook Notifications**: Send immediate notifications for critical CVEs
5. **Historical Import**: One-time import of all historical Adobe CVEs
