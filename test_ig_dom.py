import os
from playwright.sync_api import sync_playwright

profile_dir = os.path.join(os.path.expanduser("~"), ".tess", "playwright_instagram_profile")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=True,
        viewport={"width": 1280, "height": 800}
    )
    page = context.new_page()
    page.goto("https://www.instagram.com/direct/inbox/")
    page.wait_for_timeout(3000)

    # Click New Message
    page.get_by_label("New message").click(timeout=5000)
    page.wait_for_timeout(1000)
    
    # Search
    search_input = page.locator("input[placeholder='Search...']")
    username = "niightthawkk"
    search_input.fill(username)
    page.wait_for_timeout(2000)
    
    # Click User
    page.locator("div[role='dialog']").get_by_text(username, exact=False).first.click()
    page.get_by_role("button", name="Chat").click()
    page.wait_for_timeout(3000)

    # Dump all div elements with text
    divs = page.locator("div[dir='auto']").all()
    print(f"Found {len(divs)} divs with dir=auto")
    for idx, div in enumerate(divs[-15:]):  # print last 15
        try:
            print(f"[{idx}]: {div.inner_text().strip()}")
        except:
            pass
    
    context.close()
