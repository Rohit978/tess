from playwright.sync_api import sync_playwright, Page, Locator
import os
import time
import queue
import threading
import random
from .logger import setup_logger
from .terminal_ui import C

logger = setup_logger("WhatsAppClient")

# ─────────────────────────────────────────────
# Selector banks — ordered by reliability.
# If WhatsApp updates its DOM, add new selectors
# at the TOP of each list without removing old ones.
# ─────────────────────────────────────────────

SEARCH_SELECTORS = [
    # WhatsApp Web 2024+
    'div[contenteditable="true"][data-tab="3"]',
    'div[aria-label="Search input textbox"]',
    'div[title="Search input textbox"]',
    # Structural fallbacks
    'div#side div[contenteditable="true"]',
    'label div div[contenteditable="true"]',
    'div[role="textbox"][data-tab="3"]',
    # Last-resort
    'div.selectable-text[data-lexical-editor="true"]',
    'div[class*="search"] div[contenteditable="true"]',
]

CHAT_INPUT_SELECTORS = [
    'div[contenteditable="true"][data-tab="10"]',
    'div[title="Type a message"]',
    'footer div[contenteditable="true"]',
    'div[aria-label="Type a message"]',
    'div[role="textbox"][data-tab="10"]',
    'div[class*="chat"] div[contenteditable="true"]:last-child',
]

SEND_BTN_SELECTORS = [
    'button[aria-label="Send"]',
    'span[data-icon="send"]',
    'button[data-icon="send"]',
]

VOICE_CALL_BTN_SELECTORS = [
    'button[aria-label*="Voice call"]',
    'button[title*="Voice call"]',
    'header span[data-icon="call"]',
    'span[data-icon="call"]',
]

VIDEO_CALL_BTN_SELECTORS = [
    'button[aria-label*="Video call"]',
    'button[title*="Video call"]',
    'header span[data-icon="video-call"]',
    'span[data-icon="video-call"]',
]

ANSWER_CALL_BTN_SELECTORS = [
    'button[aria-label*="Answer"]',
    'button[title*="Answer"]',
    'button[data-testid*="incoming-call-accept"]',
    'span[data-icon*="accept"]',
]

LOGIN_READY_SELECTORS = [
    'div#pane-side',
    'div[data-tab="3"]',
    'div[aria-label="Chat list"]',
    'div[contenteditable="true"]',
]


def _wait(sec: float):
    time.sleep(sec)


