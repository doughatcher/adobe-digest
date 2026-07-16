#!/usr/bin/env python3
"""
Micro.blog Email Authentication
Authenticates to Micro.blog via email login flow using Gmail IMAP
"""

import os
import sys
import imaplib
import email
import re
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from html.parser import HTMLParser

# Load environment variables
load_dotenv()


class LinkExtractor(HTMLParser):
    """Extract links from HTML email"""
    def __init__(self):
        super().__init__()
        self.links = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and 'micro.blog' in value and 'signin' in value:
                    self.links.append(value)


class MicroblogAuthenticator:
    def __init__(self):
        self.gmail_email = os.getenv('GMAIL_EMAIL')
        self.gmail_password = os.getenv('GMAIL_APP_PASSWORD')
        self.microblog_email = os.getenv('MICROBLOG_EMAIL')
        self.site_id = os.getenv('MICROBLOG_SITE_ID')
        
        # Validate required environment variables
        if not self.gmail_email:
            raise ValueError("GMAIL_EMAIL not set in environment")
        if not self.gmail_password:
            raise ValueError("GMAIL_APP_PASSWORD not set in environment")
        if not self.microblog_email:
            raise ValueError("MICROBLOG_EMAIL not set in environment")
        if not self.site_id:
            raise ValueError("MICROBLOG_SITE_ID not set in environment")
    
    def request_signin_email(self):
        """Request sign-in email from Micro.blog"""
        print("📧 Requesting sign-in email from Micro.blog...")
        
        url = 'https://micro.blog/account/signin'
        files = {'email': (None, self.microblog_email)}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
            'Referer': 'https://micro.blog/signin',
            'Origin': 'https://micro.blog',
            'Accept': '*/*',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty'
        }
        
        try:
            response = requests.post(url, files=files, headers=headers, timeout=30)
            if response.status_code == 200:
                request_time = datetime.utcnow()
                print(f"✅ Sign-in email requested at {request_time.strftime('%H:%M:%S')} UTC")
                return request_time
            else:
                print(f"❌ Failed to request sign-in email: {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"❌ Error requesting sign-in email: {e}")
            return None
    
    def connect_to_gmail(self, max_attempts=3):
        """Connect to Gmail via IMAP with retry logic"""
        for attempt in range(1, max_attempts + 1):
            try:
                if attempt > 1:
                    print(f"   ⏳ Retrying IMAP connection (attempt {attempt}/{max_attempts})...")
                    time.sleep(5)  # Wait 5 seconds before retry
                mail = imaplib.IMAP4_SSL('imap.gmail.com')
                mail.login(self.gmail_email, self.gmail_password)
                if attempt > 1:
                    print(f"   ✅ IMAP connection succeeded on attempt {attempt}")
                return mail
            except Exception as e:
                print(f"   ⚠️  IMAP connection attempt {attempt}/{max_attempts} failed: {e}")
                if attempt == max_attempts:
                    print(f"❌ Failed to connect to Gmail after {max_attempts} attempts")
                    return None
        return None
    
    def search_for_signin_email(self, mail, request_time, max_retries=60, retry_interval=15):
        """Search for sign-in email with retries
        
        Default timeout: 60 retries × 15s = 15 minutes
        This handles slow Micro.blog email delivery during high load.
        """
        total_timeout_mins = (max_retries * retry_interval) // 60
        print(f"🔍 Polling Gmail IMAP (up to {max_retries} retries, {retry_interval}s apart, ~{total_timeout_mins} min timeout)...")
        
        # Search emails from 10 minutes before request (in case of clock skew)
        search_start = request_time - timedelta(minutes=10)
        
        for attempt in range(1, max_retries + 1):
            try:
                # Wait before checking (except first attempt)
                if attempt > 1:
                    print(f"   ⏳ Waiting {retry_interval}s before retry {attempt}/{max_retries}...")
                    time.sleep(retry_interval)
                else:
                    # Small delay on first attempt to give email time to arrive
                    time.sleep(5)
                
                # Select inbox
                mail.select('INBOX')
                
                # Search for emails from help@micro.blog with sign-in subject
                # Don't use SINCE filter as it can be unreliable with timezones
                search_criteria = '(FROM "help@micro.blog" SUBJECT "sign-in")'
                result, data = mail.search(None, search_criteria)
                
                if result != 'OK':
                    print(f"   ⚠️  Search failed: {result}")
                    continue
                
                email_ids = data[0].split()
                
                if not email_ids:
                    print(f"   ℹ️  Attempt {attempt}/{max_retries}: No emails found yet")
                    continue
                
                # Get last 50 emails (most recent first) to handle busy inboxes
                email_ids = email_ids[-50:][::-1]
                
                print(f"   📬 Found {len(email_ids)} sign-in emails, checking recent ones...")
                
                # Check each email for sign-in link
                for email_id in email_ids:
                    result, msg_data = mail.fetch(email_id, '(RFC822)')
                    if result != 'OK':
                        continue
                    
                    email_body = msg_data[0][1]
                    message = email.message_from_bytes(email_body)
                    
                    # Check email date to ensure it's recent (after our request)
                    email_date_str = message.get('Date', '')
                    try:
                        email_date = email.utils.parsedate_to_datetime(email_date_str)
                        # Make sure email is after our request (with 1 min buffer)
                        if email_date < search_start:
                            continue
                    except Exception as e:
                        # If date parsing fails, skip date check and process the email
                        pass
                    
                    subject = message.get('Subject', '')
                    print(f"   ✅ Found recent sign-in email: {subject}")
                    
                    # Extract HTML content
                    html_content = None
                    if message.is_multipart():
                        for part in message.walk():
                            if part.get_content_type() == 'text/html':
                                html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                    else:
                        if message.get_content_type() == 'text/html':
                            html_content = message.get_payload(decode=True).decode('utf-8', errors='ignore')
                    
                    if html_content:
                        # Extract magic link using regex (more reliable than HTML parser for quoted-printable)
                        import re
                        # Look for the signin URL with auth parameter (handle quoted-printable =3D)
                        match = re.search(r'https://micro\.blog/account/signin\?auth=3D([A-F0-9]+)', html_content)
                        if match:
                            # Decode the quoted-printable =3D to =
                            magic_link = f"https://micro.blog/account/signin?auth={match.group(1)}"
                            print(f"   🔗 Extracted magic link")
                            return magic_link
                        
                        # Fallback: try HTML parser
                        parser = LinkExtractor()
                        parser.feed(html_content)
                        
                        for link in parser.links:
                            if 'auth=' in link and 'signin' in link:
                                print(f"   🔗 Extracted magic link (via parser)")
                                return link
                
                print(f"   ℹ️  Attempt {attempt}/{max_retries}: Sign-in email not found in recent messages")
                
            except Exception as e:
                print(f"   ⚠️  Error during attempt {attempt}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"❌ Failed to find sign-in email after {max_retries} attempts")
        return None
    
    def follow_magic_link(self, magic_link):
        """Follow magic link and capture session cookie"""
        print("🔐 Following magic link to authenticate...")
        
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://micro.blog/signin'
        }
        
        try:
            # Follow the magic link - it will redirect and set the session cookie
            response = session.get(magic_link, headers=headers, allow_redirects=True, timeout=30)
            
            # Debug: Print all cookies received
            print(f"   📊 Received {len(session.cookies)} cookies:")
            for cookie in session.cookies:
                print(f"      - {cookie.name}: {cookie.value[:20]}...")
            
            if response.status_code == 200:
                # Extract rack.session cookie
                for cookie in session.cookies:
                    if cookie.name == 'rack.session':
                        print(f"✅ Session cookie captured")
                        return cookie.value
                
                # Debug: Print response details
                print("⚠️  No rack.session cookie found in response")
                print(f"   Status: {response.status_code}")
                print(f"   Final URL: {response.url}")
                print(f"   Headers: {dict(response.headers)}")
                return None
            else:
                print(f"❌ Failed to follow magic link: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error following magic link: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def switch_active_blog(self, session_cookie):
        """Switch to the target blog as the active site"""
        print(f"🔄 Switching to blog (site ID: {self.site_id})...")
        
        url = 'https://micro.blog/account/sites/make_default'
        data = f'id={self.site_id}'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cookie': f'rack.session={session_cookie}',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        try:
            response = requests.post(url, data=data, headers=headers, timeout=30)
            
            if response.status_code in [200, 204]:
                print(f"✅ Successfully switched to site {self.site_id}")
                return True
            else:
                print(f"⚠️  Site switch returned status {response.status_code}")
                # Non-fatal - cookie might still work
                return True
                
        except Exception as e:
            print(f"⚠️  Error switching site: {e}")
            # Non-fatal - cookie might still work
            return True
    
    def authenticate(self, output_file=None, max_attempts=3):
        """Complete authentication flow.

        Micro.blog sign-in links are single-use and the magic-link step
        occasionally comes back without a rack.session cookie (stale/consumed
        link or a transient server response). Rather than fail the whole deploy
        — which previously required a manual workflow re-run — retry the full
        request→email→follow sequence with a *fresh* link each time.
        """
        print("🚀 Micro.blog Email Authentication")
        print("=" * 60)

        session_cookie = None
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                print(f"\n🔁 Auth attempt {attempt}/{max_attempts} — requesting a fresh sign-in email...")
                time.sleep(8)

            # Step 1: Request sign-in email
            request_time = self.request_signin_email()
            if not request_time:
                continue

            # Step 2: Connect to Gmail
            mail = self.connect_to_gmail()
            if not mail:
                continue

            # Step 3: Search for sign-in email (shorter per-attempt window so a
            # flake retries the whole flow instead of blocking for 15 min)
            magic_link = self.search_for_signin_email(mail, request_time, max_retries=20, retry_interval=15)

            # Close IMAP connection
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

            if not magic_link:
                continue

            # Step 4: Follow magic link and get cookie
            session_cookie = self.follow_magic_link(magic_link)
            if session_cookie:
                break
            print(f"   ⚠️  Attempt {attempt}/{max_attempts} yielded no session cookie; retrying with a fresh link.")

        if not session_cookie:
            print(f"❌ Authentication failed after {max_attempts} attempts")
            return None

        # Step 5: Switch to target blog
        self.switch_active_blog(session_cookie)

        # Step 6: Save cookie if output file specified
        if output_file:
            try:
                output_path = Path(output_file)
                output_path.write_text(session_cookie)
                print(f"💾 Session cookie saved to {output_file}")
            except Exception as e:
                print(f"⚠️  Could not save cookie to file: {e}")
        
        print("=" * 60)
        print("✅ Authentication successful!")
        
        return session_cookie


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Authenticate to Micro.blog via email login')
    parser.add_argument('--output', '-o', help='Output file for session cookie (default: .session-cookie)', 
                       default='.session-cookie')
    parser.add_argument('--stdout', action='store_true', help='Output cookie to stdout instead of file')
    
    args = parser.parse_args()
    
    try:
        authenticator = MicroblogAuthenticator()
        
        output_file = None if args.stdout else args.output
        cookie = authenticator.authenticate(output_file=output_file)
        
        if cookie:
            if args.stdout:
                print(cookie)
            sys.exit(0)
        else:
            print("\n❌ Authentication failed")
            sys.exit(1)
            
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nRequired environment variables:")
        print("  - GMAIL_EMAIL")
        print("  - GMAIL_APP_PASSWORD")
        print("  - MICROBLOG_EMAIL")
        print("  - MICROBLOG_SITE_ID")
        print("\nSee .env.example for details")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
