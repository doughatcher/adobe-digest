#!/usr/bin/env python3
"""
Generic Atom/RSS Feed Scraper with filtering support
Fetches articles from feeds with optional keyword filtering
"""

import re
import requests
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from html import unescape


class AtomFeedScraper:
    """Generic scraper for Atom/RSS feeds with filtering support"""
    
    def __init__(self, output_dir, existing_posts=None):
        """Initialize scraper"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.existing_posts = existing_posts or set()
        
    def fetch_feed(self, url):
        """Fetch and parse Atom/RSS feed"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return ET.fromstring(response.content)
        except Exception as e:
            print(f"   ✗ Error fetching {url}: {e}")
            return None
    
    def matches_includes(self, text, includes):
        """Check if text contains any of the include keywords (case-insensitive)"""
        if not includes:
            return True  # No filter means include everything
        
        text_lower = text.lower()
        for keyword in includes:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def extract_articles(self, root, includes=None, source_prefix=''):
        """Extract articles from Atom feed with optional keyword filtering"""
        articles = []
        
        # Define namespaces
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'feedburner': 'http://rssnamespace.org/feedburner/ext/1.0'
        }
        
        total_found = 0
        skipped_duplicate = 0
        skipped_filter = 0
        
        # Find all entry elements (Atom) or item elements (RSS)
        entries = root.findall('atom:entry', ns)
        if not entries:
            # Try RSS format
            entries = root.findall('.//item')
        
        for entry in entries:
            total_found += 1
            
            # Extract data
            article = {}
            
            # Get URL (Atom or RSS format)
            link = entry.find('atom:link', ns)
            if link is not None:
                article['url'] = link.get('href')
            else:
                link_elem = entry.find('link')
                article['url'] = link_elem.text if link_elem is not None else None
            
            if not article['url']:
                continue
            
            # Get title
            title = entry.find('atom:title', ns)
            if title is None:
                title = entry.find('title')
            article['title'] = title.text if title is not None else 'Untitled'
            
            # Get content/summary for filtering
            content = entry.find('atom:content', ns)
            if content is None:
                content = entry.find('atom:summary', ns)
            if content is None:
                content = entry.find('description')
            
            content_text = unescape(content.text or '') if content is not None else ''
            article['summary'] = content_text
            
            # Apply includes filter
            if includes:
                combined_text = f"{article['title']} {content_text}"
                if not self.matches_includes(combined_text, includes):
                    skipped_filter += 1
                    continue
            
            # Create ID from URL
            url_slug = article['url'].split('/')[-1].replace('.html', '')
            # Clean up URL parameters
            url_slug = url_slug.split('?')[0].split('#')[0]
            # Add source prefix to avoid collisions
            article['id'] = f"{source_prefix}-{url_slug}" if source_prefix else url_slug
            
            # Check for duplicates
            if article['id'] in self.existing_posts:
                skipped_duplicate += 1
                continue
            
            # Get published date
            date_elem = entry.find('atom:updated', ns) or entry.find('atom:published', ns)
            if date_elem is None:
                date_elem = entry.find('pubDate')
            
            if date_elem is not None:
                try:
                    date_str = date_elem.text
                    # Try ISO format first
                    if 'T' in date_str:
                        article['published_date'] = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        # Try RFC 2822 format (RSS)
                        from email.utils import parsedate_to_datetime
                        article['published_date'] = parsedate_to_datetime(date_str)
                except Exception as e:
                    print(f"   ⚠️  Error parsing date '{date_str}': {e}, using current time")
                    article['published_date'] = datetime.now()
            else:
                print(f"   ⚠️  No date element found for {article.get('title', 'unknown')}, using current time")
                article['published_date'] = datetime.now()
            
            articles.append(article)
        
        if total_found > 0:
            if skipped_duplicate > 0:
                print(f"   ℹ️  Skipped {skipped_duplicate} existing articles")
            if skipped_filter > 0:
                print(f"   ℹ️  Filtered out {skipped_filter} articles (not matching includes)")
            print(f"   📥 Found {len(articles)} new articles to scrape")
        else:
            print(f"   ℹ️  No articles found")
        
        return articles
    
    def create_markdown(self, data):
        """Create markdown file with Micro.blog front matter"""
        date = data['published_date']
        
        # Use the full ID (already includes prefix)
        slug = data['id']
        
        # Create directory structure: YYYY/MM/DD/
        date_dir = self.output_dir / str(date.year) / f"{date.month:02d}" / f"{date.day:02d}"
        date_dir.mkdir(parents=True, exist_ok=True)
        
        filename = date_dir / f"{slug}.md"
        
        # Build Micro.blog compatible front matter
        url_path = f"/{date.year}/{date.month:02d}/{date.day:02d}/{slug}.html"
        
        # Get categories from source config
        source_categories = data.get('source_categories', [])
        source_name = data.get('source_name', 'research')
        
        # Base tags
        base_tags = ['news', 'security-research', source_name]
        
        front_matter = {
            'layout': 'post',
            'title': data['title'],
            'microblog': False,
            'guid': f"http://adobedigest.micro.blog{url_path}",
            'date': date.strftime('%Y-%m-%dT%H:%M:%S-05:00'),
            'type': 'post',
            'url': url_path,
            'categories': ['security-research'] + source_categories,
            'tags': base_tags + source_categories
        }
        
        # Build content
        content_parts = []
        
        # Add summary
        if data['summary']:
            # Truncate summary if too long
            summary = data['summary']
            if len(summary) > 500:
                summary = summary[:497] + '...'
            content_parts.append(summary)
            content_parts.append('')
        
        # Link to full article
        source_display = data.get('source_display_name', 'Source')
        content_parts.append(f"---\n")
        content_parts.append(f"[**Read Full Article on {source_display} →**]({data['url']})")
        
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
        Scrape articles from Atom/RSS feed
        
        Config format:
        {
            'name': 'source-name',
            'url': 'https://example.com/feed.xml',
            'limit': 50,  # Optional: limit number of articles
            'categories': [],  # Optional categories to add
            'includes': ['keyword1', 'keyword2'],  # Optional: only include if title/content contains these
            'display_name': 'Source Name'  # Optional: display name for attribution
        }
        """
        source_name = config.get('name', 'feed')
        limit = config.get('limit', 50)
        source_categories = config.get('categories', [])
        includes = config.get('includes')
        display_name = config.get('display_name', source_name.replace('-', ' ').title())
        
        filter_msg = f" (filtering for: {', '.join(includes)})" if includes else ""
        print(f"\n🔍 Scraping {source_name}{filter_msg}...")
        
        # Fetch the feed
        root = self.fetch_feed(config['url'])
        if root is None:
            return []
        
        # Extract articles with filtering
        articles = self.extract_articles(root, includes=includes, source_prefix=source_name)
        
        # Apply limit
        if limit and len(articles) > limit:
            articles = articles[:limit]
            print(f"   ⚠️  Limited to {limit} most recent articles")
        
        created_files = []
        
        # Process each article
        for article in articles:
            print(f"   Processing {article['title'][:60]}...")
            
            # Add source info to article for markdown generation
            article['source_name'] = source_name
            article['source_categories'] = source_categories
            article['source_display_name'] = display_name
            
            # Create markdown
            try:
                filename = self.create_markdown(article)
                created_files.append(filename)
                self.existing_posts.add(article['id'])
            except Exception as e:
                print(f"   ✗ Error creating markdown for {article['id']}: {e}")
        
        return created_files