class WhatsAppClient:
    def __init__(self, brain, voice_client=None):
        self.brain = brain
        self.voice_client = voice_client
        self.user_data_dir = os.path.join(os.getcwd(), "data", "whatsapp_session")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.screenshot_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.msg_queue = queue.Queue()
        self._state_lock = threading.Lock()   # Protects shared mutable state
        self._active_contact = None
        self.stop_event = threading.Event()
        self._monitor_thread = None
        self._page = None

    # --- Thread-safe properties ---
    @property
    def page(self):
        with self._state_lock:
            return self._page

    @page.setter
    def page(self, value):
        with self._state_lock:
            self._page = value

    @property
    def active_contact(self):
        with self._state_lock:
            return self._active_contact

    @active_contact.setter
    def active_contact(self, value):
        with self._state_lock:
            self._active_contact = value

    @property
    def monitor_thread(self):
        with self._state_lock:
            return self._monitor_thread

    @monitor_thread.setter
    def monitor_thread(self, value):
        with self._state_lock:
            self._monitor_thread = value

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def monitor_chat(self, contact_name, mission=None):
        """Start the WhatsApp monitor in a background thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.debug(f"Monitor already running. Switching focus to {contact_name}")
            self.active_contact = contact_name
            return

        self.stop_event.clear()
        self.monitor_thread = threading.Thread(
            target=self.monitor_loop,
            args=(self.stop_event, contact_name, mission),
            daemon=True,
        )
        self.monitor_thread.start()
        logger.debug(f"WhatsApp Monitor thread started for {contact_name}")

        # Wait up to 10 s for Playwright to bootstrap
        for _ in range(20):
            if self.page and not self.page.is_closed():
                break
            _wait(0.5)

    def stop(self):
        """Stop the monitor loop."""
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.debug("WhatsApp Monitor Stopped.")

    def send_message(self, contact, message):
        """Queue a message for a contact, auto-starting the monitor if needed."""
        if not contact:
            return "Error: No contact specified."

        logger.debug(f"Queuing message for {contact}: {message}")
        self.msg_queue.put({"contact": contact, "message": message, "action": "send"})

        if not self.monitor_thread or not self.monitor_thread.is_alive():
            print(f"  {C.DIM}🌐 Launching WhatsApp Monitor...{C.R}")
            self.monitor_chat(contact)
            for _ in range(10):
                if self.monitor_thread and self.monitor_thread.is_alive():
                    return f"WhatsApp launching… Message queued for {contact}."
                _wait(0.5)
            return "Error: WhatsApp thread failed to start."

        return f"Message queued for {contact}."

    def call_contact(self, contact, video=False):
        """Queue a WhatsApp Web call action for a contact."""
        if not contact:
            contact = self.active_contact
        if not contact:
            return "Error: No contact specified for call."

        self.msg_queue.put(
            {"contact": contact, "action": "call", "video": bool(video)}
        )

        if not self.monitor_thread or not self.monitor_thread.is_alive():
            print(f"  {C.DIM}🌐 Launching WhatsApp Monitor...{C.R}")
            self.monitor_chat(contact)
            for _ in range(10):
                if self.monitor_thread and self.monitor_thread.is_alive():
                    return f"WhatsApp launching… Call queued for {contact}."
                _wait(0.5)
            return "Error: WhatsApp thread failed to start."

        return f"Call queued for {contact}."

    def answer_call(self):
        """Queue an incoming call answer action on WhatsApp Web."""
        self.msg_queue.put({"action": "answer"})

        if not self.monitor_thread or not self.monitor_thread.is_alive():
            print(f"  {C.DIM}🌐 Launching WhatsApp Monitor...{C.R}")
            self.monitor_chat(None)
            for _ in range(10):
                if self.monitor_thread and self.monitor_thread.is_alive():
                    return "WhatsApp launching… Answer action queued."
                _wait(0.5)
            return "Error: WhatsApp thread failed to start."

        return "Answer action queued."

    # ─────────────────────────────────────────
    # Self-healing locator helpers
    # ─────────────────────────────────────────

    def _find_element(
        self,
        page: Page,
        selectors: list[str],
        label: str = "element",
        timeout: float = 5.0,
    ) -> Locator | None:
        """
        Try each selector in order.  If none match in the DOM, attempt via
        JavaScript injection as a last resort.  Returns None only if every
        strategy fails.
        """
        # 1. Selector sweep
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=timeout * 1000)
                logger.debug(f"[self-heal] {label} found via: {sel}")
                return loc
            except Exception:
                continue

        # 2. Aria snapshot fallback — ask the page for appropriate roles
        try:
            target_role = "button" if "button" in label else "textbox"
            elements = page.get_by_role(target_role).all()
            if elements:
                # For buttons, we only want to fallback if it matches 'send'
                if target_role == "button":
                    for el in elements:
                        txt = el.text_content() or ""
                        if "send" in txt.lower():
                            return el
                else:
                    logger.debug(f"[self-heal] {label} found via get_by_role('{target_role}')")
                    return elements[0]
        except Exception:
            pass

        # 3. JavaScript injection (Only for inputs/search)
        if "button" not in label:
            region = "div#side" if "search" in label.lower() else "footer"
            try:
                js = f"""
                (function() {{
                    var area = document.querySelector('{region}')
                             || document.querySelector('body');
                    var els = area.querySelectorAll('div[contenteditable="true"]');
                    for (var i = 0; i < els.length; i++) {{
                        var r = els[i].getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) return els[i];
                    }}
                    return null;
                }})()
                """
                el = page.evaluate_handle(js)
                if el:
                    logger.debug(f"[self-heal] {label} recovered via JavaScript injection")
                    return page.locator(
                        f"{region} div[contenteditable='true']"
                    ).first
            except Exception as e:
                logger.warning(f"[self-heal] JS fallback failed for {label}: {e}")

        logger.error(f"[self-heal] ❌ Could not locate {label} with any strategy.")
        return None

    def _click_search_icon(self, page: Page) -> bool:
        """
        Ensure the search bar is open/focused by clicking the search icon first.
        Some WhatsApp versions hide the bar until the icon is clicked.
        """
        icon_selectors = [
            'span[data-icon="search"]',
            'button[aria-label="Search or start new chat"]',
            'button[title="New chat"]',
            'div[data-tab="3"]',
        ]
        for sel in icon_selectors:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=2000):
                    loc.click()
                    _wait(0.4)
                    logger.debug(f"[self-heal] Opened search via: {sel}")
                    return True
            except Exception:
                continue
        return False

    def _screenshot(self, page: Page, name: str):
        """Save a debug screenshot."""
        try:
            path = os.path.join(self.screenshot_dir, f"{name}.png")
            page.screenshot(path=path)
            logger.debug(f"Screenshot saved: {path}")
        except Exception:
            pass

    # ─────────────────────────────────────────
    # Chat navigation
    # ─────────────────────────────────────────

    def _open_chat(self, page: Page, name: str, retries: int = 3) -> bool:
        """
        Navigate to a contact's chat.
        Self-heals on failure by retrying with progressively looser strategies.
        Returns True on success.
        """
        if not name:
            return False

        for attempt in range(1, retries + 1):
            print(f"  {C.DIM}🔍 Opening chat: {name} (attempt {attempt}/{retries})…{C.R}")
            try:
                # Step 1: Try clicking search icon to reveal bar
                self._click_search_icon(page)

                # Step 2: Locate search input
                search_box = self._find_element(
                    page, SEARCH_SELECTORS, label="search bar", timeout=6.0
                )
                if not search_box:
                    logger.warning(f"Search bar not found on attempt {attempt}. Reloading page…")
                    self._screenshot(page, f"search_fail_attempt_{attempt}")
                    page.reload(wait_until="domcontentloaded", timeout=30000)
                    _wait(3)
                    continue

                # Step 3: Click, clear, type
                search_box.click()
                _wait(0.4)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                _wait(0.3)
                page.keyboard.type(name, delay=100)
                _wait(2)

                # Step 4: Pick first result (multiple strategies)
                opened = False

                # Strategy A: exact row filter
                result_selectors = [
                    f'div#pane-side div[role="row"]',
                    f'div[aria-label="Search results."] div[role="row"]',
                    f'div[class*="search"] div[role="listitem"]',
                ]
                for rsel in result_selectors:
                    try:
                        row = page.locator(rsel).filter(has_text=name).first
                        if row.is_visible(timeout=3000):
                            row.click()
                            opened = True
                            break
                    except Exception:
                        continue

                # Strategy B: press Enter
                if not opened:
                    logger.debug("No result row matched. Pressing Enter…")
                    page.keyboard.press("Enter")
                    _wait(2)
                    opened = True  # optimistic

                _wait(2)

                # Step 5: Verify chat opened
                header_selectors = [
                    f'header span[title="{name}"]',
                    f'header span[title*="{name.split()[0]}"]',
                    'div[data-testid="conversation-info-header"]',
                ]
                for hsel in header_selectors:
                    try:
                        if page.locator(hsel).is_visible(timeout=3000):
                            print(f"  {C.GREEN}✅ Chat opened: {name}{C.R}")
                            self.active_contact = name
                            self._screenshot(page, f"chat_opened_{name.replace(' ', '_')}")
                            return True
                    except Exception:
                        continue

                # Chat might still be open even if header text doesn't match exactly
                if opened:
                    print(f"  {C.YELLOW}⚠️  Opened a chat (header verify failed for '{name}').{C.R}")
                    self.active_contact = name
                    return True

            except Exception as e:
                logger.error(f"open_chat attempt {attempt} failed: {e}")
                self._screenshot(page, f"open_chat_error_attempt_{attempt}")
                _wait(2)

        logger.error(f"❌ Failed to open chat for '{name}' after {retries} attempts.")
        return False

    def _send_text(self, page: Page, message: str) -> bool:
        """
        Type and send a message in the active chat.
        Self-heals if the input box isn't found.
        """
        inp = self._find_element(page, CHAT_INPUT_SELECTORS, label="chat input", timeout=5.0)
        if not inp:
            logger.error("Could not locate chat input box.")
            return False

        inp.click()
        _wait(0.3)

        # Human-like typing
        for char in message:
            page.keyboard.type(char)
            _wait(random.uniform(0.03, 0.08))

        _wait(0.5)
        page.keyboard.press("Enter")
        _wait(0.5)

        # Fallback: click send button if Enter didn't work and text is still there
        try:
            # Check if input still has text
            if inp.inner_text().strip():
                btn = self._find_element(page, SEND_BTN_SELECTORS, label="send button", timeout=2.0)
                if btn and btn.is_visible(timeout=1000):
                    btn.click()
        except Exception:
            pass

        return True

    def _click_first_visible(self, page: Page, selectors: list[str], timeout_ms=2000) -> bool:
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=timeout_ms):
                    loc.click()
                    return True
            except Exception:
                continue
        return False

    def _start_call(self, page: Page, video=False) -> bool:
        selectors = VIDEO_CALL_BTN_SELECTORS if video else VOICE_CALL_BTN_SELECTORS
        mode = "video" if video else "voice"
        print(f"  {C.DIM}📞 Starting {mode} call on WhatsApp Web...{C.R}")
        ok = self._click_first_visible(page, selectors, timeout_ms=3000)
        if not ok:
            logger.error("Call button not found in WhatsApp Web chat header.")
            self._screenshot(page, "whatsapp_call_button_missing")
            return False
        _wait(1.2)
        try:
            body_txt = (page.locator("body").inner_text(timeout=1500) or "").lower()
            if ("use whatsapp on your phone" in body_txt and "call" in body_txt) or (
                "continue on your phone" in body_txt and "call" in body_txt
            ):
                logger.error("WhatsApp Web requested phone handoff for calling.")
                self._screenshot(page, "whatsapp_call_phone_handoff")
                return False
        except Exception:
            pass
        return True

    def _answer_incoming_call(self, page: Page) -> bool:
        ok = self._click_first_visible(page, ANSWER_CALL_BTN_SELECTORS, timeout_ms=1500)
        if not ok:
            logger.warning("No incoming call answer button found.")
            return False
        _wait(1)
        return True

    # ─────────────────────────────────────────
    # Main monitor loop
    # ─────────────────────────────────────────

    def monitor_loop(self, stop_event, contact_name, mission=None):
        """Runs the WhatsApp monitor with full self-healing."""
        self.active_contact = contact_name
        logger.debug(f"Starting WhatsApp Monitor for: {contact_name} (Mission: {mission})")

        with sync_playwright() as p:
            try:
                print(f"  {C.DIM}🌐 Launching WhatsApp Browser…{C.R}")

                if self.page and not self.page.is_closed():
                    print(f"  {C.DIM}🌐 WhatsApp Browser already active.{C.R}")
                    return

                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=False,
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 720},
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--start-maximized",
                        "--no-sandbox",
                    ],
                    permissions=["microphone", "camera"],
                )

                self.page = browser.pages[0] if browser.pages else browser.new_page()
                page = self.page
                print(f"  {C.DIM}🌐 Navigating to WhatsApp Web…{C.R}")
                page.goto("https://web.whatsapp.com", timeout=60000)

                # ── Login wait ──────────────────────────────────
                print(f"  {C.DIM}🌐 Waiting for WhatsApp login…{C.R}")
                login_detected = False
                for i in range(45):
                    for sel in LOGIN_READY_SELECTORS:
                        try:
                            if page.locator(sel).is_visible(timeout=1000):
                                print(f"  {C.GREEN}✅ Logged in!{C.R}")
                                login_detected = True
                                break
                        except Exception:
                            continue
                    if login_detected:
                        break

                    if page.locator("canvas, div[data-ref]").count() > 0 and i % 5 == 0:
                        print(f"  {C.YELLOW}⚠️  Scan the QR code in the WhatsApp window.{C.R}")
                    _wait(2)

                if not login_detected:
                    self._screenshot(page, "whatsapp_login_timeout")
                    print(f"  {C.RED}❌ Login timeout. Screenshot saved.{C.R}")
                    self.brain.update_history("system", "WhatsApp login timeout.")
                    return

                # ── Dismiss banners ─────────────────────────────
                try:
                    for b in page.locator('span[data-icon="x"]').all():
                        if b.is_visible():
                            b.click()
                            _wait(0.4)
                except Exception:
                    pass

                # ── Open initial contact ────────────────────────
                if contact_name:
                    self._open_chat(page, contact_name)

                # ── Load recent chat for style context ──────────
                last_msg_text = ""
                style_context = ""
                try:
                    rows = page.locator('div[role="row"]').all()
                    chat_log = []
                    for row in rows[-10:]:
                        is_me = row.locator(".message-out").count() > 0
                        sender = "Me" if is_me else (self.active_contact or "Them")
                        text = row.inner_text().split("\n")[0].strip()
                        if text:
                            chat_log.append(f"{sender}: {text}")
                            last_msg_text = text
                    style_context = "\n".join(chat_log)
                    logger.info(f"Style context loaded ({len(chat_log)} msgs).")
                except Exception as e:
                    logger.error(f"Failed to load history: {e}")

                # ── Main message loop ───────────────────────────
                while not stop_event.is_set():
                    try:
                        # A. Outgoing queue
                        while not self.msg_queue.empty():
                            item = self.msg_queue.get()
                            target = item.get("contact")
                            msg = item.get("message", "")
                            action = item.get("action", "send")

                            if target and target != self.active_contact:
                                self._open_chat(page, target)

                            if action == "send":
                                logger.debug(f"Sending queued: {msg}")
                                if self._send_text(page, msg):
                                    self.brain.update_history(
                                        "system", f"Sent to {self.active_contact}: {msg}"
                                    )
                                    style_context += f"\nMe: {msg}"
                                    last_msg_text = msg
                                _wait(1)
                            elif action == "call":
                                video = bool(item.get("video", False))
                                if self._start_call(page, video=video):
                                    mode = "video" if video else "voice"
                                    print(f"  {C.GREEN}✅ Started WhatsApp Web {mode} call.{C.R}")
                                    self.brain.update_history(
                                        "system",
                                        f"Started WhatsApp {mode} call with {self.active_contact or target}",
                                    )
                                else:
                                    self.brain.update_history(
                                        "system",
                                        "WhatsApp Web call failed or requested phone handoff."
                                    )
                                _wait(1)
                            elif action == "answer":
                                if self._answer_incoming_call(page):
                                    self.brain.update_history("system", "Answered incoming WhatsApp call.")
                                _wait(1)

                        # B. Incoming messages
                        rows = page.locator('div[role="row"]').all()
                        if rows:
                            last_row = rows[-1]
                            is_outgoing = last_row.locator(".message-out").count() > 0
                            if not is_outgoing:
                                try:
                                    text = last_row.inner_text().split("\n")[0].strip()
                                    if text and text != last_msg_text:
                                        logger.info(f"New msg from {self.active_contact}: {text}")
                                        last_msg_text = text
                                        self.brain.update_history(
                                            "user", f"[WhatsApp - {self.active_contact}]: {text}"
                                        )

                                        # Generate reply
                                        user_name = "User"
                                        if (
                                            hasattr(self.brain, "profile")
                                            and self.brain.profile
                                            and self.brain.profile.name
                                        ):
                                            user_name = self.brain.profile.name

                                        mission_prompt = f" MISSION: {mission}" if mission else ""
                                        chat_prompt = f"""
