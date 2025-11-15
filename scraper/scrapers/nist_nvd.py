#!/usr/bin/env python3
"""
NIST NVD CVE Scraper
Fetches CVE updates from NIST National Vulnerability Database API 2.0
Filters for Adobe Commerce, Magento, and AEM related vulnerabilities
"""

import re
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path


class NistNvdScraper:
    """Scraper for NIST NVD CVE database"""
    
    def __init__(self, output_dir, existing_posts=None):
        """Initialize scraper"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.existing_posts = existing_posts or set()
        self.api_base = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        # Rate limiting: 5 requests per 30 seconds without API key
        # 50 requests per 30 seconds with API key
        self.rate_limit_delay = 6  # seconds between requests (safe for no API key)
    
    def fetch_cves(self, params):
        """Fetch CVEs from NIST NVD API with rate limiting"""
        try:
            # Add delay to respect rate limits
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(self.api_base, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"   ✗ Error fetching from NVD API: {e}")
            return None
    
    def extract_cves(self, keywords, lookback_days=30):
        """
        Extract CVEs matching keywords from the last N days
        Uses lastModStartDate/lastModEndDate for incremental updates
        """
        cves = []
        
        # Calculate date range for incremental updates
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Format dates in ISO 8601 format required by API
        start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S.000')
        end_date_str = end_date.strftime('%Y-%m-%dT%H:%M:%S.000')
        
        print(f"   📅 Searching CVEs modified between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
        
        total_found = 0
        skipped_duplicate = 0
        skipped_filter = 0
        
        # Search for each keyword separately due to API limitations
        for keyword in keywords:
            print(f"   🔍 Searching for keyword: {keyword}")
            
            # Prepare API parameters
            params = {
                'keywordSearch': keyword,
                'lastModStartDate': start_date_str,
                'lastModEndDate': end_date_str,
                'resultsPerPage': 100  # Max allowed
            }
            
            start_index = 0
            while True:
                params['startIndex'] = start_index
                
                # Fetch data from API
                data = self.fetch_cves(params)
                if not data:
                    break
                
                vulnerabilities = data.get('vulnerabilities', [])
                total_results = data.get('totalResults', 0)
                
                if not vulnerabilities:
                    break
                
                print(f"   📥 Retrieved {len(vulnerabilities)} CVEs (index {start_index})")
                
                # Process each CVE
                for vuln_wrapper in vulnerabilities:
                    cve_data = vuln_wrapper.get('cve', {})
                    cve_id = cve_data.get('id', '')
                    
                    if not cve_id:
                        continue
                    
                    total_found += 1
                    
                    # Check for duplicates
                    if cve_id in self.existing_posts:
                        skipped_duplicate += 1
                        continue
                    
                    # Check if already in our list (from another keyword)
                    if any(c['id'] == cve_id for c in cves):
                        continue
                    
                    # Extract description
                    descriptions = cve_data.get('descriptions', [])
                    description_text = ''
                    for desc in descriptions:
                        if desc.get('lang') == 'en':
                            description_text = desc.get('value', '')
                            break
                    
                    # Filter: must mention Adobe, Magento, or AEM in description
                    adobe_keywords = ['adobe commerce', 'magento', 'adobe experience manager', 'aem']
                    description_lower = description_text.lower()
                    
                    if not any(kw in description_lower for kw in adobe_keywords):
                        skipped_filter += 1
                        continue
                    
                    # Extract dates
                    published = cve_data.get('published', '')
                    last_modified = cve_data.get('lastModified', '')
                    
                    # Parse dates
                    published_date = datetime.fromisoformat(published.replace('Z', '+00:00')) if published else datetime.now()
                    modified_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00')) if last_modified else published_date
                    
                    # Extract CVSS score if available
                    cvss_score = None
                    cvss_severity = None
                    metrics = cve_data.get('metrics', {})
                    
                    # Try CVSS v3.1 first, then v3.0, then v2.0
                    for version in ['cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2']:
                        if version in metrics and metrics[version]:
                            metric = metrics[version][0]
                            cvss_data = metric.get('cvssData', {})
                            cvss_score = cvss_data.get('baseScore')
                            cvss_severity = cvss_data.get('baseSeverity') or metric.get('baseSeverity')
                            break
                    
                    # Extract references
                    references = cve_data.get('references', [])
                    reference_urls = [ref.get('url', '') for ref in references[:5]]  # Limit to 5 refs
                    
                    # Create CVE object
                    cve = {
                        'id': cve_id,
                        'description': description_text,
                        'published_date': published_date,
                        'modified_date': modified_date,
                        'cvss_score': cvss_score,
                        'cvss_severity': cvss_severity,
                        'references': reference_urls,
                        'url': f"https://nvd.nist.gov/vuln/detail/{cve_id}"
                    }
                    
                    cves.append(cve)
                
                # Check if we need to fetch more results
                if start_index + len(vulnerabilities) >= total_results:
                    break
                
                start_index += len(vulnerabilities)
        
        if total_found > 0:
            if skipped_duplicate > 0:
                print(f"   ℹ️  Skipped {skipped_duplicate} existing CVEs")
            if skipped_filter > 0:
                print(f"   ℹ️  Filtered out {skipped_filter} non-Adobe/Magento CVEs")
            print(f"   📥 Found {len(cves)} new Adobe/Magento CVEs to process")
        else:
            print(f"   ℹ️  No CVEs found")
        
        return cves
    
    def create_markdown(self, data):
        """Create markdown file with Micro.blog front matter"""
        # Use modified date for the post (when CVE was last updated)
        date = data['modified_date']
        
        # Create slug from CVE ID
        slug = f"nist-{data['id'].lower()}"
        
        # Create directory structure: YYYY/MM/DD/
        date_dir = self.output_dir / str(date.year) / f"{date.month:02d}" / f"{date.day:02d}"
        date_dir.mkdir(parents=True, exist_ok=True)
        
        filename = date_dir / f"{slug}.md"
        
        # Build Micro.blog compatible front matter
        url_path = f"/{date.year}/{date.month:02d}/{date.day:02d}/{slug}.html"
        
        # Get categories from source config
        source_categories = data.get('source_categories', [])
        source_name = data.get('source_name', 'nist-nvd')
        
        # Determine product tags from description
        description_lower = data['description'].lower()
        product_tags = []
        if 'adobe commerce' in description_lower or 'magento' in description_lower:
            product_tags.extend(['adobe-commerce', 'magento'])
        if 'adobe experience manager' in description_lower or 'aem' in description_lower:
            product_tags.extend(['adobe-experience-manager', 'aem'])
        
        # Base tags
        base_tags = ['cve', 'vulnerability', 'nist', 'nvd', source_name] + product_tags
        
        # Build title
        title_parts = [data['id']]
        if data['cvss_severity']:
            title_parts.append(f"({data['cvss_severity']})")
        if data['cvss_score']:
            title_parts.append(f"CVSS {data['cvss_score']}")
        
        title = ' '.join(title_parts)
        
        front_matter = {
            'layout': 'post',
            'title': title,
            'microblog': False,
            'guid': f"http://adobedigest.micro.blog{url_path}",
            'date': date.strftime('%Y-%m-%dT%H:%M:%S-05:00'),
            'type': 'post',
            'url': url_path,
            'categories': ['cve', 'vulnerability'] + source_categories,
            'tags': base_tags + source_categories
        }
        
        # Build content
        content_parts = []
        
        # Add severity badge if available
        if data['cvss_severity'] and data['cvss_score']:
            severity_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(data['cvss_severity'], '⚪')
            content_parts.append(f"**{severity_emoji} Severity: {data['cvss_severity']} (CVSS {data['cvss_score']})**\n")
        
        # Add description
        content_parts.append(data['description'])
        content_parts.append('')
        
        # Add dates
        pub_date = data['published_date'].strftime('%Y-%m-%d')
        mod_date = data['modified_date'].strftime('%Y-%m-%d')
        
        if pub_date == mod_date:
            content_parts.append(f"**Published:** {pub_date}")
        else:
            content_parts.append(f"**Published:** {pub_date}  ")
            content_parts.append(f"**Last Modified:** {mod_date} ⚠️")
        
        content_parts.append('')
        
        # Add references if available
        if data['references']:
            content_parts.append("**References:**")
            for ref_url in data['references']:
                content_parts.append(f"- {ref_url}")
            content_parts.append('')
        
        # Link to NVD page
        content_parts.append(f"---\n")
        content_parts.append(f"[**View Full CVE Details on NIST NVD →**]({data['url']})")
        
        content = '\n'.join(content_parts)
        
        # Write file in Micro.blog format
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('---\n')
            for key, value in front_matter.items():
                if isinstance(value, bool):
                    f.write(f'{key}: {str(value).lower()}\n')
                elif isinstance(value, list):
                    f.write(f'{key}:\n')
                    for item in value:
                        f.write(f'  - {item}\n')
                elif value is None or value == '':
                    f.write(f'{key}: ""\n')
                else:
                    f.write(f'{key}: "{value}"\n')
            f.write('---\n')
            f.write(content)
            f.write('\n')
        
        print(f"   ✓ Created: {filename}")
        return filename
    
    def scrape(self, config):
        """
        Scrape CVEs from NIST NVD API
        
        Config format:
        {
            'name': 'nist-nvd',
            'keywords': ['Adobe Commerce', 'Magento', 'Adobe Experience Manager'],
            'lookback_days': 30,  # Optional: how many days to look back for updates
            'categories': []  # Optional categories to add
        }
        """
        source_name = config.get('name', 'nist-nvd')
        keywords = config.get('keywords', ['Adobe Commerce', 'Magento', 'Adobe Experience Manager'])
        lookback_days = config.get('lookback_days', 30)
        source_categories = config.get('categories', [])
        display_name = config.get('display_name', 'NIST NVD')
        
        print(f"\n🔍 Scraping {source_name} (looking back {lookback_days} days)...")
        
        # Extract CVEs
        cves = self.extract_cves(keywords, lookback_days)
        
        created_files = []
        
        # Process each CVE
        for cve in cves:
            print(f"   Processing {cve['id']}...")
            
            # Add source info to CVE for markdown generation
            cve['source_name'] = source_name
            cve['source_categories'] = source_categories
            cve['source_display_name'] = display_name
            
            # Create markdown
            try:
                filename = self.create_markdown(cve)
                created_files.append(filename)
                self.existing_posts.add(cve['id'])
            except Exception as e:
                print(f"   ✗ Error creating markdown for {cve['id']}: {e}")
        
        return created_files
