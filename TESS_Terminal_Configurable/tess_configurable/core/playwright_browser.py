"""
Playwright Browser - Modern browser automation.
Replaces Selenium with Playwright for better reliability.
"""

import asyncio
import os
import time
from typing import Optional, Dict, Any
from pathlib import Path


class PlaywrightBrowser:
    """
    Modern browser automation using Playwright.
    More reliable than Selenium for web apps like WhatsApp Web.
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
    
    async def _init(self):
        """Initialize Playwright."""
        if self.context:  # FIX: Check context, not browser
            return
        
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            
            # Create context with persistent storage for WhatsApp login
            from ..config_manager import get_config_manager
            config = get_config_manager()
            user_data = Path(config.config.paths.data_dir) / "browser_data"
            user_data.mkdir(parents=True, exist_ok=True)
            
            # Use persistent context to maintain WhatsApp login
            self.context = await self.playwright.chromium.launch_persistent_context(
                str(user_data),
                headless=self.headless,
                viewport={'width': 1280, 'height': 800},
                permissions=['notifications'],
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--no-first-run',
                    '--start-maximized'
                ]
            )
            
            # FIX: Persistent context returns context directly, get page from it
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
            
        except ImportError:
            raise ImportError("Playwright not installed. Run: pip install playwright && playwright install chromium")
    
    async def goto(self, url: str, wait_until: str = "networkidle"):
        """Navigate to URL."""
        await self._init()
        await self.page.goto(url, wait_until=wait_until)
    
    async def click(self, selector: str, timeout: int = 5000):
        """Click element with auto-wait."""
        await self.page.click(selector, timeout=timeout)
    
    async def fill(self, selector: str, text: str, timeout: int = 5000):
        """Fill input field."""
        await self.page.fill(selector, text, timeout=timeout)
    
    async def type(self, selector: str, text: str, delay: int = 50):
        """Type text with human-like delay."""
        await self.page.type(selector, text, delay=delay)
    
    async def get_text(self, selector: str, timeout: int = 5000) -> str:
        """Get element text content."""
        element = await self.page.wait_for_selector(selector, timeout=timeout)
        return await element.text_content() if element else ""
    
    async def get_inner_html(self, selector: str) -> str:
        """Get element inner HTML."""
        return await self.page.inner_html(selector)
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000):
        """Wait for element to appear."""
        return await self.page.wait_for_selector(selector, timeout=timeout)
    
    async def wait_for_navigation(self, timeout: int = 10000):
        """Wait for page navigation."""
        await self.page.wait_for_load_state("networkidle", timeout=timeout)
    
    async def screenshot(self, path: str):
        """Take screenshot."""
        await self.page.screenshot(path=path, full_page=True)
    
    async def evaluate(self, script: str) -> Any:
        """Execute JavaScript."""
        return await self.page.evaluate(script)
    
    async def get_cookies(self) -> list:
        """Get all cookies."""
        return await self.context.cookies()
    
    async def close(self):
        """Close browser."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
        except Exception:
            pass
        self.page = None
    
    # ===== Sync wrappers for easier use =====
    
    def goto_sync(self, url: str, wait_until: str = "networkidle"):
        return asyncio.run(self.goto(url, wait_until))
    
    def click_sync(self, selector: str, timeout: int = 5000):
        return asyncio.run(self.click(selector, timeout))
    
    def fill_sync(self, selector: str, text: str, timeout: int = 5000):
        return asyncio.run(self.fill(selector, text, timeout))
    
    def get_text_sync(self, selector: str, timeout: int = 5000) -> str:
        return asyncio.run(self.get_text(selector, timeout))
    
    def screenshot_sync(self, path: str):
        return asyncio.run(self.screenshot(path))


