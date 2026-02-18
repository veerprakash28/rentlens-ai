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
        "description": text[:300] + "...",
        "contact": "Check Post",
        "availableFrom": None
    }

async def parse_posts_with_gemini(raw_posts: list[dict]) -> list[dict]:
    if not genapi_key or "your_gemini_api_key_here" in genapi_key:
        print("Using Regex Fallback Parser (AI key missing/invalid)")
        return [
            {**extract_with_regex(p['text']), "postUrl": p.get('url')} 
            for p in raw_posts
        ]
    
    results = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for post in raw_posts:
            text = post.get('text', '')
            url = post.get('url')
            
            prompt = f"""
            Extract structured data from the following Facebook post about a flat rental.
            Return strictly valid JSON. Keys: type (e.g. 2BHK), rent (number), location, availableFrom, description, contact.
            If a field is unknown, use null.
            
            Post:
            {text[:2000]} 
            """
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={genapi_key}"
            
            try:
                response = await client.post(api_url, json=payload)
                response.raise_for_status()
                
                resp_json = response.json()
                # Parse response structure
                try:
                    candidates = resp_json.get('candidates', [])
                    if not candidates:
                        raise ValueError("No candidates returned")
                        
                    content_parts = candidates[0].get('content', {}).get('parts', [])
                    raw_text = content_parts[0].get('text', '') if content_parts else "{}"
                    
                    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(cleaned)
                    
                    data['postUrl'] = url
                    
                    # Gender Logic (Hybrid - Regex is reliable for this)
                    gender = "Any"
                    if re.search(r'\b(female|females|girl|girls|lady|ladies|woman|women)\b', text, re.IGNORECASE):
                        gender = "Female"
                    elif re.search(r'\b(male|males|boy|boys|bachelor|bachelors|men|man)\b', text, re.IGNORECASE):
                        gender = "Male"
                    
                    data['genderPreference'] = gender
                    
                    results.append(data)
                except Exception as parse_err:
                     print(f"Error parsing AI response: {parse_err}")
                     results.append({**extract_with_regex(text), "postUrl": url})

            except Exception as e:
                print(f"Error calling Gemini AI: {e}")
                # Fallback
                results.append({**extract_with_regex(text), "postUrl": url})
                continue
            
    return results
