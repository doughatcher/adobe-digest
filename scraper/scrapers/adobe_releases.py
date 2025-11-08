#!/usr/bin/env python3
"""
Adobe Commerce Release Notes Scraper
Fetches release notes from experienceleague.adobe.com
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin


class AdobeReleasesScraper:
    """Scraper for Adobe Commerce and Magento Open Source release notes"""
    
    def __init__(self, output_dir, existing_posts=None):
        """Initialize scraper"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.base_url = 'https://experienceleague.adobe.com'
        self.existing_posts = existing_posts or set()
        
    def fetch_page(self, url):
        """Fetch and parse HTML page"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"   ✗ Error fetching {url}: {e}")
            return None
    
    def extract_releases_from_versions_page(self, soup, product_name):
        """
        Extract release links from the versions page
        Returns list of releases with version and link to release notes
        """
        releases = []
        
        # Find all links that point to release notes
        # Look for links containing /release/notes/ and version patterns
        # This handles both /adobe-commerce/ and /magento-open-source/ paths
        all_links = soup.find_all('a', href=True)
        
        total_found = 0
        skipped = 0
        seen_versions = set()
        
        for link in all_links:
            href = link.get('href', '')
            
            # Skip empty hrefs
            if not href:
                continue
            
            # Must contain /release/notes/ to be a release notes link
            if '/release/notes/' not in href:
                continue
            
            # Must contain adobe-commerce or magento-open-source
            if not ('adobe-commerce' in href or 'magento-open-source' in href):
                continue
            
            # Extract version from URL - looking for patterns like:
            # /2-4-7, /2-4-6-p3, /2.4.7, etc.
            version_match = re.search(r'/(\d+[-\.]\d+[-\.]\d+(?:[-\.]p\d+)?)(?:/|$|\?|#)', href)
            if not version_match:
                continue
            
            version_raw = version_match.group(1)
            # Normalize version format to use hyphens (2.4.7 -> 2-4-7)
            version = version_raw.replace('.', '-')
            
            # Avoid duplicates from the same page
            if version in seen_versions:
                continue
            seen_versions.add(version)
            
            total_found += 1
            
            # Create a unique ID for this release
            release_id = f"{product_name}-{version}"
            
            # Skip if already scraped
            if release_id in self.existing_posts:
                skipped += 1
                continue
            
            # Build full URL
            full_url = urljoin(self.base_url, href)
            
            releases.append({
                'id': release_id,
                'version': version,
                'url': full_url,
                'product': product_name
            })
        
        if total_found > 0:
            if skipped > 0:
                print(f"   ℹ️  Skipped {skipped} existing releases")
            print(f"   📥 Found {len(releases)} new releases to scrape")
        else:
            print(f"   ℹ️  No releases found")
        
        return releases
    
    def parse_release_notes(self, soup, release_info):
        """Parse release notes page and extract relevant information"""
        data = {
            'id': release_info['id'],
            'url': release_info['url'],
            'version': release_info['version'],
            'product': release_info['product'],
            'title': '',
            'summary': '',
            'published_date': None,
            'highlights': [],
            'security_fixes': [],
            'platform_upgrades': [],
            'fixed_issues': [],
        }
        
        # Extract title
        title_tag = soup.find('h1')
        if title_tag:
            data['title'] = title_tag.get_text(strip=True)
        else:
            product_display = release_info['product'].replace('-', ' ').title()
            data['title'] = f"{product_display} {release_info['version']} Release Notes"
        
        # Try to extract date from various sources
        # 1. Check meta tags first (most reliable)
        meta_date = soup.find('meta', attrs={'name': 'date'})
        if meta_date and meta_date.get('content'):
            try:
                # Try ISO format first
                date_str = meta_date.get('content')
                if 'T' in date_str:
                    data['published_date'] = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    data['published_date'] = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                pass
        
        # 2. Look for "Release date" or "Published" in the page content
        if not data['published_date']:
            page_text = soup.get_text()
            # Try various date patterns
            date_patterns = [
                (r'Release date[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})', '%B %d, %Y'),
                (r'Released[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})', '%B %d, %Y'),
                (r'Published[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})', '%B %d, %Y'),
                (r'Release date[:\s]+(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),
                (r'(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})', '%d %B %Y'),  # e.g., "9 April 2024"
                (r'([A-Z][a-z]+\s+\d{4})', '%B %Y'),  # e.g., "April 2024" (fallback to first of month)
            ]
            
            for pattern, date_format in date_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    try:
                        date_str = match.group(1)
                        data['published_date'] = datetime.strptime(date_str, date_format)
                        break
                    except:
                        continue
        
        # 3. Look in tables (Adobe often uses tables for release info)
        if not data['published_date']:
            tables = soup.find_all('table')
            for table in tables[:3]:  # Check first 3 tables
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for i, cell in enumerate(cells):
                        cell_text = cell.get_text(strip=True)
                        # Check if this cell mentions a date-related term
                        if re.search(r'release|published|date', cell_text, re.IGNORECASE):
                            # Check next cell or same cell for date
                            date_cell = cells[i + 1] if i + 1 < len(cells) else cell
                            date_text = date_cell.get_text(strip=True)
                            # Try to parse as date
                            for date_format in ['%B %d, %Y', '%B %Y', '%Y-%m-%d', '%d %B %Y']:
                                try:
                                    data['published_date'] = datetime.strptime(date_text, date_format)
                                    break
                                except:
                                    continue
                            if data['published_date']:
                                break
                if data['published_date']:
                    break
        
        # 4. Fallback: Try to infer from version and current knowledge
        # Security patches (pX) are usually released quarterly
        if not data['published_date']:
            version = release_info.get('version', '')
            # Try to extract year from context or make educated guess based on version
            # For 2.4.x versions, these were released starting in 2020
            version_match = re.match(r'(\d+)[-\.](\d+)[-\.](\d+)(?:[-\.]p(\d+))?', version)
            if version_match:
                major, minor, patch, security_patch = version_match.groups()
                # Rough estimation: 2.4.x started in 2020, increment year with minor version
                base_year = 2020 + int(minor) if int(major) == 2 else 2024
                base_month = (int(patch) * 3) % 12 or 12  # Rough quarterly estimate
                data['published_date'] = datetime(base_year, base_month, 1)
            else:
                # Last resort: use a date in the past (not today) to avoid sorting issues
                # Use January 1st of current year as a neutral fallback
                data['published_date'] = datetime(datetime.now().year, 1, 1)
        
        # Extract highlights section
        highlights_section = soup.find(['h2', 'h3'], string=re.compile(r'Highlights?|What\'s New', re.IGNORECASE))
        if highlights_section:
            content = []
            for sibling in highlights_section.find_next_siblings():
                if sibling.name in ['h2', 'h3']:
                    break
                if sibling.name == 'ul':
                    items = [li.get_text(strip=True) for li in sibling.find_all('li')]
                    content.extend(items[:5])  # Limit to first 5
                elif sibling.name == 'p':
                    text = sibling.get_text(strip=True)
                    if text:
                        content.append(text)
            data['highlights'] = content[:5]  # Limit to 5 items
        
        # Extract security section
        security_section = soup.find(['h2', 'h3'], string=re.compile(r'Security', re.IGNORECASE))
        if security_section:
            content = []
            for sibling in security_section.find_next_siblings():
                if sibling.name in ['h2', 'h3']:
                    break
                if sibling.name == 'ul':
                    items = [li.get_text(strip=True) for li in sibling.find_all('li')]
                    content.extend(items[:3])  # Limit to first 3
                elif sibling.name == 'p':
                    text = sibling.get_text(strip=True)
                    if text and len(content) < 3:
                        content.append(text)
            data['security_fixes'] = content[:3]  # Limit to 3 items
        
        # Extract platform upgrades section
        platform_section = soup.find(['h2', 'h3'], string=re.compile(r'Platform', re.IGNORECASE))
        if platform_section:
            content = []
            for sibling in platform_section.find_next_siblings():
                if sibling.name in ['h2', 'h3']:
                    break
                if sibling.name == 'ul':
                    items = [li.get_text(strip=True) for li in sibling.find_all('li')]
                    content.extend(items[:3])
                elif sibling.name == 'p':
                    text = sibling.get_text(strip=True)
                    if text and len(content) < 3:
                        content.append(text)
            data['platform_upgrades'] = content[:3]
        
        # Build summary from first paragraph or highlights
        if data['highlights']:
            data['summary'] = ' '.join(data['highlights'][:2])[:300]
        else:
            # Try to get first meaningful paragraph
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50:  # Only consider substantial paragraphs
                    data['summary'] = text[:300]
                    break
        
        return data
    
    def create_markdown(self, data):
        """Create markdown file with Micro.blog front matter"""
        date = data['published_date'] or datetime.now()
        
        # Create slug from version
        slug = f"{data['id']}"
        
        # Create directory structure: YYYY/MM/DD/
        date_dir = self.output_dir / str(date.year) / f"{date.month:02d}" / f"{date.day:02d}"
        date_dir.mkdir(parents=True, exist_ok=True)
        
        filename = date_dir / f"{slug}.md"
        
        # Build Micro.blog compatible front matter
        url_path = f"/{date.year}/{date.month:02d}/{date.day:02d}/{slug}.html"
        
        # Normalize product name for category
        product_category = data['product'].replace('_', '-').lower()
        
        # Get categories from source config (passed in data)
        source_categories = data.get('source_categories', [])
        
        # Determine if this is a security release
        is_security = 'p' in data['version'].lower() or bool(data['security_fixes'])
        
        front_matter = {
            'layout': 'post',
            'title': data['title'],
            'microblog': False,
            'guid': f"http://adobedigest.micro.blog{url_path}",
            'date': date.strftime('%Y-%m-%dT%H:%M:%S-05:00'),
            'type': 'post',
            'url': url_path,
            'categories': ['releases', product_category] + source_categories,
            'tags': [data['version'], product_category, 'release-notes', data.get('source_name', '')]
        }
        
        # Add security tag if applicable
        if is_security:
            front_matter['tags'].append('security-release')
        
        # Build content
        content_parts = []
        
        # Summary
        if data['summary']:
            content_parts.append(f"## Overview\n")
            content_parts.append(data['summary'])
            content_parts.append('')
        
        # Release metadata
        content_parts.append(f"## Release Information\n")
        content_parts.append(f"- **Version:** {data['version']}")
        product_display = data['product'].replace('-', ' ').title()
        content_parts.append(f"- **Product:** {product_display}")
        content_parts.append(f"- **Released:** {date.strftime('%B %d, %Y')}")
        content_parts.append('')
        
        # Highlights
        if data['highlights']:
            content_parts.append(f"## Highlights\n")
            for highlight in data['highlights']:
                content_parts.append(f"- {highlight}")
            content_parts.append('')
        
        # Security fixes
        if data['security_fixes']:
            content_parts.append(f"## Security Enhancements\n")
            for fix in data['security_fixes']:
                content_parts.append(f"- {fix}")
            content_parts.append('')
        
        # Platform upgrades
        if data['platform_upgrades']:
            content_parts.append(f"## Platform Upgrades\n")
            for upgrade in data['platform_upgrades']:
                content_parts.append(f"- {upgrade}")
            content_parts.append('')
        
        # Link to full release notes
        content_parts.append(f"---\n")
        content_parts.append(f"[**Read Full Release Notes →**]({data['url']})")
        
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
        Scrape release notes for Adobe Commerce or Magento Open Source
        
        Config format:
        {
            'name': 'adobe-commerce-releases',
            'type': 'adobe-release-notes',
            'url': 'https://experienceleague.adobe.com/en/docs/commerce-operations/release/versions',
            'product': 'adobe-commerce',  # or 'magento-open-source'
            'categories': []  # Optional categories to add
        }
        """
        source_name = config.get('name', 'unknown')
        product = config.get('product', 'adobe-commerce')
        source_categories = config.get('categories', [])
        
        print(f"\n🔍 Scraping {source_name} release notes...")
        
        # Fetch the versions page
        soup = self.fetch_page(config['url'])
        if not soup:
            return []
        
        # Extract release links from the versions page
        releases = self.extract_releases_from_versions_page(soup, product)
        
        created_files = []
        
        # Process each release
        for release in releases:
            print(f"   Processing {release['version']}...")
            
            # Fetch release notes page
            release_soup = self.fetch_page(release['url'])
            if not release_soup:
                continue
            
            # Parse release notes
            data = self.parse_release_notes(release_soup, release)
            
            # Add source info to data for markdown generation
            data['source_name'] = source_name
            data['source_categories'] = source_categories
            
            # Create markdown
            try:
                filename = self.create_markdown(data)
                created_files.append(filename)
                self.existing_posts.add(release['id'])
            except Exception as e:
                print(f"   ✗ Error creating markdown for {release['id']}: {e}")
        
        return created_files
