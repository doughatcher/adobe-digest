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
        self.feed_url = 'https://adobedigest.com/feed.json'
        
        if not self.token:
            raise ValueError("MICROBLOG_TOKEN not set in environment")
    
    def get_existing_posts(self):
        """Fetch existing posts from published feed"""
        try:
            response = requests.get(self.feed_url, timeout=10)
            response.raise_for_status()
            feed_data = response.json()
            
            # Extract bulletin IDs
            existing_ids = set()
            for item in feed_data.get('items', []):
                import re
                # Try to extract from URL first
                url = item.get('url', '')
                match = re.search(r'apsb\d{2}-\d{2}', url, re.IGNORECASE)
                if match:
                    existing_ids.add(match.group(0).upper())
                else:
                    # Try to extract from title if not in URL
                    title = item.get('title', '')
                    match = re.search(r'APSB\d{2}-\d{2}', title)
                    if match:
                        existing_ids.add(match.group(0).upper())
            
            print(f"📊 Found {len(existing_ids)} existing posts in feed")
            return existing_ids
        except Exception as e:
            print(f"⚠️  Could not load existing posts: {e}")
            return set()
    
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
                                
                                # Extract APSB ID from title
                                bulletin_id = None
                                if title_match:
                                    title = title_match.group(1).strip()
                                    id_match = re.search(r'APSB\d{2}-\d{2}', title)
                                    if id_match:
                                        bulletin_id = id_match.group(0)
                                
                                if bulletin_id:
                                    posts.append({
                                        'id': bulletin_id,
                                        'title': title if title_match else '',
                                        'date': date_match.group(1).strip() if date_match else '',
                                        'content': body,
                                        'file': str(md_file)
                                    })
                except Exception as e:
                    print(f"⚠️  Error reading {md_file}: {e}")
        
        # Sort by date (newest first)
        posts.sort(key=lambda x: x['date'], reverse=True)
        return posts
    
    def post_to_microblog(self, title, content, published_date=None):
        """Post content to Micro.blog using Micropub API"""
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Prepare post data
        data = {
            'h': 'entry',
            'name': title,
            'content': content
        }
        
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
            
            if response.status_code in [200, 201, 202]:
                # Extract URL from response
                location = response.headers.get('Location', '')
                result = {
                    'success': True,
                    'url': location,
                    'status': response.status_code
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
    
    def run(self, limit=5):
        """Post new bulletins to Micro.blog"""
        print("🚀 Micro.blog Poster")
        print("=" * 50)
        
        # Get existing and local posts
        existing_ids = self.get_existing_posts()
        local_posts = self.get_local_posts()
        
        print(f"📊 Found {len(local_posts)} local posts")
        print(f"📊 Found {len(existing_ids)} existing posts in feed")
        
        # Find new posts
        new_posts = [p for p in local_posts if p['id'] not in existing_ids]
        
        if not new_posts:
            print("\n✅ No new posts to publish")
            return
        
        print(f"\n📝 Found {len(new_posts)} new posts to publish")
        
        # Limit posts to publish
        posts_to_publish = new_posts[:limit]
        
        if len(new_posts) > limit:
            print(f"⚠️  Limiting to {limit} posts per run")
        
        # Publish each post
        successful = 0
        failed = 0
        
        for post in posts_to_publish:
            print(f"\n📤 Publishing {post['id']}...")
            print(f"   Title: {post['title']}")
            
            result = self.post_to_microblog(
                title=post['title'],
                content=post['content'],
                published_date=post['date']
            )
            
            if result['success']:
                print(f"   ✅ Published successfully!")
                if result.get('url'):
                    print(f"   🔗 {result['url']}")
                successful += 1
            else:
                print(f"   ❌ Failed to publish")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                failed += 1
        
        print("\n" + "=" * 50)
        print(f"✅ Published {successful} posts")
        if failed:
            print(f"❌ Failed {failed} posts")


def main():
    # Get limit from command line args
    limit = 5
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Invalid limit: {sys.argv[1]}, using default of 5")
    
    poster = MicroblogPoster()
    poster.run(limit=limit)


if __name__ == '__main__':
    main()