class WhatsAppPlaywright:
    """
    WhatsApp Web using Playwright - SYNC version based on working original.
    Uses sync_playwright to avoid async/event loop issues.
    """
    
    def __init__(self, brain=None):
        self.brain = brain
        self.logged_in = False
        self.browser = None
        self.context = None
        self.page = None
        
        # Setup user data directory for persistent login
        from ..config_manager import get_config_manager
        config = get_config_manager()
        self.user_data_dir = str(Path(config.config.paths.data_dir) / "whatsapp_session")
        os.makedirs(self.user_data_dir, exist_ok=True)
    
    def _init_browser(self):
        """Initialize browser if not already done."""
        if self.page:
            return
            
        from playwright.sync_api import sync_playwright
        
        self.playwright = sync_playwright().start()
        
        # Launch persistent context (saves login session)
        self.context = self.playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=False,
            viewport={'width': 1280, 'height': 720},
            args=[
                '--disable-blink-features=AutomationControlled',
                '--start-maximized'
            ],
            permissions=['notifications', 'microphone', 'camera']
        )
        
        # Get or create page
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()
    
    def login(self) -> str:
        """Login to WhatsApp Web."""
        try:
            self._init_browser()
            self.page.goto("https://web.whatsapp.com")
            
            # Wait for login - check for search box (data-tab="3")
            try:
                self.page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=45000)
                self.logged_in = True
                return "✓ Logged in successfully!"
            except Exception:
                return "⚠ QR code not scanned. Please scan the QR code in the browser."
                
        except Exception as e:
            return f"Login error: {e}"
    
    def send_message(self, contact: str, message: str) -> str:
        """Send message to contact."""
        if not self.logged_in:
            result = self.login()
            if "error" in result.lower() and "QR code" not in result.lower():
                return result
        
        try:
            # Search for contact using the working selector from original
            search_box = self.page.locator('div[contenteditable="true"][data-tab="3"]')
            search_box.click()
            
            # Clear existing text
            self.page.keyboard.down("Control")
            self.page.keyboard.press("a")
            self.page.keyboard.up("Control")
            self.page.keyboard.press("Backspace")
            
            # Type contact name
            search_box.fill(contact)
            import time
            time.sleep(2)
            
            # Press Enter to open chat
            self.page.keyboard.press("Enter")
            time.sleep(2)
            
            # Type message
            self.page.keyboard.type(message)
            time.sleep(0.5)
            
            # Send
            self.page.keyboard.press("Enter")
            time.sleep(1)
            
            return f"✓ Message sent to {contact}"
            
        except Exception as e:
            return f"Send error: {e}"
    
    def close(self):
        """Close browser."""
        try:
            if self.context:
                self.context.close()
        except:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except:
            pass
        self.page = None
        self.context = None
    
    # Sync wrappers (for API compatibility)
    def login_sync(self) -> str:
        return self.login()
    
    def send_message_sync(self, contact: str, message: str) -> str:
        return self.send_message(contact, message)


class WebSearchPlaywright:
    """
    Web search using Playwright.
    """
    
    def __init__(self):
        self.browser = PlaywrightBrowser(headless=True)
    
    async def search(self, query: str) -> str:
        """Search Google and return results."""
        try:
            from urllib.parse import quote_plus
            encoded_query = quote_plus(query)
            await self.browser.goto(f"https://www.google.com/search?q={encoded_query}")
            
            # Wait for results
            await self.browser.wait_for_selector("#search", timeout=10000)
            
            # Extract results
            page = self.browser.page
            
            # Get search results
            results = await page.query_selector_all("div.g")
            output = []
            
            for i, result in enumerate(results[:5], 1):
                try:
                    title_elem = await result.query_selector("h3")
                    title = await title_elem.text_content() if title_elem else "No title"
                    
                    snippet_elem = await result.query_selector("div.VwiC3b")
                    snippet = await snippet_elem.text_content() if snippet_elem else ""
                    
                    output.append(f"{i}. {title}\n{snippet[:150]}...")
                except Exception:
                    continue
            
            return "\n\n".join(output) if output else "No results found"
            
        except Exception as e:
            return f"Search error: {e}"
        finally:
            await self.browser.close()
    
    def search_sync(self, query: str) -> str:
        return asyncio.run(self.search(query))


# Factory function to migrate gradually
def get_browser(use_playwright: bool = False):
    """Get browser instance. Set use_playwright=True to use new system."""
    if use_playwright:
        return PlaywrightBrowser()
    else:
        # Fallback to old Selenium WebBrowser
        from .web_browser import WebBrowser
        return WebBrowser()
