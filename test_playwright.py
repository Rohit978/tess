import os
from playwright.sync_api import sync_playwright

print("Starting playwright test...")
user_data_dir = os.path.join(os.getcwd(), "test_whatsapp_session")

try:
    with sync_playwright() as p:
        print("Playwright synced. Launching context...")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            viewport={"width": 1280, "height": 720},
            args=["--disable-blink-features=AutomationControlled", "--start-maximized", "--no-sandbox"],
            permissions=["microphone", "camera"]
        )
        print("Context launched. Opening page...")
        page = browser.pages[0] if browser.pages else browser.new_page()
        print("Navigating to WhatsApp...")
        page.goto("https://web.whatsapp.com", timeout=10000)
        print("Successfully reached WhatsApp Web.")
        browser.close()
except Exception as e:
    import traceback
    traceback.print_exc()
