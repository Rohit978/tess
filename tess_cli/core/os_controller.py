"""
OSController — Windows OS-level UI automation for TESS.

Works like dom_op but for native Windows apps.
Uses the Windows UI Automation (UIA) accessibility tree via pywinauto,
with an automatic vision-LLM fallback for apps that don't expose a UIA tree
(Electron, games, custom renderers, etc.).

Sub-actions:
    find        — Locate a UI element, return its description + bounding rect
    click       — Find and click an element
    type        — Find an input field and type text into it
    read        — Read all text from a window / specific element
    get_tree    — Dump the UIA element tree (like Chrome DevTools Elements panel)
    menu        — Navigate a menu path, e.g. "File->Save As"
"""

import os
import re
import time
import logging

import pyautogui

from .logger import setup_logger

logger = setup_logger("OSController")


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _parse_coords(text: str):
    """Extract x=<n> y=<n> from vision LLM response. Returns (x, y) or (None, None)."""
    m = re.search(r"x\s*=\s*(\d+).*?y\s*=\s*(\d+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        x, y = int(m.group(1)), int(m.group(2))
        if x > 0 and y > 0:
            return x, y
    return None, None


# ────────────────────────────────────────────────────────────────────────────
# Main class
# ────────────────────────────────────────────────────────────────────────────

class OSController:
    """
    OS-level UI controller.  Think of this as Playwright for the Windows desktop.

    Args:
        brain: TESS Brain instance (needed for vision fallback).
    """

    def __init__(self, brain=None):
        self.brain = brain
        self._desktop = None
        self._pywinauto_failed = False

    # ── Internal: UIA desktop handle ────────────────────────────────────────

    @property
    def desktop(self):
        if self._desktop is None:
            if self._pywinauto_failed:
                raise ImportError("pywinauto is not installed or failed to initialize.")
            try:
                from pywinauto import Desktop
                self._desktop = Desktop(backend="uia")
            except Exception as e:
                self._pywinauto_failed = True
                logger.warning(f"pywinauto Desktop init failed (desktop UI features disabled): {e}")
                raise
        return self._desktop

    def _get_window(self, app: str = None):
        """
        Resolve the target window.
        - If app is given, search by title (substring, case-insensitive).
        - Otherwise return the currently active foreground window.
        """
        try:
            if app:
                return self.desktop.window(title_re=f"(?i).*{re.escape(app)}.*")
            return self.desktop.active()
        except Exception as e:
            logger.warning(f"Window lookup failed (app={app!r}): {e}")
            return None

    # ── Internal: vision fallback ────────────────────────────────────────────

    def _take_snapshot(self) -> str | None:
        """Take a screenshot and return its absolute path."""
        try:
            from .desktop_vision import DesktopVisionController
            dv = DesktopVisionController()
            snap_name = f"os_vision_{int(time.time())}.png"
            dv.screenshot(filename=snap_name)
            snap_path = os.path.join(dv.snapshot_dir, snap_name)
            return snap_path if os.path.exists(snap_path) else None
        except Exception as e:
            logger.error(f"Snapshot failed: {e}")
            return None

    def _vision_locate(self, query: str) -> tuple[int | None, int | None]:
        """
        Use the vision LLM to find pixel coordinates of a UI element.
        Returns (x, y) or (None, None) if not found.
        """
        if not self.brain:
            logger.warning("Vision fallback skipped — no brain available.")
            return None, None

        snap_path = self._take_snapshot()
        if not snap_path:
            return None, None

        prompt = (
            f"This is a screenshot of a Windows desktop. "
            f"Find the UI element described as: \"{query}\". "
            f"Return ONLY one line in this exact format: x=<number> y=<number> "
            f"where the numbers are the pixel coordinates of the CENTER of that element. "
            f"If you cannot find it, return: x=0 y=0"
        )
        try:
            result = self.brain.request_vision(snap_path, prompt)
            x, y = _parse_coords(result)
            if x and y:
                logger.info(f"Vision located '{query}' at ({x}, {y})")
            else:
                logger.warning(f"Vision could not locate '{query}'")
            return x, y
        except Exception as e:
            logger.error(f"Vision locate error: {e}")
            return None, None

    def _vision_read(self, query: str = None) -> str:
        """Use vision LLM to read text visible on screen."""
        if not self.brain:
            return "Vision unavailable — no brain."

        snap_path = self._take_snapshot()
        if not snap_path:
            return "Could not take screenshot for vision read."

        prompt = (
            "Read all visible text on this Windows desktop screenshot."
            + (f" Focus specifically on: {query}." if query else "")
            + " Return the text verbatim, preserving structure."
        )
        try:
            return self.brain.request_vision(snap_path, prompt)
        except Exception as e:
            return f"Vision read error: {e}"

    # ── Internal: UIA element finder ─────────────────────────────────────────

    def _find_uia(self, query: str, window, control_type: str = None):
        """
        Walk the UIA tree of *window* looking for an element matching *query*.
        Returns the pywinauto control or None.
        """
        if not window:
            return None
        try:
            params = {"title_re": f"(?i).*{re.escape(query)}.*"}
            if control_type:
                params["control_type"] = control_type
            ctrl = window.child_window(**params)
            ctrl.wait("exists", timeout=3)
            return ctrl
        except Exception:
            pass
        # Second pass: search all descendants by window_text
        try:
            for child in window.descendants():
                try:
                    text = child.window_text().strip()
                    if query.lower() in text.lower():
                        if not control_type or child.element_info.control_type == control_type:
                            return child
                except Exception:
                    continue
        except Exception:
            pass
        return None

    # ── Public API ────────────────────────────────────────────────────────────

    def find(self, query: str, app: str = None, control_type: str = None) -> str:
        """
        Locate a UI element and return a description (name, type, bounding rect).
        Uses vision fallback if UIA cannot find it.
        """
        window = self._get_window(app)
        ctrl = self._find_uia(query, window, control_type)

        if ctrl:
            try:
                rect = ctrl.rectangle()
                ctype = ctrl.element_info.control_type or "Unknown"
                name = ctrl.window_text().strip() or "(no text)"
                return (
                    f"Found [{ctype}] '{name}'\n"
                    f"  Bounding rect: left={rect.left}, top={rect.top}, "
                    f"right={rect.right}, bottom={rect.bottom}\n"
                    f"  Center: ({(rect.left + rect.right)//2}, {(rect.top + rect.bottom)//2})"
                )
            except Exception as e:
                return f"Found element but could not inspect it: {e}"

        # Vision fallback
        x, y = self._vision_locate(query)
        if x and y:
            return f"Located '{query}' via vision at ({x}, {y})."
        return f"Element not found: '{query}'"

    def click(self, query: str, app: str = None, control_type: str = None) -> str:
        """Click a UI element. Falls back to vision-guided click."""
        window = self._get_window(app)
        ctrl = self._find_uia(query, window, control_type)

        if ctrl:
            try:
                ctrl.click_input()
                return f"Clicked '{query}' via UIA."
            except Exception as e:
                logger.warning(f"UIA click failed for '{query}': {e}")

        # Vision fallback
        x, y = self._vision_locate(query)
        if x and y:
            pyautogui.click(x, y)
            return f"Clicked '{query}' at ({x}, {y}) via vision."
        return f"Could not click '{query}' — element not found."

    def type(self, query: str, text: str, app: str = None) -> str:
        """
        Type *text* into the UI field described by *query*.
        Tries to find an Edit control first; falls back to vision click + pyautogui.write.
        """
        if not text:
            return "No text provided to type."

        window = self._get_window(app)

        # Prefer Edit control type
        ctrl = self._find_uia(query, window, control_type="Edit")
        if not ctrl:
            ctrl = self._find_uia(query, window)   # Any control

        if ctrl:
            try:
                ctrl.click_input()
                time.sleep(0.1)
                ctrl.type_keys(text, with_spaces=True)
                return f"Typed into '{query}' via UIA."
            except Exception as e:
                logger.warning(f"UIA type failed for '{query}': {e}")

        # Vision fallback: click to focus, then type
        x, y = self._vision_locate(query)
        if x and y:
            pyautogui.click(x, y)
            time.sleep(0.2)
            pyautogui.write(text, interval=0.02)
            return f"Typed into '{query}' at ({x}, {y}) via vision."
        return f"Could not find input field: '{query}'"

    def read(self, query: str = None, app: str = None) -> str:
        """
        Read text content from a window or specific element.
        Falls back to vision OCR if UIA returns nothing useful.
        """
        window = self._get_window(app)

        # Specific element
        if query and window:
            ctrl = self._find_uia(query, window)
            if ctrl:
                try:
                    text = ctrl.window_text().strip()
                    if text:
                        return text
                except Exception:
                    pass

        # All text in window
        if window:
            try:
                texts = []
                for ctrl in window.descendants():
                    try:
                        t = ctrl.window_text().strip()
                        if t and len(t) > 1:
                            texts.append(t)
                    except Exception:
                        continue
                combined = "\n".join(dict.fromkeys(texts))   # preserve order, deduplicate
                if combined.strip():
                    return combined
            except Exception as e:
                logger.warning(f"UIA read failed: {e}")

        # Vision fallback
        return self._vision_read(query)

    def get_tree(self, app: str = None, max_depth: int = 4) -> str:
        """
        Dump the UIA accessibility tree of the target window — like DevTools Elements panel.
        Returns a formatted indented string showing all interactive elements.
        """
        window = self._get_window(app)
        if not window:
            # Vision fallback: describe what's on screen
            if self.brain:
                snap_path = self._take_snapshot()
                if snap_path:
                    return self.brain.request_vision(
                        snap_path,
                        "List every visible UI element (buttons, text fields, menus, labels) "
                        "on this Windows desktop screenshot. Format as a structured list."
                    )
            return "Could not find window."

        lines = []
        try:
            win_title = window.window_text().strip() or "(no title)"
            lines.append(f"[Window] {win_title}")
            self._walk_tree(window, lines, depth=1, max_depth=max_depth)
        except Exception as e:
            return f"Tree walk error: {e}"

        return "\n".join(lines) if lines else "UI tree is empty."

    def _walk_tree(self, element, lines: list, depth: int, max_depth: int):
        """Recursively walk UIA children and append to lines."""
        if depth > max_depth:
            return
        indent = "  " * depth
        try:
            for child in element.children():
                try:
                    ctrl_type = child.element_info.control_type or "?"
                    name = child.window_text().strip() or "(no text)"
                    # Skip invisible / useless nodes
                    if ctrl_type in ("Pane", "Custom") and name == "(no text)":
                        self._walk_tree(child, lines, depth, max_depth)
                        continue
                    lines.append(f"{indent}[{ctrl_type}] {name}")
                    self._walk_tree(child, lines, depth + 1, max_depth)
                except Exception:
                    continue
        except Exception:
            pass

    def menu(self, path: str, app: str = None) -> str:
        """
        Select a menu item by path, e.g. "File->Save As".
        Falls back to vision-guided sequential clicking if menu_select() fails.
        """
        if not path:
            return "No menu path provided."

        window = self._get_window(app)
        if window:
            try:
                window.menu_select(path)
                return f"Selected menu: {path}"
            except Exception as e:
                logger.warning(f"menu_select failed for '{path}': {e}")

        # Vision fallback: click each menu level in sequence
        if self.brain:
            parts = [p.strip() for p in path.split("->")]
            for i, part in enumerate(parts):
                x, y = self._vision_locate(part)
                if x and y:
                    pyautogui.click(x, y)
                    time.sleep(0.3)
                else:
                    return f"Vision could not locate menu item: '{part}'"
            return f"Navigated menu '{path}' via vision."

        return f"Could not navigate menu: '{path}'"
