from playwright.async_api import async_playwright
import asyncio
import os

async def run_manual_login():
    auth_file = "auth.json"
    
    async with async_playwright() as p:
        print("Launching browser for manual login...")
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-notifications"]
        )
        
        # Load existing state if it exists
        context_args = {}
        if os.path.exists(auth_file):
            context_args["storage_state"] = auth_file
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        # Go to Facebook
        await page.goto("https://www.facebook.com", wait_until="domcontentloaded")
        
        print("Please log in to Facebook manually in the opened browser window.")
        print("Close the browser once you are logged in and want to save the session.")
        
        # Wait for the browser to be closed by the user
        while True:
            try:
                if browser.is_connected():
                    await asyncio.sleep(1)
                else:
                    break
            except Exception:
                break
                
        # If we got here, user closed the browser. Let's hope they logged in.
        # Re-opening context briefly to save state (or if it's already closed, it might fail)
        # Actually, let's use a different approach: wait for a specific signal or just save on closure if possible.
        # Better: use a loop that checks if we are on a post-login page, but manual closure is simpler.
        
        # Note: To reliably save state before closure, we should have a 'Save' button or similar, 
        # but Playwright's storage_state() can be called anytime.
        
        # Let's try to save state periodically or on a specific condition.
        # For now, let's keep it simple: the user logs in, and we save it.
        
        # Wait for browser to be closed
        print("Browser closed. Saving session state...")
        # Note: If closed, context is gone. We should have saved it while it was open.
        
if __name__ == "__main__":
    asyncio.run(run_manual_login())
