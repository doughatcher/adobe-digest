#!/usr/bin/env python3
"""
Adobe Security Bulletin Scraper
Fetches security bulletins from Adobe and generates markdown posts for micro.blog
"""

import os
import re
import yaml
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
import hashlib
import json


class AdobeSecurityScraper:
    def __init__(self, config_file='scraper.yaml', output_dir='posts'):
        """Initialize scraper with config file and output directory"""
        self.config_file = config_file
        self.output_dir = Path(__file__).parent / output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.base_url = 'https://helpx.adobe.com'
        
        # Load existing posts to avoid duplicates
        self.existing_posts = self.load_existing_posts()
        
    def load_existing_posts(self):
        """Load list of already scraped bulletin IDs"""
        posts_file = Path(__file__).parent / 'scraped_posts.json'
        if posts_file.exists():
            with open(posts_file, 'r') as f:
                return set(json.load(f))
        return set()
    
    def save_existing_posts(self):
        """Save list of scraped bulletin IDs"""
        posts_file = Path(__file__).parent / 'scraped_posts.json'
        with open(posts_file, 'w') as f:
            json.dump(list(self.existing_posts), f, indent=2)
    
    def load_config(self):
        """Load products from scraper.yaml"""
        with open(self.config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('products', [])
    
    def fetch_page(self, url):
        """Fetch and parse HTML page"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_bulletins(self, soup, product_name):
        """Extract security bulletin links from product page"""
        bulletins = []
        
        # Find all links that match APSB pattern
        for link in soup.find_all('a', href=re.compile(r'/security/products/.*/apsb\d{2}-\d{2}\.html')):
            href = link.get('href')
            if href:
                # Build full URL
                full_url = urljoin(self.base_url, href)
                
                # Extract bulletin ID
                bulletin_id = re.search(r'(apsb\d{2}-\d{2})', href.lower())
                if bulletin_id:
                    bulletin_id = bulletin_id.group(1).upper()
                    
                    # Skip if already scraped
                    if bulletin_id not in self.existing_posts:
                        bulletins.append({
                            'id': bulletin_id,
                            'url': full_url,
                            'product': product_name
                        })
        
        return bulletins
    
    def parse_bulletin(self, soup, bulletin_info):
        """Parse bulletin page and extract relevant information"""
        data = {
            'id': bulletin_info['id'],
            'url': bulletin_info['url'],
            'product': bulletin_info['product'],
            'title': '',
            'summary': '',
            'published_date': None,
            'severity': '',
            'cve_ids': []
        }
        
        # Extract title
        title_tag = soup.find('h1', class_='page-title')
        if title_tag:
            data['title'] = title_tag.get_text(strip=True)
        else:
            data['title'] = f"{bulletin_info['id'].upper()} - {bulletin_info['product']}"
        
        # Extract date from bulletin ID (APSB25-94 = 2025)
        match = re.match(r'apsb(\d{2})-(\d{2})', bulletin_info['id'].lower())
        if match:
            year = 2000 + int(match.group(1))
            # Estimate month based on bulletin number (rough approximation)
            bulletin_num = int(match.group(2))
            month = min((bulletin_num // 8) + 1, 12)
            data['published_date'] = datetime(year, month, 1)
        
        # Extract summary
        summary_section = soup.find('h2', id='Summary')
        if summary_section:
            summary_content = []
            for sibling in summary_section.find_next_siblings():
                if sibling.name == 'h2':
                    break
                if sibling.name == 'p':
                    summary_content.append(sibling.get_text(strip=True))
            data['summary'] = ' '.join(summary_content)
        
        # Extract CVE IDs
        text = soup.get_text()
        cve_pattern = r'CVE-\d{4}-\d{4,7}'
        data['cve_ids'] = list(set(re.findall(cve_pattern, text)))
        
        # Try to determine severity
        text_lower = text.lower()
        if 'critical' in text_lower:
            data['severity'] = 'Critical'
        elif 'important' in text_lower:
            data['severity'] = 'Important'
        elif 'moderate' in text_lower:
            data['severity'] = 'Moderate'
        elif 'low' in text_lower:
            data['severity'] = 'Low'
        
        return data
    
    def generate_slug(self, title, bulletin_id):
        """Generate URL-friendly slug"""
        # Use bulletin ID as base
        slug = bulletin_id.lower()
        return slug
    
    def create_markdown(self, data):
        """Create markdown file with front matter"""
        # Generate filename
        date = data['published_date'] or datetime.now()
        slug = self.generate_slug(data['title'], data['id'])
        
        # Create directory structure: YYYY/MM/DD/
        date_dir = self.output_dir / str(date.year) / f"{date.month:02d}" / f"{date.day:02d}"
        date_dir.mkdir(parents=True, exist_ok=True)
        
        filename = date_dir / f"{slug}.md"
        
        # Build front matter
        front_matter = {
            'title': f"{data['id'].upper()} - {data['product'].title()} Security Update",
            'date': date.strftime('%Y-%m-%dT%H:%M:%S-05:00'),
            'categories': ['security-bulletins', data['product']],
            'tags': [data['id'].upper(), data['product']]
        }
        
        if data['severity']:
            front_matter['tags'].append(data['severity'])
        
        if data['cve_ids']:
            front_matter['tags'].extend(data['cve_ids'][:5])  # Limit to 5 CVEs
        
        # Build content
        content_parts = []
        
        if data['summary']:
            content_parts.append(data['summary'])
            content_parts.append('')
        
        content_parts.append(f"**Bulletin ID:** {data['id'].upper()}")
        
        if data['severity']:
            content_parts.append(f"**Severity:** {data['severity']}")
        
        if data['cve_ids']:
            content_parts.append(f"**CVE IDs:** {', '.join(data['cve_ids'][:10])}")
        
        content_parts.append('')
        content_parts.append(f"[Read full bulletin]({data['url']})")
        
        content = '\n'.join(content_parts)
        
        # Write file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('---\n')
            for key, value in front_matter.items():
                if isinstance(value, list):
                    f.write(f'{key}:\n')
                    for item in value:
                        f.write(f'  - {item}\n')
                else:
                    f.write(f'{key}: {value}\n')
            f.write('---\n\n')
            f.write(content)
            f.write('\n')
        
        print(f"✓ Created: {filename}")
        return filename
    
    def scrape_product(self, product):
        """Scrape all bulletins for a product"""
        print(f"\n🔍 Scraping {product['name']}...")
        
        # Fetch product page
        soup = self.fetch_page(product['url'])
        if not soup:
            return []
        
        # Extract bulletin links
        bulletins = self.extract_bulletins(soup, product['name'])
        print(f"   Found {len(bulletins)} new bulletins")
        
        created_files = []
        
        # Process each bulletin
        for bulletin in bulletins:
            print(f"   Processing {bulletin['id'].upper()}...")
            
            # Fetch bulletin page
            bulletin_soup = self.fetch_page(bulletin['url'])
            if not bulletin_soup:
                continue
            
            # Parse bulletin
            data = self.parse_bulletin(bulletin_soup, bulletin)
            
            # Create markdown
            try:
                filename = self.create_markdown(data)
                created_files.append(filename)
                self.existing_posts.add(bulletin['id'])
            except Exception as e:
                print(f"   ✗ Error creating markdown for {bulletin['id']}: {e}")
        
        return created_files
    
    def run(self):
        """Main scraper execution"""
        print("🚀 Adobe Security Bulletin Scraper")
        print("=" * 50)
        
        # Load config
        products = self.load_config()
        print(f"Loaded {len(products)} products from config")
        
        all_files = []
        
        # Process each product
        for product in products:
            files = self.scrape_product(product)
            all_files.extend(files)
        
        # Save scraped posts list
        self.save_existing_posts()
        
        print("\n" + "=" * 50)
        print(f"✅ Complete! Created {len(all_files)} new posts")
        
        return all_files


def main():
    scraper = AdobeSecurityScraper()
    scraper.run()


if __name__ == '__main__':
    main()
