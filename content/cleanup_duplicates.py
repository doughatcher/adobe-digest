#!/usr/bin/env python3
"""
Cleanup duplicate posts on Micro.blog
Identifies and optionally deletes duplicate posts via Micropub API
"""

import os
import sys
import requests
import json
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DuplicateCleanup:
    def __init__(self):
        self.api_url = os.getenv('MICROBLOG_API_URL', 'https://micro.blog/micropub')
        self.token = os.getenv('MICROBLOG_TOKEN')
        self.feed_url = 'https://adobedigest.com/feed.json'
        
        if not self.token:
            raise ValueError("MICROBLOG_TOKEN not set in environment")
    
    def get_all_posts_from_feed(self):
        """Fetch all posts from the JSON feed (limited to recent items)"""
        try:
            response = requests.get(self.feed_url, timeout=10)
            response.raise_for_status()
            feed_data = response.json()
            
            posts = []
            for item in feed_data.get('items', []):
                posts.append({
                    'url': item.get('url', ''),
                    'title': item.get('title', '').strip(),
                    'date_published': item.get('date_published', ''),
                    'content_text': item.get('content_text', ''),
                })
            
            return posts
        except Exception as e:
            print(f"❌ Error fetching feed: {e}")
            return []
    
    def get_all_posts_from_api(self):
        """Fetch ALL posts from Micro.blog via Micropub source query"""
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
            }
            
            # Micropub query endpoint to get all posts
            params = {
                'q': 'source',
                'limit': 1000  # Get up to 1000 posts
            }
            
            response = requests.get(
                self.api_url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                # Extract posts from response
                items = data.get('items', [])
                for item in items:
                    # Micropub source returns posts with these properties
                    # All values are arrays in Micropub format
                    props = item.get('properties', {})
                    
                    # Extract URL from properties.url array
                    url_array = props.get('url', [])
                    url = url_array[0] if url_array else ''
                    
                    # Extract title from properties.name array
                    name_array = props.get('name', [])
                    title = name_array[0] if name_array else ''
                    
                    # Extract published date from properties.published array
                    published_array = props.get('published', [])
                    pub_date = published_array[0] if published_array else ''
                    
                    posts.append({
                        'url': url,
                        'title': title,
                        'published': pub_date,
                        'date_published': pub_date,  # Add both formats for compatibility
                    })
                
                print(f"✅ Fetched {len(posts)} posts from Micro.blog API")
                return posts
            else:
                print(f"⚠️  API returned status {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching from API: {e}")
            return []
    
    def find_duplicates_by_title(self, posts):
        """Find duplicate posts by title"""
        title_map = defaultdict(list)
        
        for post in posts:
            title = post.get('title', '').strip().lower()
            if title:
                title_map[title].append(post)
        
        # Find titles with multiple posts
        duplicates = {}
        for title, post_list in title_map.items():
            if len(post_list) > 1:
                duplicates[title] = post_list
        
        return duplicates
    
    def delete_post(self, post_url):
        """Delete a post via Micropub API"""
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        data = json.dumps({
            'action': 'delete',
            'url': post_url
        })
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                data=data,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202, 204]:
                return {'success': True, 'status': response.status_code}
            else:
                return {
                    'success': False,
                    'status': response.status_code,
                    'error': response.text
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def run(self, dry_run=True, use_api=False):
        """Find and optionally delete duplicate posts"""
        print("🔍 Micro.blog Duplicate Cleanup")
        print("=" * 60)
        
        if dry_run:
            print("🔹 DRY RUN MODE - No posts will be deleted")
        else:
            print("⚠️  LIVE MODE - Duplicates will be deleted!")
        
        print()
        
        # Get posts
        if use_api:
            print("📡 Fetching posts from Micropub API...")
            posts = self.get_all_posts_from_api()
        else:
            print("📡 Fetching posts from JSON feed...")
            posts = self.get_all_posts_from_feed()
            print(f"⚠️  Note: Feed limited to ~20 recent posts. Use --api for full list.")
        
        if not posts:
            print("❌ No posts found!")
            return
        
        print(f"📊 Total posts: {len(posts)}")
        print()
        
        # Find duplicates
        print("🔍 Scanning for duplicates...")
        duplicates = self.find_duplicates_by_title(posts)
        
        if not duplicates:
            print("✅ No duplicates found!")
            return
        
        print(f"⚠️  Found {len(duplicates)} titles with duplicates:")
        print()
        
        deleted_count = 0
        kept_count = 0
        failed_count = 0
        
        for title, post_list in sorted(duplicates.items()):
            print(f"📝 '{title[:60]}...' ({len(post_list)} copies)")
            
            # Sort to prioritize keeping the best URL:
            # 1. Prefer human-readable slugs over random hex IDs
            # 2. Among similar quality URLs, keep the oldest
            import re
            
            def url_quality_score(post):
                """Score URLs - lower is better (kept first)"""
                url = post.get('url', '')
                
                # Extract the slug from URL
                slug = url.rstrip('/').split('/')[-1].replace('.html', '')
                
                # Check if it's a random hex ID (6 chars, all hex digits)
                is_hex_id = bool(re.match(r'^[0-9a-f]{6}$', slug))
                
                # Priority scoring:
                # 1. Human-readable slugs (contains hyphens and letters) = 0
                # 2. Numeric-only slugs like "000000" = 1
                # 3. Random hex IDs like "23e5ac" = 2
                if is_hex_id and slug not in ['000000']:
                    return 2  # Random hex - delete these
                elif slug == '000000' or slug.isdigit():
                    return 1  # Generic numeric - delete if better option exists
                else:
                    return 0  # Human-readable - keep these
            
            # Sort by URL quality first (best first), then by date (oldest first)
            sorted_posts = sorted(post_list, key=lambda p: (
                url_quality_score(p),
                p.get('date_published', p.get('published', ''))
            ))
            
            # Keep the first one (best quality URL), mark others for deletion
            keep_post = sorted_posts[0]
            delete_posts = sorted_posts[1:]
            
            print(f"   ✅ KEEP: {keep_post['url']}")
            kept_count += 1
            
            for dup_post in delete_posts:
                print(f"   ❌ DELETE: {dup_post['url']}")
                
                if not dry_run:
                    result = self.delete_post(dup_post['url'])
                    if result['success']:
                        print(f"      → Deleted successfully")
                        deleted_count += 1
                    else:
                        print(f"      → Failed to delete: {result.get('error', 'Unknown error')}")
                        failed_count += 1
                else:
                    deleted_count += 1
            
            print()
        
        # Summary
        print("=" * 60)
        if dry_run:
            print(f"📊 Summary (DRY RUN):")
            print(f"   Would keep: {kept_count} posts")
            print(f"   Would delete: {deleted_count} duplicates")
        else:
            print(f"📊 Summary:")
            print(f"   Kept: {kept_count} posts")
            print(f"   Deleted: {deleted_count} duplicates")
            if failed_count:
                print(f"   Failed: {failed_count} deletions")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Find and delete duplicate posts on Micro.blog')
    parser.add_argument('--delete', action='store_true', help='Actually delete duplicates (default is dry-run)')
    parser.add_argument('--api', action='store_true', help='Use Micropub API to fetch all posts (not just feed)')
    parser.add_argument('--help-guide', action='store_true', help='Show detailed cleanup guide')
    
    args = parser.parse_args()
    
    if args.help_guide:
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    MICRO.BLOG DUPLICATE CLEANUP GUIDE                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 OVERVIEW
-----------
This tool helps identify and delete duplicate posts on Micro.blog by comparing
post titles and keeping only the oldest version of each post.

🔍 HOW IT WORKS
---------------
1. Fetches posts from either the JSON feed (limited) or Micropub API (all posts)
2. Groups posts by title to find duplicates
3. For each duplicate group, keeps the oldest post
4. Optionally deletes the newer duplicates via Micropub API

⚠️  IMPORTANT NOTES
-------------------
• Feed method: Only sees ~20 most recent posts
• API method: Can fetch up to 1000 posts (recommended)
• Keeps the OLDEST post (first published) as the canonical version
• Dry-run is default - posts won't be deleted unless you use --delete

📚 USAGE EXAMPLES
-----------------

1. Dry run with feed (safe, shows what would be deleted):
   python3 cleanup_duplicates.py

2. Dry run with full API access:
   python3 cleanup_duplicates.py --api

3. Actually delete duplicates (USE WITH CAUTION):
   python3 cleanup_duplicates.py --api --delete

4. Check feed duplicates and delete:
   python3 cleanup_duplicates.py --delete

🔧 ALTERNATIVE: MANUAL CLEANUP VIA WEB UI
------------------------------------------
If you prefer manual control:
1. Go to https://micro.blog/posts
2. Search for duplicate titles
3. Click into each duplicate post
4. Click "..." menu → "Delete"

💡 RECOMMENDATIONS
------------------
1. First run with --api to see all duplicates
2. Review the list carefully
3. If satisfied, run with --api --delete
4. Verify on https://adobedigest.com/ afterward

⚠️  CANNOT UNDO
---------------
Once deleted via API, posts are gone permanently. Always start with dry-run!

═══════════════════════════════════════════════════════════════════════════════
        """)
        return
    
    cleanup = DuplicateCleanup()
    cleanup.run(dry_run=not args.delete, use_api=args.api)


if __name__ == '__main__':
    main()
