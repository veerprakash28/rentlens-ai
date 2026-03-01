import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

# Check for API Key
genapi_key = os.getenv("GEMINI_API_KEY")

import re

def extract_with_regex(text: str) -> dict:
    """Fallback parser using regex when AI is unavailable"""
    rent_match = re.search(r'(?:Rs\.?|₹)\s*(\d+(?:,\d+)*)|(\d+(?:,\d+)*)\s*(?:rent|price)', text, re.IGNORECASE)
    rent = None
    if rent_match:
        val = rent_match.group(1) or rent_match.group(2)
        try:
            rent = int(val.replace(',', ''))
        except:
            pass

    flat_type = "Unknown"
    if re.search(r'1\s*BHK', text, re.IGNORECASE): flat_type = "1BHK"
    elif re.search(r'2\s*BHK', text, re.IGNORECASE): flat_type = "2BHK"
    elif re.search(r'3\s*BHK', text, re.IGNORECASE): flat_type = "3BHK"
    elif re.search(r'single', text, re.IGNORECASE): flat_type = "Single Room"
    
    # Try to extract location (near X, at Y)
    location = "See description"
    loc_match = re.search(r'(?:near|at|in)\s+([A-Za-z0-9\s,]+?)(?:\.|,|\n|$)', text, re.IGNORECASE)
    if loc_match:
        # cleanup match
        raw_loc = loc_match.group(1).strip()
        if len(raw_loc) < 30: # Avoid capturing long sentences
            location = raw_loc

    # Try to extract gender preference
    gender = "Any"
    if re.search(r'\b(female|females|girl|girls|lady|ladies|woman|women)\b', text, re.IGNORECASE):
        gender = "Female"
    elif re.search(r'\b(male|males|boy|boys|bachelor|bachelors|men|man)\b', text, re.IGNORECASE):
        gender = "Male"
    
    return {
        "type": flat_type,
        "rent": rent,
        "location": location,
        "genderPreference": gender, 
        "description": text[:300].replace("See more", "").replace("See More", "").strip() + "...",
        "contact": "Check Post",
        "availableFrom": None
    }

async def parse_posts_with_gemini(raw_posts: list[dict]) -> list[dict]:
    if not raw_posts:
        return []
    
    if not genapi_key or "your_gemini_api_key_here" in genapi_key:
        print("Using Regex Fallback Parser (AI key missing/invalid)")
        return [
            {**extract_with_regex(p['text']), "postUrl": p.get('url')} 
            for p in raw_posts
        ]
    
    # Batch ALL posts into a single API call to avoid rate limits
    posts_text = ""
    for i, post in enumerate(raw_posts):
        text = post.get('text', '')[:1500]  # Limit per post
        # Clean "See more" artifacts from Facebook
        text = re.sub(r'\s*See more\s*', ' ', text).strip()
        posts_text += f"\n---POST {i+1}---\n{text}\n"
    
    prompt = f"""Extract structured data from these {len(raw_posts)} Facebook rental posts.
Return a JSON ARRAY with one object per post, in order. Each object must have these keys:
- type (e.g. "1BHK", "2BHK", "3BHK", "Single Room", "PG", or null)
- rent (number or null)
- location (string or null)
- availableFrom (string or null)
- description (1-2 sentence summary of the post)
- contact (phone/name or null)
- genderPreference ("Male", "Female", or "Any")

Return ONLY valid JSON array, no markdown formatting.

Posts:
{posts_text}
"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={genapi_key}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Retry with exponential backoff for rate limits
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = await client.post(api_url, json=payload)
                response.raise_for_status()
                
                resp_json = response.json()
                candidates = resp_json.get('candidates', [])
                if not candidates:
                    raise ValueError("No candidates returned")
                    
                content_parts = candidates[0].get('content', {}).get('parts', [])
                raw_text = content_parts[0].get('text', '[]') if content_parts else '[]'
                
                cleaned = raw_text.replace("```json", "").replace("```", "").strip()
                data_list = json.loads(cleaned)
                
                if not isinstance(data_list, list):
                    data_list = [data_list]
                
                results = []
                for i, data in enumerate(data_list):
                    if i < len(raw_posts):
                        data['postUrl'] = raw_posts[i].get('url')
                    results.append(data)
                
                print(f"AI successfully parsed {len(results)} posts in one batch call")
                return results
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries:
                    wait_time = [5, 15, 30][attempt]
                    print(f"Rate limited (429). Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    import asyncio
                    await asyncio.sleep(wait_time)
                    continue
                print(f"Error calling Gemini AI (batch): {e}")
                break
            except Exception as e:
                print(f"Error calling Gemini AI (batch): {e}")
                break
        
        print("Falling back to regex parser for all posts")
        return [
            {**extract_with_regex(re.sub(r'\s*See more\s*', ' ', p['text']).strip()), "postUrl": p.get('url')} 
            for p in raw_posts
        ]

