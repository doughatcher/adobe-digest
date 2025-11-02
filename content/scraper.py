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
            'priority': '',
            'severity': '',
            'cve_ids': [],
            'affected_versions': [],
            'solution': '',
            'vulnerabilities': [],
            'acknowledgements': []
        }
        
        # Extract title
        title_tag = soup.find('h1', class_='page-title')
        if title_tag:
            data['title'] = title_tag.get_text(strip=True)
        else:
            data['title'] = f"{bulletin_info['id'].upper()} - {bulletin_info['product']}"
        
        # Extract date and priority from first table
        tables = soup.find_all('table')
        if tables:
            first_table = tables[0]
            rows = first_table.find_all('tr')
            if len(rows) > 1:
                cells = rows[1].find_all(['td', 'th'])
                if len(cells) >= 2:
                    # Parse date
                    date_text = cells[1].get_text(strip=True)
                    try:
                        data['published_date'] = datetime.strptime(date_text, '%B %d, %Y')
                    except:
                        pass
                if len(cells) >= 3:
                    data['priority'] = cells[2].get_text(strip=True)
        
        # Fallback date extraction from bulletin ID
        if not data['published_date']:
            match = re.match(r'apsb(\d{2})-(\d{2})', bulletin_info['id'].lower())
            if match:
                year = 2000 + int(match.group(1))
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
        
        # Extract affected versions from second table
        if len(tables) > 1:
            version_table = tables[1]
            rows = version_table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    product = cells[0].get_text(strip=True)
                    version = cells[1].get_text(strip=True)
                    if product and version:
                        data['affected_versions'].append({
                            'product': product,
                            'version': version
                        })
        
        # Extract solution
        solution_section = soup.find('h2', id='Solution')
        if solution_section:
            solution_content = []
            for sibling in solution_section.find_next_siblings():
                if sibling.name == 'h2':
                    break
                if sibling.name in ['p', 'ul', 'ol']:
                    solution_content.append(sibling.get_text(strip=True))
            data['solution'] = ' '.join(solution_content)
        
        # Extract vulnerability details
        vuln_section = soup.find('h2', string='Vulnerability Details')
        if vuln_section:
            vuln_table = vuln_section.find_next('table')
            if vuln_table:
                headers = [th.get_text(strip=True) for th in vuln_table.find_all('th')]
                rows = vuln_table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 8:
                        vuln = {
                            'category': cells[0].get_text(strip=True),
                            'impact': cells[1].get_text(strip=True),
                            'severity': cells[2].get_text(strip=True),
                            'auth_required': cells[3].get_text(strip=True),
                            'admin_required': cells[4].get_text(strip=True),
                            'cvss_score': cells[5].get_text(strip=True),
                            'cvss_vector': cells[6].get_text(strip=True),
                            'cve': cells[7].get_text(strip=True)
                        }
                        data['vulnerabilities'].append(vuln)
                        
                        # Add CVE to list
                        cve_ids = re.findall(r'CVE-\d{4}-\d{4,7}', vuln['cve'])
                        data['cve_ids'].extend(cve_ids)
        
        # Remove duplicate CVEs
        data['cve_ids'] = list(set(data['cve_ids']))
        
        # Extract acknowledgements
        ack_section = soup.find('h2', id='Acknowledgements')
        if ack_section:
            ack_content = []
            for sibling in ack_section.find_next_siblings():
                if sibling.name == 'h2':
                    break
                if sibling.name in ['p', 'ul']:
                    ack_content.append(sibling.get_text(strip=True))
            data['acknowledgements'] = ack_content
        
        # Determine overall severity from vulnerabilities
        severities = [v['severity'] for v in data['vulnerabilities'] if v.get('severity')]
        if 'Critical' in severities:
            data['severity'] = 'Critical'
        elif 'Important' in severities:
            data['severity'] = 'Important'
        elif 'Moderate' in severities:
            data['severity'] = 'Moderate'
        elif 'Low' in severities:
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
            front_matter['tags'].extend(data['cve_ids'][:10])  # Include up to 10 CVEs
        
        # Build content
        content_parts = []
        
        # Summary
        if data['summary']:
            content_parts.append(f"## Summary\n")
            content_parts.append(data['summary'])
            content_parts.append('')
        
        # Bulletin metadata
        content_parts.append(f"## Bulletin Information\n")
        content_parts.append(f"- **Bulletin ID:** {data['id'].upper()}")
        content_parts.append(f"- **Published:** {date.strftime('%B %d, %Y')}")
        
        if data['priority']:
            content_parts.append(f"- **Priority:** {data['priority']}")
        
        if data['severity']:
            content_parts.append(f"- **Severity:** {data['severity']}")
        
        if data['cve_ids']:
            content_parts.append(f"- **CVE Count:** {len(data['cve_ids'])}")
        
        content_parts.append('')
        
        # Affected versions
        if data['affected_versions']:
            content_parts.append(f"## Affected Versions\n")
            for av in data['affected_versions'][:5]:  # Limit to first 5
                content_parts.append(f"- **{av['product']}:** {av['version']}")
            if len(data['affected_versions']) > 5:
                content_parts.append(f"- *...and {len(data['affected_versions']) - 5} more versions*")
            content_parts.append('')
        
        # Solution
        if data['solution']:
            content_parts.append(f"## Solution\n")
            content_parts.append(data['solution'][:500])  # Limit length
            if len(data['solution']) > 500:
                content_parts.append('...')
            content_parts.append('')
        
        # Vulnerability details
        if data['vulnerabilities']:
            content_parts.append(f"## Vulnerability Details\n")
            content_parts.append(f"**Total Vulnerabilities:** {len(data['vulnerabilities'])}\n")
            
            # Count by severity
            severity_counts = {}
            for v in data['vulnerabilities']:
                sev = v.get('severity', 'Unknown')
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            if severity_counts:
                content_parts.append(f"**Severity Breakdown:**")
                for sev, count in sorted(severity_counts.items(), reverse=True):
                    content_parts.append(f"- **{sev}:** {count}")
                content_parts.append('')
            
            # List first 3 vulnerabilities with details
            content_parts.append(f"**Key Vulnerabilities:**\n")
            for i, vuln in enumerate(data['vulnerabilities'][:3], 1):
                content_parts.append(f"### {i}. {vuln.get('cve', 'Unknown CVE')}")
                content_parts.append(f"- **Category:** {vuln.get('category', 'N/A')}")
                content_parts.append(f"- **Impact:** {vuln.get('impact', 'N/A')}")
                content_parts.append(f"- **Severity:** {vuln.get('severity', 'N/A')}")
                content_parts.append(f"- **CVSS Score:** {vuln.get('cvss_score', 'N/A')}")
                if vuln.get('auth_required'):
                    content_parts.append(f"- **Authentication Required:** {vuln.get('auth_required')}")
                content_parts.append('')
            
            if len(data['vulnerabilities']) > 3:
                content_parts.append(f"*...and {len(data['vulnerabilities']) - 3} more vulnerabilities*\n")
        
        # CVE list
        if data['cve_ids']:
            content_parts.append(f"## CVE Identifiers\n")
            content_parts.append(', '.join(data['cve_ids']))
            content_parts.append('')
        
        # Acknowledgements
        if data['acknowledgements']:
            content_parts.append(f"## Acknowledgements\n")
            for ack in data['acknowledgements'][:3]:  # Limit to first 3
                content_parts.append(f"- {ack[:200]}")
            content_parts.append('')
        
        # Link to full bulletin
        content_parts.append(f"---\n")
        content_parts.append(f"[**Read Full Bulletin on Adobe Security Portal →**]({data['url']})")
        
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
