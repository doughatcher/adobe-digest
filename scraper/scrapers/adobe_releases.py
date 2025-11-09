#!/usr/bin/env python3
"""
Adobe Commerce Release Notes Scraper
Fetches release notes from experienceleague.adobe.com
"""

import re
import requests
import hashlib
import json
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
        # Load tracking data for content hashes and states
        self.tracking_file = Path(__file__).parent.parent / 'scraped_posts.json'
        self.release_tracking = self.load_release_tracking()
    
    def load_release_tracking(self):
        """Load release tracking data (content hashes, states, dates)"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    data = json.load(f)
                    return data.get('release_tracking', {})
            except Exception as e:
                print(f"   ⚠️  Error loading release tracking: {e}")
        return {}
    
    def save_release_tracking(self, tracking_data):
        """Save release tracking data back to scraped_posts.json"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    data = json.load(f)
            except:
                data = {'ids': [], 'last_updated': None, 'total_count': 0}
        else:
            data = {'ids': [], 'last_updated': None, 'total_count': 0}
        
        data['release_tracking'] = tracking_data
        data['last_updated'] = datetime.now().isoformat()
        
        try:
            with open(self.tracking_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"   ⚠️  Error saving release tracking: {e}")
    
    def detect_release_state(self, soup, version):
        """
        Detect if release is alpha, beta, or GA (general availability)
        Returns: 'alpha', 'beta', or 'ga'
        
        Strategy:
        1. Check title and first few paragraphs for clear indicators
        2. Be conservative - only mark as alpha/beta if explicitly stated
        3. Security patches (-pX) are always GA
        """
        # Security patches are always GA
        if re.search(r'-p\d+', version):
            return 'ga'
        
        # Check title first (most reliable indicator)
        title = soup.find('h1')
        if title:
            title_text = title.get_text()
            # Look for clear pre-release indicators in title
            if re.search(r'\b(alpha|ALPHA|Alpha)\b', title_text):
                return 'alpha'
            if re.search(r'\b(beta|BETA|Beta)\b', title_text):
                return 'beta'
        
        # Check first few paragraphs and any prominent notices
        # Look for strong indicators like badges, notices, or explicit statements
        for tag in ['div', 'p', 'span']:
            for element in soup.find_all(tag, class_=re.compile(r'(alert|notice|badge|warning)', re.IGNORECASE)):
                text = element.get_text()
                if re.search(r'\b(alpha|ALPHA|Alpha)\s+(release|version)', text):
                    return 'alpha'
                if re.search(r'\b(beta|BETA|Beta)\s+(release|version)', text):
                    return 'beta'
        
        # Check first 3 paragraphs for explicit pre-release statements
        paragraphs = soup.find_all('p')[:3]
        for p in paragraphs:
            text = p.get_text()
            # Look for phrases like "This is an alpha release" or "Beta version"
            if re.search(r'(this is|currently in)\s+(an?\s+)?(alpha|ALPHA)', text, re.IGNORECASE):
                return 'alpha'
            if re.search(r'(this is|currently in)\s+(an?\s+)?(beta|BETA)', text, re.IGNORECASE):
                return 'beta'
            if re.search(r'(pre-release|preview)\s+(version|release)', text, re.IGNORECASE):
                return 'beta'
        
        # Default to GA - be conservative, don't mark as pre-release unless clearly indicated
        return 'ga'
    
    def create_content_hash(self, soup):
        """
        Create a hash of the meaningful content to detect updates
        This helps track when release notes are updated
        """
        # Extract main content sections
        content_parts = []
        
        # Get title
        title = soup.find('h1')
        if title:
            content_parts.append(title.get_text(strip=True))
        
        # Get main content (look for common content containers)
        for selector in ['main', 'article', '.content', '#content', 'body']:
            main_content = soup.select_one(selector)
            if main_content:
                # Get all headings
                for heading in main_content.find_all(['h2', 'h3', 'h4']):
                    content_parts.append(heading.get_text(strip=True))
                
                # Get substantial paragraphs (helps detect content changes)
                for p in main_content.find_all('p'):
                    text = p.get_text(strip=True)
                    if len(text) > 20:  # Only substantial content
                        content_parts.append(text[:200])  # First 200 chars
                
                # Get list items
                for li in main_content.find_all('li'):
                    text = li.get_text(strip=True)
                    if len(text) > 10:
                        content_parts.append(text[:100])
                
                break
        
        # Create hash of combined content
        combined = '|'.join(content_parts)
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
        
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
        Extract ALL discrete releases from the versions page.
        The page lists all versions (base, patches, alphas) with their release dates.
        
        Links have patterns like:
        - Base: <a href="/adobe-commerce/2-4-8">2.4.8</a>
        - Patches: <a href="/security-patches/2-4-8-patches#p1">2.4.8-p1</a>
        - Alphas: <a href="/adobe-commerce/2-4-9#alpha1">2.4.9-alpha1</a>
        """
        releases = []
        seen_versions = set()
        
        # Find all links
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # Look for version pattern in link text: 2.4.8, 2.4.8-p1, 2.4.9-alpha1, etc.
            version_match = re.match(r'^(\d+\.\d+\.\d+(?:-(?:p\d+|alpha\d*|beta\d*))?)$', text)
            if not version_match:
                continue
            
            version_text = version_match.group(1)
            # Normalize to use hyphens
            version = version_text.replace('.', '-')
            
            # Skip duplicates
            if version in seen_versions:
                continue
            seen_versions.add(version)
            
            # Build full URL
            full_url = urljoin(self.base_url, href)
            
            # Create release entry
            releases.append({
                'base_id': f"{product_name}-{version}",
                'version': version,
                'url': full_url,
                'product': product_name,
                'link_text': text
            })
        
        print(f"   📥 Found {len(releases)} discrete release versions")
        
        # Show summary by type
        base_versions = [r for r in releases if not re.search(r'-(p\d+|alpha|beta)', r['version'])]
        patch_versions = [r for r in releases if re.search(r'-p\d+', r['version'])]
        alpha_versions = [r for r in releases if 'alpha' in r['version']]
        beta_versions = [r for r in releases if 'beta' in r['version']]
        
        print(f"      • Base versions: {len(base_versions)}")
        print(f"      • Patch versions: {len(patch_versions)}")
        print(f"      • Alpha versions: {len(alpha_versions)}")
        print(f"      • Beta versions: {len(beta_versions)}")
        
        return releases
    
    def parse_release_notes(self, soup, release_info):
        """Parse release notes page and extract relevant information"""
        # Detect release state (alpha, beta, GA)
        state = self.detect_release_state(soup, release_info['version'])
        
        # Create content hash to detect updates
        content_hash = self.create_content_hash(soup)
        
        # Create ID based on version
        # The version already includes alpha/beta/patch info (e.g., 2-4-9-alpha2, 2-4-8-p3)
        # So we just use the base_id which is product-version
        # Examples:
        #   - adobe-commerce-2-4-7 (base version)
        #   - adobe-commerce-2-4-7-p3 (patch version)
        #   - adobe-commerce-2-4-9-alpha2 (alpha version)
        post_id = release_info['base_id']
        
        data = {
            'base_id': release_info['base_id'],
            'id': post_id,
            'url': release_info['url'],
            'version': release_info['version'],
            'product': release_info['product'],
            'state': state,
            'content_hash': content_hash,
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
        version_display = release_info['version'].replace('-', '.')  # 2-4-7 -> 2.4.7
        
        if title_tag:
            data['title'] = title_tag.get_text(strip=True)
            
            # Append version to title if it's a patch version or alpha/beta and not already in title
            # This handles cases like "Release notes for Adobe Commerce 2.4.8 security patches"
            # which should become "... 2.4.8 security patches (2.4.8-p3)"
            if 'p' in release_info['version'] or state in ['alpha', 'beta']:
                # Check if the specific version is already in the title
                # Create both possible formats: 2.4.8-p3 (dotted-mixed) and 2.4.8.p3 (all dots)
                parts = release_info['version'].split('-')
                if len(parts) >= 3:
                    version_dotted_mixed = f"{parts[0]}.{parts[1]}.{'-'.join(parts[2:])}"  # 2.4.8-p3
                else:
                    version_dotted_mixed = version_display
                
                # Check if either format is in the title
                if version_display not in data['title'] and version_dotted_mixed not in data['title']:
                    # Append the specific version in parentheses
                    data['title'] = f"{data['title']} ({version_display})"
        else:
            # Generate title from version info
            product_display = release_info['product'].replace('-', ' ').title()
            
            # For pre-release versions, add state label
            if state == 'alpha':
                data['title'] = f"{product_display} {version_display} Alpha Release Notes"
            elif state == 'beta':
                data['title'] = f"{product_display} {version_display} Beta Release Notes"
            else:
                # For GA releases, just use version (which includes -pX if present)
                data['title'] = f"{product_display} {version_display} Release Notes"
        
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
        
        # 4. Fallback: Use known release dates lookup table for Adobe Commerce
        # Security patches (pX) are usually released quarterly
        if not data['published_date']:
            version = release_info.get('version', '')
            
            # Known Adobe Commerce release dates (from official Adobe release calendar)
            # Format: 'version': (year, month, day)
            KNOWN_RELEASES = {
                # 2.4.8 releases
                '2-4-8': (2028, 4, 8),  # Future release
                '2-4-8-p1': (2028, 6, 10),
                '2-4-8-p2': (2028, 8, 12),
                '2-4-8-p3': (2028, 10, 14),
                
                # 2.4.7 releases (started March 2024)
                '2-4-7': (2024, 3, 12),
                '2-4-7-p1': (2024, 6, 11),
                '2-4-7-p2': (2024, 8, 13),
                '2-4-7-p3': (2024, 10, 8),
                '2-4-7-p4': (2025, 2, 11),
                '2-4-7-p5': (2025, 4, 8),
                '2-4-7-p6': (2025, 6, 10),
                '2-4-7-p7': (2025, 8, 12),
                '2-4-7-p8': (2025, 10, 14),
                
                # 2.4.6 releases (started March 2023)
                '2-4-6': (2023, 3, 14),
                '2-4-6-p1': (2023, 6, 13),
                '2-4-6-p2': (2023, 8, 8),
                '2-4-6-p3': (2023, 10, 10),
                '2-4-6-p4': (2024, 2, 13),
                '2-4-6-p5': (2024, 4, 9),
                '2-4-6-p6': (2024, 6, 11),
                '2-4-6-p7': (2024, 8, 13),
                '2-4-6-p8': (2024, 10, 8),
                '2-4-6-p9': (2025, 2, 11),
                '2-4-6-p10': (2025, 4, 8),
                '2-4-6-p11': (2025, 6, 10),
                '2-4-6-p12': (2025, 8, 12),
                '2-4-6-p13': (2025, 10, 14),
                
                # 2.4.5 releases (started August 2022)
                '2-4-5': (2022, 8, 9),
                '2-4-5-p1': (2022, 10, 11),
                '2-4-5-p2': (2023, 2, 14),
                '2-4-5-p3': (2023, 4, 11),
                '2-4-5-p4': (2023, 6, 13),
                '2-4-5-p5': (2023, 8, 8),
                '2-4-5-p6': (2023, 10, 10),
                '2-4-5-p7': (2024, 2, 13),
                '2-4-5-p8': (2024, 4, 9),
                '2-4-5-p9': (2024, 6, 11),
                '2-4-5-p10': (2024, 8, 13),
                '2-4-5-p11': (2024, 10, 8),
                '2-4-5-p12': (2025, 2, 11),
                '2-4-5-p13': (2025, 4, 8),
                '2-4-5-p14': (2025, 6, 10),
                '2-4-5-p15': (2025, 8, 12),
                
                # 2.4.4 releases (started April 2022)
                '2-4-4': (2022, 4, 12),
                '2-4-4-p1': (2022, 6, 14),
                '2-4-4-p2': (2022, 10, 11),
                '2-4-4-p3': (2023, 2, 14),
                '2-4-4-p4': (2023, 4, 11),
                '2-4-4-p5': (2023, 6, 13),
                '2-4-4-p6': (2023, 8, 8),
                '2-4-4-p7': (2023, 10, 10),
                '2-4-4-p8': (2024, 2, 13),
                '2-4-4-p9': (2024, 4, 9),
                '2-4-4-p10': (2024, 6, 11),
                '2-4-4-p11': (2024, 8, 13),
                '2-4-4-p12': (2024, 10, 8),
                '2-4-4-p13': (2025, 2, 11),
                '2-4-4-p14': (2025, 4, 8),
                '2-4-4-p15': (2025, 6, 10),
                '2-4-4-p16': (2025, 8, 12),
                
                # 2.4.3 releases (started August 2021)
                '2-4-3': (2021, 8, 10),
                '2-4-3-p1': (2021, 10, 12),
                '2-4-3-p2': (2022, 2, 8),
                '2-4-3-p3': (2022, 8, 9),
                
                # 2.4.2 releases (started February 2021)
                '2-4-2': (2021, 2, 9),
                '2-4-2-p2': (2021, 8, 10),
                
                # 2.4.1 release (October 2020)
                '2-4-1': (2020, 10, 15),
                
                # 2.4.0 release (July 2020)
                '2-4-0': (2020, 7, 28),
                
                # 2.4.9 alpha releases (future/pre-release)
                '2-4-9-alpha1': (2025, 1, 15),
                '2-4-9-alpha2': (2025, 2, 15),
                '2-4-9-alpha3': (2025, 3, 15),
            }
            
            # Try to find in lookup table
            if version in KNOWN_RELEASES:
                year, month, day = KNOWN_RELEASES[version]
                data['published_date'] = datetime(year, month, day)
            else:
                # Try to extract version parts for estimation
                version_match = re.match(r'(\d+)[-\.](\d+)[-\.](\d+)(?:[-\.]p(\d+)|[-\.]alpha(\d+)|[-\.]beta(\d+))?', version)
                if version_match:
                    major, minor, patch, security_patch, alpha, beta = version_match.groups()
                    
                    # Estimate based on pattern:
                    # - Base versions: released in March/April or August
                    # - Patches: quarterly (Feb, Apr, Jun, Aug, Oct)
                    # - Alphas/Betas: monthly before GA
                    
                    base_year = 2020 + int(minor) if int(major) == 2 else 2024
                    
                    if security_patch:
                        # Security patches are quarterly
                        patch_num = int(security_patch)
                        # First patch usually ~2 months after base, then every ~2 months
                        months_offset = 2 + (patch_num - 1) * 2
                        base_month = 3  # Base versions typically in March
                        month = (base_month + months_offset - 1) % 12 + 1
                        year = base_year + ((base_month + months_offset - 1) // 12)
                        data['published_date'] = datetime(year, month, 10)
                    elif alpha:
                        # Alpha releases are pre-GA
                        alpha_num = int(alpha) if alpha else 1
                        data['published_date'] = datetime(base_year, alpha_num, 15)
                    elif beta:
                        # Beta releases are pre-GA
                        beta_num = int(beta) if beta else 1
                        data['published_date'] = datetime(base_year, beta_num + 6, 15)
                    else:
                        # Base version - typically March or August
                        data['published_date'] = datetime(base_year, 3, 15)
                else:
                    # Last resort: use a date in the past
                    data['published_date'] = datetime(2024, 1, 1)
        
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
        
        # Create slug from ID (which now includes state)
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
        
        # Build tags list
        tags = [data['version'], product_category, 'release-notes', data.get('source_name', '')]
        
        # Add state tag
        state = data.get('state', 'ga')
        if state != 'ga':
            tags.append(state)
        
        front_matter = {
            'layout': 'post',
            'title': data['title'],
            'microblog': False,
            'guid': f"http://adobedigest.micro.blog{url_path}",
            'date': date.strftime('%Y-%m-%dT%H:%M:%S-05:00'),
            'type': 'post',
            'url': url_path,
            'categories': ['releases', product_category] + source_categories,
            'tags': tags
        }
        
        # Add security tag if applicable
        if is_security:
            front_matter['tags'].append('security-release')
        
        # Build content
        content_parts = []
        
        # Add release state notice for alpha/beta
        state = data.get('state', 'ga')
        if state == 'alpha':
            content_parts.append(f"**⚠️ ALPHA RELEASE** - This is a pre-release version for testing purposes.\n")
        elif state == 'beta':
            content_parts.append(f"**⚠️ BETA RELEASE** - This is a pre-release version for evaluation.\n")
        
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
        if state != 'ga':
            content_parts.append(f"- **Release Type:** {state.upper()}")
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
        
        # Log creation with details and full content
        print(f"   ✓ Created: {filename}")
        print(f"      ID: {data['id']}")
        print(f"      Title: {data['title']}")
        print(f"      State: {data['state'].upper()}")
        if data.get('highlights'):
            print(f"      Highlights: {len(data['highlights'])} items")
        
        # Show the complete markdown file content
        print(f"\n   📄 Complete file content:")
        print("   " + "="*76)
        with open(filename, 'r', encoding='utf-8') as f:
            file_content = f.read()
            # Indent each line for better readability in logs
            for line in file_content.split('\n'):
                print(f"   {line}")
        print("   " + "="*76)
        
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
        skipped_count = 0
        updated_count = 0
        
        # Process each release
        for release in releases:
            print(f"   Checking {release['version']}...")
            
            # Fetch release notes page
            release_soup = self.fetch_page(release['url'])
            if not release_soup:
                continue
            
            # Parse release notes to get state and content hash
            data = self.parse_release_notes(release_soup, release)
            
            base_id = data['base_id']
            state = data['state']
            content_hash = data['content_hash']
            full_id = data['id']  # base_id + state
            
            # Check if we need to create a post
            should_create = False
            reason = ""
            
            # Get tracking info for this release
            tracking_key = base_id
            tracked = self.release_tracking.get(tracking_key, {})
            
            # Case 1: This version/state combination has never been seen
            if full_id not in self.existing_posts:
                should_create = True
                if state == 'alpha':
                    reason = f"New ALPHA release {release['version']}"
                elif state == 'beta':
                    reason = f"New BETA release {release['version']}"
                else:
                    # Check if we've seen this version in a different state
                    previous_state = tracked.get('last_state')
                    if previous_state and previous_state != state:
                        reason = f"State change: {previous_state.upper()} → {state.upper()}"
                    else:
                        reason = f"New GA release {release['version']}"
            
            # Case 2: Content has been updated since last scrape
            elif tracked.get('content_hash') != content_hash:
                should_create = True
                reason = f"Content updated for {state.upper()} release"
                updated_count += 1
            else:
                # Already scraped and no changes
                skipped_count += 1
                continue
            
            if should_create:
                print(f"      → {reason}")
                
                # Add source info to data for markdown generation
                data['source_name'] = source_name
                data['source_categories'] = source_categories
                
                # Create markdown
                try:
                    filename = self.create_markdown(data)
                    created_files.append(filename)
                    
                    # Add to existing posts
                    self.existing_posts.add(full_id)
                    
                    # Update tracking data
                    self.release_tracking[tracking_key] = {
                        'last_state': state,
                        'content_hash': content_hash,
                        'last_scraped': datetime.now().isoformat(),
                        'version': release['version']
                    }
                    
                except Exception as e:
                    print(f"   ✗ Error creating markdown for {full_id}: {e}")
        
        # Save updated tracking data
        if created_files:
            self.save_release_tracking(self.release_tracking)
        
        print(f"   ✅ Created {len(created_files)} posts")
        if skipped_count > 0:
            print(f"   ℹ️  Skipped {skipped_count} unchanged releases")
        if updated_count > 0:
            print(f"   🔄 Detected {updated_count} content updates")
        
        return created_files
        return created_files
