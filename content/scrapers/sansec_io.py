#!/usr/bin/env python3
"""
Sansec.io Research Feed Scraper
Fetches security research articles from sansec.io atom feed
"""

import re
import requests
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from html import unescape


class SansecScraper:
    """Scraper for Sansec.io security research articles"""
    
    def __init__(self, output_dir, existing_posts=None):
        """Initialize scraper"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.existing_posts = existing_posts or set()
        
    def fetch_feed(self, url):
        """Fetch and parse Atom feed"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return ET.fromstring(response.content)
        except Exception as e:
            print(f"   ✗ Error fetching {url}: {e}")
            return None
    
    def extract_articles(self, root):
        """Extract articles from Atom feed"""
        articles = []
        
        # Define namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        total_found = 0
        skipped = 0
        
        # Find all entry elements
        for entry in root.findall('atom:entry', ns):
            total_found += 1
            
            # Extract data
            article = {}
            
            # Get URL
            link = entry.find('atom:link', ns)
            if link is not None:
                article['url'] = link.get('href')
            else:
                continue
            
            # Create ID from URL
            article['id'] = article['url'].split('/')[-1] if article['url'] else f"sansec-{total_found}"
            
            # Skip if already scraped
            if article['id'] in self.existing_posts:
                skipped += 1
                continue
            
            # Get title
            title = entry.find('atom:title', ns)
            article['title'] = title.text if title is not None else 'Untitled'
            
            # Get published date
            updated = entry.find('atom:updated', ns)
            if updated is not None:
                try:
                    # Parse ISO format date
                    article['published_date'] = datetime.fromisoformat(updated.text.replace('Z', '+00:00'))
                except:
                    article['published_date'] = datetime.now()
            else:
                article['published_date'] = datetime.now()
            
            # Get content/summary
            content = entry.find('atom:content', ns)
            if content is not None:
                article['summary'] = unescape(content.text or '')
            else:
                summary = entry.find('atom:summary', ns)
                article['summary'] = unescape(summary.text) if summary is not None else ''
            
            articles.append(article)
        
        if total_found > 0:
            if skipped > 0:
                print(f"   ℹ️  Skipped {skipped} existing articles (already in feed)")
            print(f"   📥 Found {len(articles)} new articles to scrape")
        else:
            print(f"   ℹ️  No articles found")
        
        return articles
    
    def create_markdown(self, data):
        """Create markdown file with Micro.blog front matter"""
        date = data['published_date']
        
        # Create slug from ID
        slug = f"sansec-{data['id']}"
        
        # Create directory structure: YYYY/MM/DD/
        date_dir = self.output_dir / str(date.year) / f"{date.month:02d}" / f"{date.day:02d}"
        date_dir.mkdir(parents=True, exist_ok=True)
        
        filename = date_dir / f"{slug}.md"
        
        # Build Micro.blog compatible front matter
        url_path = f"/{date.year}/{date.month:02d}/{date.day:02d}/{slug}.html"
        
        front_matter = {
            'layout': 'post',
            'title': data['title'],
            'microblog': False,
            'guid': f"http://adobedigest.micro.blog{url_path}",
            'date': date.strftime('%Y-%m-%dT%H:%M:%S-05:00'),
            'type': 'post',
            'url': url_path,
            'categories': ['security-research', 'sansec'],
            'tags': ['sansec', 'ecommerce-security', 'magento', 'malware']
        }
        
        # Build content
        content_parts = []
        
        # Add summary
        if data['summary']:
            content_parts.append(data['summary'])
            content_parts.append('')
        
        # Link to full article
        content_parts.append(f"---\n")
        content_parts.append(f"[**Read Full Article on Sansec.io →**]({data['url']})")
        
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
        Scrape articles from Sansec.io atom feed
        
        Config format:
        {
            'name': 'sansec-research',
            'url': 'https://sansec.io/atom.xml',
            'limit': 50  # Optional: limit number of articles to fetch
        }
        """
        source_name = config.get('name', 'sansec')
        limit = config.get('limit', 50)
        
        print(f"\n🔍 Scraping {source_name}...")
        
        # Fetch the atom feed
        root = self.fetch_feed(config['url'])
        if root is None:
            return []
        
        # Extract articles
        articles = self.extract_articles(root)
        
        # Apply limit
        if limit and len(articles) > limit:
            articles = articles[:limit]
            print(f"   ⚠️  Limited to {limit} most recent articles")
        
        created_files = []
        
        # Process each article
        for article in articles:
            print(f"   Processing {article['id']}...")
            
            # Create markdown
            try:
                filename = self.create_markdown(article)
                created_files.append(filename)
                self.existing_posts.add(article['id'])
            except Exception as e:
                print(f"   ✗ Error creating markdown for {article['id']}: {e}")
        
        return created_files
