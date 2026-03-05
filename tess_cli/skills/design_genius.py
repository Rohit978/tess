
import os
import time
from playwright.sync_api import sync_playwright
from ..core.logger import setup_logger

logger = setup_logger("DesignGenius")

class DesignGenius:
    """
    The Artist: Creates stunning visuals using HTML/CSS + Playwright Screenshots.
    No API keys required. Infinite customization.
    """
    def __init__(self, brain):
        self.brain = brain
        self.output_dir = os.path.join(os.getcwd(), "workspace", "designs")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def create_post(self, topic, style="modern"):
        """
        Generates a social media post about a topic.
        1. Asks Brain for HTML/CSS.
        2. Renders via Playwright.
        3. Screenshots.
        """
        logger.info(f"🎨 Designing post for: {topic} ({style})")
        
        # 1. Generate Code
        prompt = (
            f"Create a single file HTML+CSS for a stunning social media post (1080x1080px) about '{topic}'.\n"
            f"Style: {style} (e.g., gradients, glassmorphism, bold typography).\n"
            "CRITICAL:\n"
            "- Use Google Fonts (import via URL).\n"
            "- Use random harmonious high-quality gradients or solid colors.\n"
            "- Center content perfectly using Flexbox/Grid.\n"
            "- Make sure text is large and legible.\n"
            "- Output ONLY the raw HTML code starting with <!DOCTYPE html>."
        )
        
        html_content = self.brain.think(prompt)
        # Clean up code blocks if present
        if "```html" in html_content:
            html_content = html_content.split("```html")[1].split("```")[0].strip()
        elif "```" in html_content:
            html_content = html_content.split("```")[1].split("```")[0].strip()

        # 2. Save HTML locally
        timestamp = int(time.time())
        html_path = os.path.join(self.output_dir, f"post_{timestamp}.html")
        img_path = os.path.join(self.output_dir, f"post_{timestamp}.png")
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        # 3. Render & Screenshot
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1080, "height": 1080})
                page.goto(f"file:///{html_path}")
                time.sleep(1) # Wait for fonts/rendering
                page.screenshot(path=img_path)
                browser.close()
                
            logger.info(f"✨ Design saved: {img_path}")
            return f"Design created successfully: {img_path}"
            
        except Exception as e:
            logger.error(f"Render failed: {e}")
            return f"Failed to render design: {e}"
