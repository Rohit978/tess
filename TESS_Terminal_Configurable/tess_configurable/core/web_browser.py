"""
Web Browser module - Search and scrape web content.
Uses Selenium for browser automation.
"""

import time
import urllib.parse
from typing import Optional
from pathlib import Path


class WebBrowser:
    """
    Web browsing capabilities using Selenium.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self._init_driver()
    
    def _init_driver(self):
        """Initialize Selenium WebDriver."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = Options()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
        except Exception as e:
            print(f"WebDriver init failed: {e}")
            self.driver = None
    
    def search(self, query: str) -> str:
        """
        Search Google and return results.
        
        Args:
            query: Search query
            
        Returns:
            Search results text
        """
        if not self.driver:
            # Fallback: return instructions
            return f"Search: {query}\n(Web search requires Selenium setup)"
        
        try:
            # Google search
            encoded = urllib.parse.quote(query)
            url = f"https://www.google.com/search?q={encoded}"
            
            self.driver.get(url)
            time.sleep(2)  # Wait for JS
            
            # Extract results
            results = []
            
            # Try to find result snippets
            try:
                from selenium.webdriver.common.by import By
                
                # Featured snippet
                snippets = self.driver.find_elements(By.CSS_SELECTOR, "span.ILfuVd")
                if snippets:
                    results.append(f"Featured: {snippets[0].text}")
                
                # Regular results
                result_divs = self.driver.find_elements(By.CSS_SELECTOR, "div.g")[:5]
                for div in result_divs:
                    try:
                        title = div.find_element(By.CSS_SELECTOR, "h3").text
                        snippet = div.find_element(By.CSS_SELECTOR, "div.VwiC3b").text
                        results.append(f"- {title}: {snippet[:100]}...")
                    except:
                        pass
                        
            except Exception as e:
                results.append(f"Error extracting: {e}")
            
            return "\n".join(results) if results else "No results found"
            
        except Exception as e:
            return f"Search error: {e}"
    
    def scrape(self, url: str) -> str:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Page content
        """
        if not self.driver:
            return f"Cannot scrape {url} - WebDriver not available"
        
        try:
            self.driver.get(url)
            time.sleep(2)
            
            # Get main content
            from selenium.webdriver.common.by import By
            
            # Try to find main content
            selectors = ["main", "article", "div.content", "div.main", "body"]
            for sel in selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, sel)
                    text = elem.text
                    if len(text) > 100:
                        return text[:3000]  # Limit
                except:
                    continue
            
            # Fallback to body
            return self.driver.find_element(By.TAG_NAME, "body").text[:3000]
            
        except Exception as e:
            return f"Scrape error: {e}"
    
    def screenshot(self, url: str, output_path: Optional[str] = None) -> str:
        """
        Take screenshot of a webpage.
        
        Args:
            url: URL to screenshot
            output_path: Where to save (default: temp dir)
            
        Returns:
            Path to saved screenshot
        """
        if not self.driver:
            return "WebDriver not available"
        
        try:
            if output_path is None:
                from ..config_manager import get_config_manager
                config = get_config_manager()
                output_path = str(Path(config.config.paths.temp_dir) / f"screenshot_{int(time.time())}.png")
            
            self.driver.get(url)
            time.sleep(2)
            self.driver.save_screenshot(output_path)
            
            return output_path
            
        except Exception as e:
            return f"Screenshot error: {e}"
    
    def close(self):
        """Close browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __del__(self):
        self.close()
