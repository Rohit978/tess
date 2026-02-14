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

    def scrape_sync(self, url):
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

    def search_sync(self, query, headless=True):
        """
        Performs a DuckDuckGo Search (HTML version) to avoid CAPTCHAs.
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                page = browser.new_page()
                
                # Use DuckDuckGo HTML (faster, no ads, easier to scrape)
                page.goto("https://html.duckduckgo.com/html/", timeout=60000)
                
                # Type Query
                page.fill('input[name="q"]', query)
                page.keyboard.press("Enter")
                
                # Wait for results
                try:
                    page.wait_for_selector(".result", timeout=15000)
                except:
                    return "No results found or connection timeout."
                
                results = []
                # DDG HTML Result Structure
                result_divs = page.locator('.result').all()
                
                for div in result_divs[:5]: # Top 5
                    try:
                        title_el = div.locator(".result__title").first
                        link_el = div.locator(".result__url").first
                        snippet_el = div.locator(".result__snippet").first
                        
                        if title_el.count() > 0:
                            title = title_el.inner_text().strip()
                            # DDG HTML links are often relative or redirects, but usually the text is usable
                            # Actually result__url in HTML version is the display URL, the real link is in 'a.result__a'
                            link_a = div.locator("a.result__a").first
                            link = link_a.get_attribute("href") if link_a.count() > 0 else "N/A"
                            
                            snippet = snippet_el.inner_text().strip() if snippet_el.count() > 0 else ""
                            
                            results.append(f"🔹 **{title}**\n{snippet}\n[Link]({link})")
                    except:
                        continue
                        
                browser.close()
                
                if not results:
                    return "No results found."
                    
                return "\n\n".join(results)
                
        except Exception as e:
            logger.error(f"Search Sync Error: {e}")
            return f"Search failed: {e}"

    async def search_async(self, query):
        """
        Async DuckDuckGo Search (for Telegram).
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto("https://html.duckduckgo.com/html/", timeout=60000)
                
                await page.fill('input[name="q"]', query)
                await page.keyboard.press("Enter")
                
                try:
                    await page.wait_for_selector(".result", timeout=15000)
                except:
                    await browser.close()
                    return "No results found."
                
                results = []
                result_divs = await page.locator('.result').all()
                
                for div in result_divs[:5]:
                    try:
                        title_el = div.locator(".result__title").first
                        snippet_el = div.locator(".result__snippet").first
                        link_a = div.locator("a.result__a").first
                        
                        if await title_el.count() > 0:
                            title = await title_el.inner_text()
                            title = title.strip()
                            
                            link = await link_a.get_attribute("href") if await link_a.count() > 0 else "N/A"
                            snippet = await snippet_el.inner_text() if await snippet_el.count() > 0 else ""
                            snippet = snippet.strip()
                            
                            results.append(f"🔹 **{title}**\n{snippet}\n[Link]({link})")
                    except:
                        continue
                        
                await browser.close()
                
                if not results:
                    return "No results found."
                    
                return "\n\n".join(results)
                
        except Exception as e:
            logger.error(f"Search Async Error: {e}")
            return f"Search failed: {e}"
