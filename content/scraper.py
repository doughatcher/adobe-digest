#!/usr/bin/env python3
"""
Adobe Digest Scraper Coordinator
Coordinates multiple scrapers (Adobe HelpX, Sansec, etc.) to fetch security content
"""

import re
import yaml
import requests
from pathlib import Path
from scrapers import AdobeHelpxScraper, SansecScraper


class ScraperCoordinator:
    def __init__(self, config_file='scraper.yaml', output_dir='.', force=False):
        """Initialize coordinator with config file and output directory"""
        self.config_file = config_file
        # Output directly to content directory (current directory)
        self.output_dir = Path(__file__).parent / output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.feed_url = 'https://adobedigest.com/feed.json'
        self.force = force
        
        # Load existing posts to avoid duplicates (unless force mode)
        if not force:
            self.existing_posts = self.load_existing_posts()
        else:
            self.existing_posts = set()
            print("🔄 Force mode: Will scrape all content")
        
        # Initialize scrapers
        self.adobe_scraper = AdobeHelpxScraper(self.output_dir, self.existing_posts)
        self.sansec_scraper = SansecScraper(self.output_dir, self.existing_posts)
    
    def load_existing_posts(self):
        """Load list of already scraped IDs from published feed.json"""
        try:
            response = requests.get(self.feed_url, timeout=10)
            response.raise_for_status()
            feed_data = response.json()
            
            # Extract IDs from existing feed items
            existing_ids = set()
            for item in feed_data.get('items', []):
                # Extract APSB ID from URL or title (for Adobe bulletins)
                url = item.get('url', '')
                match = re.search(r'apsb\d{2}-\d{2}', url, re.IGNORECASE)
                if match:
                    existing_ids.add(match.group(0).upper())
                else:
                    title = item.get('title', '')
                    match = re.search(r'APSB\d{2}-\d{2}', title)
                    if match:
                        existing_ids.add(match.group(0).upper())
                
                # Extract Sansec article IDs (from URL path)
                if 'sansec.io' in url or 'sansec-' in url:
                    # Get the last part of the URL path
                    article_id = url.rstrip('/').split('/')[-1]
                    # Also try to extract from the slug
                    slug_match = re.search(r'sansec-(.+)\.html', url)
                    if slug_match:
                        article_id = slug_match.group(1)
                    if article_id:
                        existing_ids.add(article_id)
            
            print(f"📊 Found {len(existing_ids)} existing posts in feed")
            return existing_ids
        except Exception as e:
            print(f"⚠️  Could not load existing posts from feed: {e}")
            print(f"   Will scrape all content")
            return set()
    
    def load_config(self):
        """Load sources from scraper.yaml"""
        with open(self.config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('sources', [])
    
    def run(self):
        """Main coordinator execution"""
        print("🚀 Adobe Digest Security Scraper")
        print("=" * 50)
        
        # Load config
        sources = self.load_config()
        print(f"Loaded {len(sources)} sources from config\n")
        
        all_files = []
        
        # Process each source
        for source in sources:
            source_type = source.get('type', 'unknown')
            
            try:
                if source_type == 'adobe-helpx':
                    files = self.adobe_scraper.scrape(source)
                    all_files.extend(files)
                elif source_type == 'atom-feed':
                    files = self.sansec_scraper.scrape(source)
                    all_files.extend(files)
                else:
                    print(f"⚠️  Unknown source type: {source_type} for {source.get('name', 'unknown')}")
            except Exception as e:
                print(f"✗ Error scraping {source.get('name', 'unknown')}: {e}")
        
        print("\n" + "=" * 50)
        print(f"✅ Complete! Created {len(all_files)} new posts")
        
        return all_files


def main():
    import sys
    force = '--force' in sys.argv or '-f' in sys.argv
    coordinator = ScraperCoordinator(force=force)
    coordinator.run()


if __name__ == '__main__':
    main()