You are {user_name}, the owner of this phone. You are texting on WhatsApp.{mission_prompt}

RECENT HISTORY:
{style_context[-1000:]}

PARTNER JUST SAID: "{text}"

YOUR GOAL: Reply naturally as {user_name}. Be casual, use slang if appropriate.
CRITICAL:
1. You are NOT an AI. Do NOT call yourself TESS.
2. You are NOT an assistant. Do NOT offer to help.
3. Keep it short and human-like.

IMPORTANT: Output ONLY the message text. No JSON, no quotes, no labels.
"""
                                        reply = self.brain.request_completion(
                                            [{"role": "user", "content": chat_prompt}],
                                            json_mode=False,
                                            temperature=0.8,
                                        )
                                        if reply:
                                            logger.info(f"Typing reply: {reply}")
                                            self._send_text(page, reply)
                                            last_msg_text = reply
                                            style_context += f"\nMe: {reply}"
                                        else:
                                            logger.warning("Brain returned no reply.")
                                except Exception as e:
                                    logger.error(f"Error processing incoming msg: {e}")

                        _wait(2)

                    except Exception as loop_e:
                        logger.error(f"Monitor loop error: {loop_e}")
                        err = str(loop_e).lower()
                        if any(k in err for k in ["target closed", "connection closed", "browser has been closed"]):
                            logger.error("Browser closed — exiting monitor.")
                            break
                        _wait(5)

                logger.info("Stopping WhatsApp Monitor…")
                browser.close()

            except Exception as e:
                logger.error(f"WhatsApp Fatal Error: {e}")
                self.brain.update_history("system", f"WhatsApp Monitor failed: {e}")
