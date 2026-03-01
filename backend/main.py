from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
import os
from scraper import scrape_facebook_group, signal_stop
from ai_parser import parse_posts_with_gemini
from playwright.async_api import async_playwright

app = FastAPI(
    title="RentLens API",
    description="Backend API for the RentLens Facebook Group scraper and AI parser.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Filters(BaseModel):
    minRent: Optional[float] = None
    maxRent: Optional[float] = None
    flatType: Optional[str] = None
    location: Optional[str] = None
    gender: Optional[str] = None

class ScrapeRequest(BaseModel):
    group_url: str
    max_posts: int = 15
    filters: Optional[Filters] = None

class FlatDetails(BaseModel):
    type: Optional[str] = None
    rent: Optional[float] = None
    location: Optional[str] = None
    availableFrom: Optional[str] = None
    description: Optional[str] = None
    contact: Optional[str] = None
    genderPreference: Optional[str] = None # 'Male', 'Female', 'Any'
    postUrl: Optional[str] = None

class ScrapeResponse(BaseModel):
    raw_count: int
    processed_posts: List[FlatDetails]

@app.post("/scrape", response_model=ScrapeResponse)
async def trigger_scrape(request: ScrapeRequest):
    try:
        # 1. Scrape Raw Text
        print(f"Scraping {request.group_url}...")
        
        # Build search keywords from filters
        search_keywords = []
        if request.filters:
            if request.filters.location:
                search_keywords.append(request.filters.location)
            if request.filters.flatType:
                search_keywords.append(request.filters.flatType)
                
        raw_posts = await scrape_facebook_group(request.group_url, request.max_posts, search_keywords)
        
        # Check if scraper returned an error
        if raw_posts and isinstance(raw_posts[0], dict) and raw_posts[0].get('error'):
            return {"raw_count": 0, "processed_posts": raw_posts}
        
        if not raw_posts:
            print("No posts found. The group may be empty, the URL may be wrong, or the session may have expired.")
            return {
                "raw_count": 0,
                "processed_posts": [{
                    "type": None, "rent": None, "location": None,
                    "description": "No posts found. Please check the group URL and try again. If the problem persists, try logging out and logging back in.",
                    "error": "No posts found. The group may require re-authentication. Try logging out and back in."
                }]
            }
        
        # 2. Parse with AI
        print(f"Parsing {len(raw_posts)} posts with AI...")
        structured_data = await parse_posts_with_gemini(raw_posts)
        
        # 3. Apply Filters (Server-Side) if provided
        filtered_data = structured_data
        if request.filters:
            f = request.filters
            filtered_data = []
            for post in structured_data:
                # Rent Filter
                if f.minRent and (not post['rent'] or post['rent'] < f.minRent): continue
                if f.maxRent and (not post['rent'] or post['rent'] > f.maxRent): continue
                
                # Type Filter (Fuzzy)
                if f.flatType and post['type']:
                    if f.flatType.lower() not in post['type'].lower(): continue
                elif f.flatType and not post['type']:
                    continue # Skip if type required but unknown? Or keep? Let's skip strict.

                # Gender Filter
                if f.gender and post['genderPreference']:
                    if post['genderPreference'] != "Any" and post['genderPreference'] != f.gender:
                         continue

                # Location Filter (Search in location or description)
                if f.location:
                    search = f.location.lower()
                    in_loc = post.get('location') and search in post['location'].lower()
                    in_desc = post.get('description') and search in post['description'].lower()
                    if not in_loc and not in_desc:
                        continue
                
                filtered_data.append(post)

        return {
            "raw_count": len(raw_posts),
            "processed_posts": filtered_data
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cancel")
def cancel_scraping():
    try:
        # 1. Signal scraper to stop
        signal_stop()
        
        # 2. Keep session
        # if os.path.exists("auth.json"):
        #     os.remove("auth.json")
            
        return {"status": "cancelled", "message": "Scraping stopped."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/status")
async def get_auth_status():
    auth_file = "auth.json"
    if os.path.exists(auth_file):
        try:
            with open(auth_file, 'r') as f:
                state = json.load(f)
            
            # Try to find user info from metadata file first
            user_info_file = "user_info.json"
            if os.path.exists(user_info_file):
                with open(user_info_file, 'r') as f:
                    info = json.load(f)
                    return {"logged_in": True, "user": info.get("name", "User"), "file": auth_file}

            # Fallback to cookie ID
            user_name = "Facebook User"
            for cookie in state.get("cookies", []):
                if cookie.get("name") == "c_user":
                    user_name = f"User {cookie.get('value')[-4:]}"
                    break
            
            return {"logged_in": True, "user": user_name, "file": auth_file}
        except Exception:
            return {"logged_in": True, "user": "User", "file": auth_file}
    return {"logged_in": False}

@app.post("/auth/login")
async def trigger_login():
    try:
        auth_file = "auth.json"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-notifications"]
            )
            
            context_args = {}
            if os.path.exists(auth_file):
                context_args["storage_state"] = auth_file
                
            context = await browser.new_context(**context_args)
            page = await context.new_page()
            
            await page.goto("https://www.facebook.com", wait_until="domcontentloaded")
            
            print("Login browser opened. Waiting for user to log in...")
            
            while browser.is_connected():
                await asyncio.sleep(3)
                
                # Save state on EVERY iteration so manual close always captures cookies
                try:
                    await context.storage_state(path=auth_file)
                except Exception:
                    # Browser already closed - state was saved on last successful iteration
                    break
                
                # Check if logged in by looking at the current URL and page content
                try:
                    current_url = page.url
                    # Facebook redirects to various logged-in pages
                    is_on_login_page = "/login" in current_url or current_url.rstrip("/") == "https://www.facebook.com"
                    
                    # Check for known logged-in indicators
                    has_account_menu = await page.query_selector('[aria-label="Your profile"], [aria-label="Account"], [aria-label="Account controls and settings"]') is not None
                    has_composer = await page.query_selector('[aria-label="Create a post"], [role="main"]') is not None
                    
                    is_logged_in = has_account_menu or (has_composer and not is_on_login_page)
                    
                    if is_logged_in:
                        print("Login detected! Saving final state and closing browser...")
                        await context.storage_state(path=auth_file)
                        
                        # Extract user's name WITHOUT navigating away (no redirect!)
                        user_name = None
                        try:
                            # Method 1: Facebook homepage sidebar has a link with the user's name
                            # It's typically the first link with the user's profile URL
                            name_el = await page.query_selector('[aria-label="Your profile"]')
                            if name_el:
                                # The nearby text or the link text might have the name
                                parent = await name_el.evaluate_handle('el => el.closest("a") || el.parentElement')
                                if parent:
                                    user_name = await parent.evaluate('el => el.textContent')
                            
                            # Method 2: Look for profile link in the left sidebar
                            if not user_name or user_name.strip() == "":
                                sidebar_links = await page.query_selector_all('a[role="link"]')
                                for link in sidebar_links[:20]:  # Only check first 20 links
                                    href = await link.get_attribute("href") or ""
                                    text = (await link.inner_text()).strip()
                                    # Profile links contain the user's vanity URL and have actual text
                                    if text and len(text) > 1 and len(text) < 40 and "/profile.php" not in href and "login" not in href and href.startswith("https://www.facebook.com/") and "groups" not in href and "pages" not in href and "watch" not in href and "marketplace" not in href and "gaming" not in href:
                                        # This is likely the user's name link
                                        user_name = text
                                        break
                            
                            # Method 3: Use JavaScript to find the c_user and construct the name
                            if not user_name or user_name.strip() == "":
                                user_name = await page.evaluate('''() => {
                                    // Sometimes the user name is in the document title after login
                                    const title = document.title;
                                    if (title && title.includes("|")) {
                                        return title.split("|")[0].trim();
                                    }
                                    return null;
                                }''')
                            
                            if user_name and user_name.strip():
                                user_name = user_name.strip()
                                print(f"User name captured: {user_name}")
                                with open("user_info.json", "w") as f:
                                    json.dump({"name": user_name}, f)
                        except Exception as e:
                            print(f"Could not extract name (non-critical): {e}")
                        
                        # Close immediately — no redirect!
                        try:
                            await browser.close()
                        except Exception:
                            pass
                        break
                except Exception:
                    # Browser was closed by user - that's fine, state was already saved above
                    break
            
            print("Login flow complete. auth.json saved.")
            return {"status": "success", "message": "Login session updated."}
            
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/logout")
async def logout():
    auth_file = "auth.json"
    user_info_file = "user_info.json"
    if os.path.exists(auth_file):
        os.remove(auth_file)
    if os.path.exists(user_info_file):
        os.remove(user_info_file)
    return {"status": "success", "message": "Logged out successfully."}

@app.get("/")
def read_root():
    return {"status": "ok", "service": "fb-group-scraper-backend"}
