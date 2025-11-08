#!/usr/bin/env python3
"""
Post new bulletins to Micro.blog via Micropub API
"""

import os
import sys
import requests
import json
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MicroblogPoster:
    def __init__(self):
        self.api_url = os.getenv('MICROBLOG_API_URL', 'https://micro.blog/micropub')
        self.token = os.getenv('MICROBLOG_TOKEN')
        self.mp_destination = os.getenv('MICROBLOG_MP_DESTINATION')
        self.feed_url = 'https://adobedigest.com/feed.json'
        
        if not self.token:
            raise ValueError("MICROBLOG_TOKEN not set in environment")
        
        if self.mp_destination:
            print(f"📍 Posting to: {self.mp_destination}")
    
    def get_existing_posts(self):
        """Fetch existing posts from published feed AND tracking file"""
        existing_ids = set()
        existing_titles = set()
        
        # First, load from tracking file (most comprehensive)
        tracking_file = Path(__file__).parent / 'scraped_posts.json'
        if tracking_file.exists():
            try:
                with open(tracking_file, 'r') as f:
                    tracking_data = json.load(f)
                    tracked_ids = tracking_data.get('ids', [])
                    existing_ids.update(tracked_ids)
                    print(f"📊 Loaded {len(tracked_ids)} IDs from tracking file")
            except Exception as e:
                print(f"⚠️  Could not load tracking file: {e}")
        
        # Then, also check the feed for titles (for title-based deduplication)
        try:
            response = requests.get(self.feed_url, timeout=10)
            response.raise_for_status()
            feed_data = response.json()
            
            for item in feed_data.get('items', []):
                import re
                url = item.get('url', '')
                title = item.get('title', '').strip()
                
                # Store title for deduplication
                if title:
                    existing_titles.add(title.lower())
                
                # Try to extract APSB ID from URL first
                match = re.search(r'apsb\d{2}-\d{2}', url, re.IGNORECASE)
                if match:
                    existing_ids.add(match.group(0).upper())
                else:
                    # Try to extract from title
                    match = re.search(r'APSB\d{2}-\d{2}', title)
                    if match:
                        existing_ids.add(match.group(0).upper())
                    else:
                        # Extract slug from URL for non-APSB posts (e.g., Sansec)
                        # URL format: https://adobedigest.com/2025/10/22/sansec-sessionreaper-exploitation.html
                        slug_match = re.search(r'/([^/]+)\.html$', url)
                        if slug_match:
                            slug = slug_match.group(1)
                            # Ignore generic Micro.blog generated slugs like "000000", "13cd3c", etc.
                            if slug not in ['000000'] and not re.match(r'^[0-9a-f]{6}$', slug):
                                existing_ids.add(slug)
            
            print(f"📊 Found {len(existing_titles)} titles in feed")
        except Exception as e:
            print(f"⚠️  Could not load feed: {e}")
        
        print(f"📊 Total {len(existing_ids)} existing post IDs")
        # Store titles for later use
        self._existing_titles = existing_titles
        return existing_ids
    
    def get_local_posts(self):
        """Get all local markdown posts"""
        posts = []
        content_dir = Path(__file__).parent
        
        # Look in year directories (2023, 2024, 2025, etc.)
        for year_dir in sorted(content_dir.glob('[0-9][0-9][0-9][0-9]'), reverse=True):
            for md_file in year_dir.rglob('*.md'):
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Parse front matter
                        if content.startswith('---\n'):
                            parts = content.split('---\n', 2)
                            if len(parts) >= 3:
                                front_matter = parts[1]
                                body = parts[2].strip()
                                
                                # Extract fields from front matter
                                import re
                                title_match = re.search(r'^title:\s*["\']?(.+?)["\']?$', front_matter, re.MULTILINE)
                                date_match = re.search(r'^date:\s*(.+)$', front_matter, re.MULTILINE)
                                
                                # Extract categories and tags (YAML list format)
                                categories = []
                                tags = []
                                in_categories = False
                                in_tags = False
                                
                                for line in front_matter.split('\n'):
                                    if line.startswith('categories:'):
                                        in_categories = True
                                        in_tags = False
                                        continue
                                    elif line.startswith('tags:'):
                                        in_tags = True
                                        in_categories = False
                                        continue
                                    
                                    if in_categories:
                                        if line.startswith('  - '):
                                            categories.append(line.strip('  - ').strip())
                                        elif line and not line.startswith(' '):
                                            in_categories = False
                                    elif in_tags:
                                        if line.startswith('  - '):
                                            tags.append(line.strip('  - ').strip())
                                        elif line and not line.startswith(' '):
                                            in_tags = False
                                
                                # Extract post ID - either APSB ID or filename-based ID
                                post_id = None
                                if title_match:
                                    title = title_match.group(1).strip()
                                    # Try to extract APSB ID from title
                                    id_match = re.search(r'APSB\d{2}-\d{2}', title)
                                    if id_match:
                                        post_id = id_match.group(0)
                                
                                # If no APSB ID, use filename as ID (for Sansec and other posts)
                                if not post_id:
                                    post_id = md_file.stem  # e.g., "sansec-sessionreaper-exploitation"
                                
                                if post_id and title_match and date_match:
                                    # Use tags as categories for Micropub (Micro.blog uses categories as tags)
                                    all_categories = tags if tags else categories
                                    
                                    posts.append({
                                        'id': post_id,
                                        'title': title if title_match else '',
                                        'date': date_match.group(1).strip() if date_match else '',
                                        'content': body,
                                        'categories': all_categories,
                                        'file': str(md_file)
                                    })
                except Exception as e:
                    print(f"⚠️  Error reading {md_file}: {e}")
        
        # Sort by date (newest first)
        posts.sort(key=lambda x: x['date'], reverse=True)
        return posts
    
    def get_post_url_from_feed(self, post_id):
        """Get the URL of an existing post from the feed"""
        try:
            response = requests.get(self.feed_url, timeout=10)
            response.raise_for_status()
            feed_data = response.json()
            
            for item in feed_data.get('items', []):
                import re
                url = item.get('url', '')
                
                # Check if post_id is in the URL (works for both APSB IDs and slugs)
                if re.search(re.escape(post_id.lower()), url.lower()):
                    # Convert micro.blog subdomain to custom domain for API compatibility
                    if 'adobedigest.micro.blog' in url:
                        url = url.replace('adobedigest.micro.blog', 'adobedigest.com')
                    return url
                
                # Also check title for APSB IDs
                title = item.get('title', '')
                if re.search(re.escape(post_id), title, re.IGNORECASE):
                    if 'adobedigest.micro.blog' in url:
                        url = url.replace('adobedigest.micro.blog', 'adobedigest.com')
                    return url
            return None
        except Exception as e:
            print(f"⚠️  Could not get post URL: {e}")
            return None
    
    def post_to_microblog(self, title, content, published_date=None, update_url=None, categories=None):
        """Post or update content on Micro.blog using Micropub API"""
        
        if update_url:
            # Update existing post - use JSON format for Micropub updates
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            replace_data = {
                'name': [title],
                'content': [content]
            }
            
            # Add categories if provided
            if categories:
                replace_data['category'] = categories
            
            update_request = {
                'action': 'update',
                'url': update_url,
                'replace': replace_data
            }
            
            # Add mp-destination if configured for multi-blog accounts
            if self.mp_destination:
                update_request['mp-destination'] = self.mp_destination
            
            data = json.dumps(update_request)
            
            encoded_data = data
        else:
            # Create new post - use form encoding
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'h': 'entry',
                'name': title,
                'content': content
            }
            
            # Add mp-destination if configured for multi-blog accounts
            if self.mp_destination:
                data['mp-destination'] = self.mp_destination
            
            # Add categories if provided
            if categories:
                for i, category in enumerate(categories):
                    data[f'category[{i}]'] = category
            
            # Add published date if provided
            if published_date:
                data['published'] = published_date
            
            # Encode data
            encoded_data = urlencode(data)
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                data=encoded_data,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202, 204]:
                # Extract URL from response
                location = response.headers.get('Location', update_url or '')
                result = {
                    'success': True,
                    'url': location,
                    'status': response.status_code,
                    'updated': bool(update_url)
                }
                
                # Try to get JSON response with preview URL
                try:
                    json_response = response.json()
                    result['json'] = json_response
                except:
                    pass
                
                return result
            else:
                return {
                    'success': False,
                    'status': response.status_code,
                    'error': response.text
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_to_tracking_file(self, post_ids):
        """Save successfully posted IDs to tracking file"""
        tracking_file = Path(__file__).parent / 'scraped_posts.json'
        
        # Load existing data
        data = {'ids': [], 'last_updated': None}
        if tracking_file.exists():
            try:
                with open(tracking_file, 'r') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading tracking file: {e}")
        
        # Add new IDs
        current_ids = set(data.get('ids', []))
        original_count = len(current_ids)
        current_ids.update(post_ids)
        
        # Save updated data
        data = {
            'ids': sorted(list(current_ids)),
            'last_updated': datetime.now().isoformat(),
            'total_count': len(current_ids)
        }
        
        try:
            with open(tracking_file, 'w') as f:
                json.dump(data, f, indent=2)
            new_count = len(current_ids) - original_count
            print(f"💾 Updated tracking file: {new_count} new IDs added, {len(current_ids)} total")
        except Exception as e:
            print(f"⚠️  Error saving tracking file: {e}")
    
    def run(self, limit=5, update_mode=False):
        """Post new bulletins to Micro.blog or update existing ones"""
        print("🚀 Micro.blog Poster")
        print("=" * 50)
        
        # Get existing and local posts
        existing_ids = self.get_existing_posts()
        local_posts = self.get_local_posts()
        
        print(f"📊 Found {len(local_posts)} local posts")
        print(f"📊 Found {len(existing_ids)} existing posts in feed")
        
        if update_mode:
            # Update mode: update existing posts
            posts_to_process = [p for p in local_posts if p['id'] in existing_ids]
            mode_name = "update"
            print(f"\n♻️  Update mode: Will update {len(posts_to_process)} existing posts")
        else:
            # Create mode: only post new ones - check both ID and title
            posts_to_process = []
            for p in local_posts:
                if p['id'] not in existing_ids:
                    # Also check if title already exists (for when slugs don't match)
                    if p['title'].lower() not in self._existing_titles:
                        posts_to_process.append(p)
                    else:
                        print(f"⏭️  Skipping duplicate by title: {p['title'][:60]}")
            
            mode_name = "publish"
            print(f"\n📝 Found {len(posts_to_process)} new posts to publish")
        
        if not posts_to_process:
            if update_mode:
                print("\n✅ No existing posts to update")
            else:
                print("\n✅ No new posts to publish")
            return
        
        # Limit posts to process
        posts_to_process = posts_to_process[:limit]
        
        if len(posts_to_process) > limit:
            print(f"⚠️  Limiting to {limit} posts per run")
        
        # Process each post
        successful = 0
        failed = 0
        posted_ids = []
        
        for post in posts_to_process:
            if update_mode:
                print(f"\n♻️  Updating {post['id']}...")
                print(f"   Title: {post['title']}")
                
                # Get existing post URL
                post_url = self.get_post_url_from_feed(post['id'])
                if not post_url:
                    print(f"   ⚠️  Could not find URL for {post['id']}, skipping")
                    continue
                
                result = self.post_to_microblog(
                    title=post['title'],
                    content=post['content'],
                    update_url=post_url,
                    categories=post.get('categories', [])
                )
            else:
                print(f"\n📤 Publishing {post['id']}...")
                print(f"   Title: {post['title']}")
                
                result = self.post_to_microblog(
                    title=post['title'],
                    content=post['content'],
                    published_date=post['date'],
                    categories=post.get('categories', [])
                )
            
            if result['success']:
                if result.get('updated'):
                    print(f"   ✅ Updated successfully!")
                else:
                    print(f"   ✅ Published successfully!")
                if result.get('url'):
                    print(f"   🔗 {result['url']}")
                successful += 1
                posted_ids.append(post['id'])  # Track successful posts
            else:
                print(f"   ❌ Failed to {mode_name}")
                error_msg = result.get('error', 'Unknown error')
                status = result.get('status', 'unknown')
                print(f"   Error: {error_msg}")
                print(f"   Status: {status}")
                failed += 1
        
        # Save successfully posted IDs to tracking file
        if posted_ids:
            self.save_to_tracking_file(posted_ids)
        
        print("\n" + "=" * 50)
        if update_mode:
            print(f"✅ Updated {successful} posts")
        else:
            print(f"✅ Published {successful} posts")
        if failed:
            print(f"❌ Failed {failed} posts")


def main():
    # Parse command line args
    limit = 5
    update_mode = False
    
    for arg in sys.argv[1:]:
        if arg in ['--update', '-u']:
            update_mode = True
        elif arg in ['--help', '-h']:
            print("Usage: post_to_microblog.py [LIMIT] [--update]")
            print("\nArguments:")
            print("  LIMIT      Maximum number of posts to process (default: 5)")
            print("  --update   Update existing posts instead of creating new ones")
            print("\nExamples:")
            print("  python3 post_to_microblog.py 10          # Post up to 10 new bulletins")
            print("  python3 post_to_microblog.py --update    # Update up to 5 existing posts")
            print("  python3 post_to_microblog.py 10 --update # Update up to 10 existing posts")
            sys.exit(0)
        else:
            try:
                limit = int(arg)
            except ValueError:
                print(f"Invalid argument: {arg}")
                print("Use --help for usage information")
                sys.exit(1)
    
    poster = MicroblogPoster()
    poster.run(limit=limit, update_mode=update_mode)


if __name__ == '__main__':
    main()
