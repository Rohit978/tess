
import logging
import time
import os
from playwright.sync_api import sync_playwright

# Setup simple logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CanvaAutomator")

class CanvaAutomator:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # PERSISTENCE: Save login cookies here
        self.user_data_dir = os.path.join(os.getcwd(), "data", "canva_session")
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

    def start(self):
        logger.info(f"🌐 Launching Canva (Headless={self.headless})...")
        self.playwright = sync_playwright().start()
        
        # Launch persistent context
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            channel="chrome", # Try to use installed Chrome for better login success
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.goto("https://www.canva.com")
        
        logger.info("✅ Browser launched. Checking login status...")
        
        # Check if logged in by looking for "Create a design" button
        # Selector might change, but usually there's a 'Create a design' button in header
        try:
            # Flexible selector for the main CTA
            self.page.wait_for_selector('button:has-text("Create a design"), button:has-text("Create design"), button#create-design-button, button:has-text("Create")', timeout=5000)
            logger.info("✅ User is LOGGED IN.")
        except:
            logger.warning("⚠️ User NOT logged in. Waiting for manual login...")
            print("\n🚨 PLEASE LOG IN TO CANVA IN THE BROWSER WINDOW NOW. 🚨\n")
            # Wait indefinitely for user to login
            self.page.wait_for_selector('button:has-text("Create a design"), button:has-text("Create design"), button#create-design-button', timeout=300000)
            logger.info("✅ Login detected!")

    def create_design(self, design_type="Instagram Post"):
        logger.info(f"🎨 Creating new design: {design_type}")
        
        # 1. Click 'Create a design'
        if self.page.is_visible('button:has-text("Create a design")'):
            self.page.click('button:has-text("Create a design")')
        elif self.page.is_visible('button:has-text("Create design")'):
            self.page.click('button:has-text("Create design")')
        elif self.page.is_visible('button#create-design-button'):
            self.page.click('button#create-design-button')
        else:
            # Fallback for sidebar
            self.page.click('button:has-text("Create")')
            
        time.sleep(1)
        
        # 2. Type in search box (it appears in a dropdown)
        # We look for the input field inside the dropdown menu
        self.page.type('input[placeholder*="Search"]', design_type, delay=100)
        time.sleep(1)
        
        # 3. Press Enter to select first result (or click it)
        self.page.keyboard.press("Enter")
        
        logger.info("⏳ Waiting for editor to load...")
        # Canva opens new tab for editor usually
        # We need to handle new page
        with self.context.expect_page() as new_page_info:
            logger.info("   (Opening new tab...)")
            
        new_page = new_page_info.value
        new_page.wait_for_load_state()
        logger.info(f"✅ Editor loaded: {new_page.title()}")
        
        # Optional: Add a text heading to prove it works
        try:
            logger.info("✍️  Adding text to canvas...")
            new_page.keyboard.press("t") # 't' is shortcut for Text
            time.sleep(1)
            new_page.keyboard.type("Hello from TESS!", delay=50)
        except Exception as e:
            logger.error(f"Failed to add text: {e}")

        logger.info("✨ Demo complete! Keeping browser open for 10s...")
        time.sleep(10)

if __name__ == "__main__":
    bot = CanvaAutomator(headless=False)
    try:
        bot.start()
        bot.create_design("Instagram Post")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # bot.context.close() # Keep open for debugging
        pass
