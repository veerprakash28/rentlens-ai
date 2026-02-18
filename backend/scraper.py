from playwright.async_api import async_playwright
import asyncio
import json
import os

SCRAPE_CONFIG = {
    "viewport": {"width": 1280, "height": 800},
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

_stop_signal = False

def signal_stop():
    global _stop_signal
    _stop_signal = True

async def scrape_facebook_group(group_url: str, max_posts: int = 10, search_keywords: list[str] = None) -> list[dict]:
    global _stop_signal
    _stop_signal = False  # Reset signal at start
    
    print(f"Starting scraper for: {group_url}")
    
    auth_file = "auth.json"
    
    async with async_playwright() as p:
        # Check login state
        context_args = {
             "user_agent": "Mozilla/50 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if os.path.exists(auth_file):
            context_args["storage_state"] = auth_file
            
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-notifications"]
        )
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        try:
            await page.goto(group_url, wait_until="domcontentloaded")
            
            # Check for login
            if "login" in page.url or await page.get_by_role("button", name="Log In").count() > 0:
                print("Login required or session expired. Please log in manually (30s wait)...")
                await page.wait_for_timeout(30000)
                
                # Save state after manual login attempt
                print("Saving new login session to auth.json...")
                await context.storage_state(path=auth_file)
            else:
                 # If we didn't need to login, ensure we have the latest cookies anyway
                 if not os.path.exists(auth_file):
                      await context.storage_state(path=auth_file)

            print("Scrolling to load posts...")
            posts_data = []
            no_new_content_counts = 0
            
            # Housing keywords to validate real posts (vs comments/ads)
            KEYWORDS = ["flat", "room", "bhk", "rent", "deposit", "available", "looking", "occupied", "female", "male", "bachelor", "family", "pg", "apartment", "house", "broker", "tenant", "leads", "place", "help", "need"]
            
            if search_keywords:
                KEYWORDS.extend([k.lower() for k in search_keywords])
            
            start_time = asyncio.get_event_loop().time()
            TIMEOUT_DURATION = 120 # 2 minutes
            
            while len(posts_data) < max_posts and no_new_content_counts < 3:
                # check cancellation
                if _stop_signal:
                    print("Stop signal received. Halting scraper.")
                    break
                    
                # check timeout
                if asyncio.get_event_loop().time() - start_time > TIMEOUT_DURATION:
                    print(f"Timeout of {TIMEOUT_DURATION}s reached. Stopping scrape.")
                    break
                
                # check timeout
                if asyncio.get_event_loop().time() - start_time > TIMEOUT_DURATION:
                    print(f"Timeout of {TIMEOUT_DURATION}s reached. Stopping scrape.")
                    break
                
                # Diagnostic: Check structure (disabled)
                # feed_count = await page.locator("div[role='feed']").count()
                # main_count = await page.locator("div[role='main']").count()
                
                # Strategy: Look for the post TEXT directly using common attribute
                elements = await page.locator("div[data-ad-preview='message']").all()
                
                if not elements:
                     # Fallback to article if message not found
                     elements = await page.locator("div[role='article']").all()

                for el in elements:
                    if len(posts_data) >= max_posts:
                        break
                    try:
                        text = await el.inner_text() 
                        
                        # Data Cleaning & Validation
                        if not text: 
                            continue
                            
                        if len(text) < 20: 
                            continue

                        # Explicitly skip Comments/Replies
                        if "Reply" in text and "Comment" not in text: 
                             continue
                        
                        # Check for at least one keyword
                        text_lower = text.lower()
                        # Add 'location' to keywords
                        KEYWORDS_EXT = KEYWORDS + ["location", "contact", "details", "call"]
                        if not any(k in text_lower for k in KEYWORDS_EXT):
                            print(f"Ignored (no keywords): {text[:50].replace(chr(10), ' ')}...")
                            continue
                            
                        # Remove interaction noise
                        clean_text = text
                        # Main posts have "Like Comment Share" or just "Like Comment"
                        if "Like" in clean_text and "Comment" in clean_text:
                            clean_text = clean_text.split("Like\nComment")[0].strip()
                            clean_text = clean_text.split("Like  Comment")[0].strip()
                        
                        if len(clean_text) < 20: continue


                        # Try to extract Post URL
                        post_url = None
                        try:
                            # Debug: try to find ANY parent with a link
                            # Go up 6 levels - usually enough to hit the main card wrapper
                            ancestor = el.locator("xpath=./ancestor::div[contains(@class, 'x1yztbdb')] | ./ancestor::div[@role='article'] | ./../../../..")
                            
                            # Just grab the first effective ancestor found
                            if await ancestor.count() > 0:
                                container = ancestor.first
                                
                                all_links = await container.locator("a").all()
                                for link in all_links:
                                    href = await link.get_attribute("href")
                                    
                                    if href and ("/posts/" in href or "/permalink/" in href):
                                         post_url = href
                                         break

                                    if href and "facebook.com/groups/" in href and "/posts/" in href:
                                         post_url = href
                                         break
                                
                            # Clean URL
                            if post_url:
                                if post_url.startswith("/"):
                                    post_url = "https://www.facebook.com" + post_url
                                post_url = post_url.split("?")[0]
                                
                        except Exception as e:
                            pass
                            
                        # Use text as key checks for deduplication
                        if not any(p['text'] == clean_text for p in posts_data):
                            posts_data.append({"text": clean_text, "url": post_url})
                            print(f"Accepted: {clean_text[:50].replace(chr(10), ' ')}...")
                        else:
                            pass # Duplicate

                    except Exception as e:
                        print(f"Error processing element: {e}")
                        continue
                
                # Scroll
                previous_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == previous_height:
                    no_new_content_counts += 1
                else:
                    no_new_content_counts = 0
                
                print(f"Collected {len(posts_data)} unique posts...")
            
            return list(posts_data)
            
        except Exception as e:
            print(f"Error scraping: {e}")
            return []
        finally:
            await browser.close()
