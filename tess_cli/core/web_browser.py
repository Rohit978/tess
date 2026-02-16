import asyncio
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import os
from .logger import setup_logger

logger = setup_logger("WebBrowser")

class WebBrowser:
    """
    Handles Headless Browsing for scraping and screenshots.
    Supports both Sync (CLI) and Async (Telegram) execution.
    """
    def __init__(self):
        self.screenshot_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def scrape_page(self, url):
        """Synchronous scraping for CLI"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=60000)
                content = page.content()
                browser.close()
                
                # Parse with BS4 for clean text
                soup = BeautifulSoup(content, 'html.parser')
                # Kill scripts and styles
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text(separator='\n')
                # Clean whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = '\n'.join(chunk for chunk in chunks if chunk)
                
                return clean_text[:5000] # Limit return size
        except Exception as e:
            logger.error(f"Scrape Sync Error: {e}")
            return f"Error scraping {url}: {e}"

    async def scrape_async(self, url):
        """Async scraping for Telegram"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=60000)
                content = await page.content()
                await browser.close()
                
                soup = BeautifulSoup(content, 'html.parser')
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text(separator='\n')
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = '\n'.join(chunk for chunk in chunks if chunk)
                
                return clean_text[:5000]
        except Exception as e:
            logger.error(f"Scrape Async Error: {e}")
            return f"Error scraping {url}: {e}"

    def screenshot_sync(self, url):
        """Sync Screenshot"""
        try:
            filename = f"screenshot_{os.urandom(4).hex()}.png"
            path = os.path.join(self.screenshot_dir, filename)
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=60000)
                page.screenshot(path=path)
                browser.close()
            return path
        except Exception as e:
            logger.error(f"Screenshot Sync Error: {e}")
            return f"Error: {e}"

    async def screenshot_async(self, url):
        """Async Screenshot"""
        try:
            filename = f"screenshot_{os.urandom(4).hex()}.png"
            path = os.path.join(self.screenshot_dir, filename)
            
            async with async_playwright() as p:
                # Launch Chromium
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=60000)
                await page.screenshot(path=path)
                await browser.close()
            return path
        except Exception as e:
            logger.error(f"Screenshot Async Error: {e}")
            return f"Error: {e}"

    def search_google(self, query, headless=True):
        """
        Performs a Web Search using DuckDuckGo API (via duckduckgo-search).
        Much faster and more reliable than headless browsing.
        """
        try:
            from duckduckgo_search import DDGS
            
            results = []
            with DDGS() as ddgs:
                # Use the new .text method (which is now a standard method, not a generator in newer versions)
                response = ddgs.text(query, max_results=5)
                
                for r in response:
                    title = r.get('title', 'No Title')
                    link = r.get('href', 'N/A')
                    snippet = r.get('body', '')
                    results.append(f"🔹 **{title}**\n{snippet}\n[Link]({link})")
            
        except Exception as e:
            logger.warning(f"DuckDuckGo API failed: {e}. Falling back to Browser Search...")
            results = []
        
        # 🛡️ FALLBACK: Use Playwright to scrape a search engine
        if not results:
            try:
                logger.info(f"🌐 Falling back to Playwright search for: {query}")
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                scrape_res = self.scrape_page(search_url)
                if scrape_res and "Error" not in scrape_res:
                    return f"Search Results (via Browser Fallback):\n\n{scrape_res[:1500]}..."
                else:
                    return "Search failed both via API and Browser Fallback."
            except Exception as fe:
                logger.error(f"Search Fallback Error: {fe}")
                return f"Search failed: {e}"

        return "\n\n".join(results)

    async def search_async(self, query):
        """
        Async Web Search (for Telegram) using DuckDuckGo.
        """
        # DDGS is synchronous but fast. We can wrap it or just run it.
        # For true async, we'd loop. For now, running sync is fine as it's an HTTP call.
        return self.search_google(query)
