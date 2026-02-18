from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import os
from scraper import scrape_facebook_group, signal_stop
from ai_parser import parse_posts_with_gemini

app = FastAPI()

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

@app.get("/")
def read_root():
    return {"status": "ok", "service": "fb-group-scraper-backend"}
