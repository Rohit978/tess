import json

from playwright.sync_api import sync_playwright

from .logger import setup_logger

logger = setup_logger("DOMController")


class DOMController:
    """
    Browser DOM automation controller backed by Playwright.
    Supports CSS/XPath/Text/Role locators, frame-aware actions, and self-healing retries.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._page = None
        self._browser_name = "edge"

    def _reset_session(self):
        try:
            if self._page:
                self._page.close()
        except Exception:
            pass
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        self._page = None
        self._browser = None

    def _is_session_alive(self):
        if not self._page or not self._browser:
            return False
        try:
            if self._page.is_closed():
                return False
            if not self._browser.is_connected():
                return False
            return True
        except Exception:
            return False

    def _launch_browser(self, browser_name="edge", headless=False):
        target = (browser_name or "edge").lower()
        if target in ["edge", "msedge", "microsoft-edge"]:
            try:
                self._browser_name = "edge"
                return self._playwright.chromium.launch(channel="msedge", headless=headless)
            except Exception as e:
                logger.warning(f"MS Edge launch failed; fallback to Chromium: {e}")
        if target == "chrome":
            try:
                self._browser_name = "chrome"
                return self._playwright.chromium.launch(channel="chrome", headless=headless)
            except Exception as e:
                logger.warning(f"Chrome launch failed; fallback to Chromium: {e}")
        self._browser_name = "chromium"
        return self._playwright.chromium.launch(headless=headless)

    def _ensure_page(self, headless=False, browser_name="edge", force_recreate=False):
        if force_recreate:
            self._reset_session()
        if self._is_session_alive():
            if browser_name and browser_name.lower() != self._browser_name:
                self._reset_session()
            else:
                return self._page
        if self._page:
            return self._page
        self._playwright = sync_playwright().start()
        self._browser = self._launch_browser(browser_name=browser_name, headless=headless)
        self._page = self._browser.new_page()
        return self._page

    def _all_frames(self, page):
        try:
            return list(page.frames)
        except Exception:
            return [page.main_frame]

    def _parse_role_selector(self, selector):
        # role=button;name=Log in;exact=true
        raw = selector[len("role="):].strip()
        parts = [p.strip() for p in raw.split(";") if p.strip()]
        if not parts:
            return None, {}
        role = parts[0]
        opts = {}
        for item in parts[1:]:
            if "=" not in item:
                continue
            k, v = item.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            if k in ["exact", "checked", "disabled", "selected"]:
                opts[k] = str(v).lower() in ["1", "true", "yes", "on"]
            elif k in ["name", "level"]:
                opts[k] = v
        return role, opts

    def _locator_from_selector(self, container, selector):
        s = str(selector or "").strip()
        if not s:
            return None
        if s.startswith("xpath="):
            return container.locator(f"xpath={s[len('xpath='):]}")
        if s.startswith("css="):
            return container.locator(s[len("css="):])
        if s.startswith("text="):
            txt = s[len("text="):].strip()
            return container.get_by_text(txt)
        if s.startswith("role="):
            role, opts = self._parse_role_selector(s)
            if role:
                try:
                    return container.get_by_role(role, **opts)
                except Exception:
                    return container.get_by_role(role)
        return container.locator(s)

    def _find_locator(self, selector, timeout=8000):
        page = self._ensure_page()
        frames = self._all_frames(page)
        last_err = None
        for frame in frames:
            try:
                loc = self._locator_from_selector(frame, selector)
                if loc is None:
                    continue
                loc.first.wait_for(state="attached", timeout=timeout)
                return loc.first
            except Exception as e:
                last_err = e
                continue
        if last_err:
            raise last_err
        raise RuntimeError(f"Could not locate selector: {selector}")

    def _retry_action(self, fn, retries=2):
        last = None
        for _ in range(retries + 1):
            try:
                return fn()
            except Exception as e:
                last = e
                page = self._ensure_page(force_recreate=True)
                _ = page
        raise last

    def open(self, url=None, headless=False, browser_name="edge"):
        page = self._ensure_page(headless=headless, browser_name=browser_name)
        if url:
            def _go():
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
            self._retry_action(_go, retries=1)
            return f"DOM session opened and navigated to {url}"
        return "DOM session opened."

    def navigate(self, url, browser_name="edge", headless=False):
        if not url:
            return "Provide a URL for navigation."
        page = self._ensure_page(headless=headless, browser_name=browser_name)
        def _go():
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
        self._retry_action(_go, retries=1)
        return f"Navigated to {url}"

    def click(self, selector):
        if not selector:
            return "Provide a selector for click."
        def _run():
            loc = self._find_locator(selector)
            loc.scroll_into_view_if_needed(timeout=5000)
            loc.click(timeout=15000)
        self._retry_action(_run, retries=1)
        return f"Clicked selector: {selector}"

    def type(self, selector, text, clear_first=False):
        if not selector:
            return "Provide a selector for typing."
        def _run():
            loc = self._find_locator(selector)
            loc.scroll_into_view_if_needed(timeout=5000)
            if clear_first:
                loc.fill(str(text or ""), timeout=15000)
            else:
                loc.click(timeout=10000)
                loc.type(str(text or ""), delay=20, timeout=15000)
        self._retry_action(_run, retries=1)
        return f"Typed into selector: {selector}"

    def press(self, key):
        page = self._ensure_page()
        page.keyboard.press(str(key or "").strip())
        return f"Pressed key: {key}"

    def wait_for(self, selector, state="visible", timeout=10000):
        loc = self._find_locator(selector, timeout=timeout)
        loc.wait_for(state=state, timeout=int(timeout))
        return f"Waited for selector: {selector} ({state})"

    def extract_text(self, selector=None, max_chars=2000):
        page = self._ensure_page()
        if selector:
            txt = self._find_locator(selector, timeout=10000).inner_text(timeout=15000)
        else:
            txt = page.locator("body").inner_text(timeout=15000)
        return (txt or "")[:int(max_chars)]

    def get_html(self, selector=None, max_chars=3000):
        page = self._ensure_page()
        if selector:
            html = self._find_locator(selector, timeout=10000).inner_html(timeout=15000)
        else:
            html = page.content()
        return (html or "")[:int(max_chars)]

    def evaluate(self, script):
        if not script:
            return "Provide JavaScript code for eval."
        page = self._ensure_page()
        result = page.evaluate(script)
        try:
            return json.dumps(result, ensure_ascii=True)
        except Exception:
            return str(result)

    def elements(self, selector=None, limit=20):
        page = self._ensure_page()
        sel = str(selector or "a,button,input,textarea,select,[role='button'],[role='link']")
        handle = page.evaluate(
            """([css, limit]) => {
                const nodes = Array.from(document.querySelectorAll(css)).slice(0, limit);
                return nodes.map((el, idx) => ({
                    index: idx,
                    tag: (el.tagName || '').toLowerCase(),
                    id: el.id || '',
                    classes: el.className || '',
                    role: el.getAttribute('role') || '',
                    name: el.getAttribute('name') || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    text: (el.innerText || el.textContent || '').trim().slice(0, 140),
                    visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
                }));
            }""",
            [sel, int(limit)],
        )
        return json.dumps(handle, ensure_ascii=True)

    def info(self):
        page = self._ensure_page()
        return json.dumps(
            {"url": page.url, "title": page.title(), "browser": self._browser_name},
            ensure_ascii=True,
        )

    def screenshot(self, path=None):
        page = self._ensure_page()
        target = str(path or "dom_page.png")
        page.screenshot(path=target, full_page=True)
        return f"DOM screenshot saved: {target}"

    def close(self):
        self._reset_session()
        if self._playwright:
            self._playwright.stop()
        self._playwright = None
        return "DOM session closed."

