#!/usr/bin/env python3
"""
Adobe Digest Scraper Coordinator
Coordinates multiple scrapers (Adobe HelpX, Sansec, etc.) to fetch security content
"""

import re
import yaml
import requests
from pathlib import Path
from scrapers import AdobeHelpxScraper, SansecScraper, AtomFeedScraper


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
        self.atom_scraper = AtomFeedScraper(self.output_dir, self.existing_posts)
    
    def load_from_tracking_file(self):
        """Load tracked IDs from scraped_posts.json"""
        tracking_file = self.output_dir / 'scraped_posts.json'
        if tracking_file.exists():
            try:
                import json
                with open(tracking_file, 'r') as f:
                    data = json.load(f)
                    ids = set(data.get('ids', []))
                    print(f"📄 Loaded {len(ids)} IDs from tracking file")
                    return ids
            except Exception as e:
                print(f"⚠️  Error loading tracking file: {e}")
        return set()
    
    def load_from_feed(self):
        """Load IDs from published feed.json (limited to recent items)"""
        try:
            response = requests.get(self.feed_url, timeout=10)
            response.raise_for_status()
            feed_data = response.json()
            
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
                    article_id = url.rstrip('/').split('/')[-1]
                    slug_match = re.search(r'sansec-(.+)\.html', url)
                    if slug_match:
                        article_id = slug_match.group(1)
                    if article_id:
                        existing_ids.add(article_id)
            
            print(f"🌐 Loaded {len(existing_ids)} IDs from live feed")
            return existing_ids
        except Exception as e:
            print(f"⚠️  Could not load from feed: {e}")
            return set()
    
    def load_from_local_files(self):
        """Scan local markdown files for existing IDs"""
        existing_ids = set()
        
        # Scan year directories for markdown files
        for year_dir in self.output_dir.glob('[0-9][0-9][0-9][0-9]'):
            for md_file in year_dir.rglob('*.md'):
                try:
                    # Extract ID from filename
                    filename = md_file.stem
                    
                    # Check for APSB ID in filename
                    match = re.search(r'apsb\d{2}-\d{2}', filename, re.IGNORECASE)
                    if match:
                        existing_ids.add(match.group(0).upper())
                    # Check for Sansec slug
                    elif filename.startswith('sansec-'):
                        existing_ids.add(filename)
                    else:
                        # Fallback: use full filename as ID
                        existing_ids.add(filename)
                except Exception as e:
                    continue
        
        print(f"📁 Loaded {len(existing_ids)} IDs from local files")
        return existing_ids
    
    def load_existing_posts(self):
        """Load existing posts from multiple sources (hybrid approach)"""
        print("🔍 Loading existing posts from multiple sources...")
        
        existing_ids = set()
        
        # Source 1: Tracking file (most reliable, full history)
        tracked_ids = self.load_from_tracking_file()
        existing_ids.update(tracked_ids)
        
        # Source 2: Live feed (verification, limited to recent)
        feed_ids = self.load_from_feed()
        existing_ids.update(feed_ids)
        
        # Source 3: Local filesystem (backup)
        local_ids = self.load_from_local_files()
        existing_ids.update(local_ids)
        
        print(f"📊 Total unique IDs: {len(existing_ids)}")
        return existing_ids
    
    def save_tracking_file(self, new_ids):
        """Update tracking file with newly scraped IDs"""
        tracking_file = self.output_dir / 'scraped_posts.json'
        
        # Load existing data
        data = {'ids': [], 'last_updated': None}
        if tracking_file.exists():
            try:
                import json
                with open(tracking_file, 'r') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading existing tracking file: {e}")
        
        # Add new IDs
        current_ids = set(data.get('ids', []))
        current_ids.update(new_ids)
        
        # Save updated data
        import json
        from datetime import datetime
        data = {
            'ids': sorted(list(current_ids)),
            'last_updated': datetime.now().isoformat(),
            'total_count': len(current_ids)
        }
        
        try:
            with open(tracking_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"💾 Updated tracking file: {len(new_ids)} new IDs, {len(current_ids)} total")
        except Exception as e:
            print(f"⚠️  Error saving tracking file: {e}")
    
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
        new_ids = set()
        
        # Process each source
        for source in sources:
            source_type = source.get('type', 'unknown')
            
            try:
                if source_type == 'adobe-helpx':
                    files = self.adobe_scraper.scrape(source)
                    all_files.extend(files)
                    # Extract IDs from created files
                    for file_path in files:
                        filename = Path(file_path).stem
                        match = re.search(r'apsb\d{2}-\d{2}', filename, re.IGNORECASE)
                        if match:
                            new_ids.add(match.group(0).upper())
                elif source_type == 'atom-feed':
                    # Use generic atom scraper if source has 'includes' filter
                    if source.get('includes'):
                        files = self.atom_scraper.scrape(source)
                    else:
                        # Use Sansec scraper for backward compatibility
                        files = self.sansec_scraper.scrape(source)
                    all_files.extend(files)
                    # Extract IDs from created files
                    for file_path in files:
                        filename = Path(file_path).stem
                        new_ids.add(filename)
                else:
                    print(f"⚠️  Unknown source type: {source_type} for {source.get('name', 'unknown')}")
            except Exception as e:
                print(f"✗ Error scraping {source.get('name', 'unknown')}: {e}")
        
        # DON'T update tracking file here - let post_to_microblog.py do it after publishing
        # This prevents marking posts as "already scraped" before they're actually published
        
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
