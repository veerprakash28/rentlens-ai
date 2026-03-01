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
            print(f"Loading session from {auth_file}...")
            context_args["storage_state"] = auth_file
            
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-notifications", "--no-sandbox"]
        )
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        try:
            print(f"Navigating to {group_url}...")
            await page.goto(group_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for content to load after DOM is ready
            await page.wait_for_timeout(3000)

            # Detect login wall or "Log In" button
            is_login_page = "login" in page.url or await page.get_by_role("button", name="Log in", exact=False).count() > 0
            is_login_wall = await page.get_by_text("You must log in to continue").count() > 0
            
            if is_login_page or is_login_wall:
                print("SESSION EXPIRED or LOGIN REQUIRED. Please use the 'Login' button in the dashboard first.")
                # We won't block here anymore, we'll return an error so the UI can show the login gate
                return [{"error": "Authentication required. Please log in to Facebook first."}]

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

                
                # Diagnostic: Check structure (disabled)
                # feed_count = await page.locator("div[role='feed']").count()
                # main_count = await page.locator("div[role='main']").count()
                
                # Click all "See more" buttons to expand truncated posts
                try:
                    see_more_buttons = await page.locator("div[role='button']:has-text('See more'), span[role='button']:has-text('See more')").all()
                    for btn in see_more_buttons[:10]:  # Limit to avoid slow loops
                        try:
                            await btn.click(timeout=500)
                        except:
                            pass
                    if see_more_buttons:
                        await page.wait_for_timeout(500)
                except:
                    pass
                
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
                        
                        # Remove "See more" artifacts
                        clean_text = clean_text.replace("See more", "").replace("See More", "").strip()
                        
                        if len(clean_text) < 20: continue


                        # Try to extract Post URL using JavaScript (most reliable)
                        post_url = None
                        try:
                            post_url = await el.evaluate('''(el) => {
                                // Walk up the DOM to find the post container
                                let node = el;
                                for (let i = 0; i < 15; i++) {
                                    if (!node.parentElement) break;
                                    node = node.parentElement;
                                    // Check if this is an article or has role="article"
                                    if (node.getAttribute && node.getAttribute('role') === 'article') break;
                                }
                                
                                // Search for post links within this container
                                const links = node.querySelectorAll('a[href]');
                                let bestUrl = null;
                                for (const link of links) {
                                    const href = link.getAttribute('href') || '';
                                    // Direct post/permalink links (best match)
                                    if (href.includes('/posts/') || href.includes('/permalink/')) {
                                        return href;
                                    }
                                    // Group links with numeric post IDs
                                    if (href.includes('/groups/') && href.match(/\\/\\d{10,}\\/?/)) {
                                        bestUrl = href;
                                    }
                                }
                                return bestUrl;
                            }''')
                            
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
