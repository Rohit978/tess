import ctypes
import json
import os
import re
import subprocess

import pyautogui
import psutil

from .logger import setup_logger

logger = setup_logger("DesktopVision")


class DesktopVisionController:
    """
    Desktop perception + interaction helpers for Windows apps.
    """

    def __init__(self):
        self.snapshot_dir = os.path.join(os.getcwd(), "data", "screenshots")
        os.makedirs(self.snapshot_dir, exist_ok=True)
        self._hidden_windows = {}
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self._SW_HIDE = 0
        self._SW_SHOW = 5
        self._SW_RESTORE = 9
        self._SW_MINIMIZE = 6
        self._GWL_EXSTYLE = -20
        self._WS_EX_TOOLWINDOW = 0x00000080
        self._WS_EX_APPWINDOW = 0x00040000
        self._SWP_NOSIZE = 0x0001
        self._SWP_NOMOVE = 0x0002
        self._SWP_NOZORDER = 0x0004
        self._SWP_NOACTIVATE = 0x0010
        self._SWP_FRAMECHANGED = 0x0020
        self._SWP_HIDEWINDOW = 0x0080

    def _run_ps(self, script, timeout=30):
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return (result.stdout or result.stderr).strip()
        except Exception as e:
            logger.error(f"PowerShell call failed: {e}")
            return f"Error: {e}"

    def list_visible_apps(self, query=None, limit=20):
        script = (
            "$apps = Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and "
            "$_.MainWindowTitle -and $_.MainWindowTitle.Trim().Length -gt 0 } | "
            "Select-Object ProcessName, Id, MainWindowTitle | Sort-Object ProcessName -Unique | "
            f"Select-Object -First {int(limit)}; "
            "$apps | ConvertTo-Json -Compress"
        )
        raw = self._run_ps(script)
        if raw.startswith("Error:"):
            return raw
        if not raw:
            return "No visible apps found."

        try:
            parsed = json.loads(raw)
            apps = parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            return raw

        if query:
            q = str(query).lower()
            apps = [
                app for app in apps
                if q in str(app.get("MainWindowTitle", "")).lower()
                or q in str(app.get("ProcessName", "")).lower()
            ]

        if not apps:
            return f"No visible apps matched '{query}'."

        lines = []
        for app in apps:
            lines.append(
                f"- {app.get('ProcessName', 'Unknown')} (PID {app.get('Id', '?')}): "
                f"{app.get('MainWindowTitle', '').strip()}"
            )
        return "Visible apps:\n" + "\n".join(lines)

    def active_app(self):
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return "No active foreground window found."
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buffer = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buffer, length)
            title = buffer.value.strip()
            return f"Active app window: {title}" if title else "Active window has no title."
        except Exception as e:
            logger.error(f"Failed to read active window: {e}")
            return f"Failed to read active app: {e}"

    def focus_app(self, title):
        if not title:
            return "Provide a window title to focus."
        safe_title = str(title).replace("'", "''")
        script = f"$ws = New-Object -ComObject WScript.Shell; $ws.AppActivate('{safe_title}')"
        out = self._run_ps(script)
        if out.lower() == "true":
            return f"Focused app window matching: {title}"
        return f"Could not focus app window: {title}"

    def screenshot(self, filename=None):
        try:
            if not filename:
                import time
                filename = f"desktop_{int(time.time())}.png"
            path = os.path.join(self.snapshot_dir, filename)
            pyautogui.screenshot(path)
            return f"Desktop screenshot saved: {path}"
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return f"Screenshot failed: {e}"

    def click(self, x, y):
        try:
            pyautogui.click(int(x), int(y))
            return f"Clicked at ({int(x)}, {int(y)})."
        except Exception as e:
            return f"Click failed: {e}"

    def type_text(self, text):
        if not text:
            return "No text provided."
        try:
            pyautogui.write(str(text), interval=0.02)
            return "Typed text into focused app."
        except Exception as e:
            return f"Typing failed: {e}"

    def hotkey(self, keys):
        if not keys:
            return "No hotkey provided."
        try:
            if isinstance(keys, str):
                parts = [k.strip() for k in keys.split("+") if k.strip()]
            else:
                parts = [str(k).strip() for k in keys if str(k).strip()]
            if not parts:
                return "No valid hotkey keys provided."
            pyautogui.hotkey(*parts)
            return f"Pressed hotkey: {'+'.join(parts)}"
        except Exception as e:
            return f"Hotkey failed: {e}"

    def _window_title(self, hwnd):
        length = self._user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value.strip()

    def _process_name(self, pid):
        try:
            return psutil.Process(pid).name()
        except Exception:
            return ""

    def _enum_windows(self):
        windows = []
        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def _callback(hwnd, _lparam):
            try:
                if not self._user32.IsWindow(hwnd):
                    return True
                if not self._user32.IsWindowVisible(hwnd):
                    return True
                title = self._window_title(hwnd)
                if not title:
                    return True
                pid = ctypes.c_ulong()
                self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                pname = self._process_name(pid.value)
                windows.append({
                    "hwnd": int(hwnd),
                    "title": title,
                    "pid": int(pid.value),
                    "process_name": pname,
                })
            except Exception:
                return True
            return True

        self._user32.EnumWindows(enum_proc(_callback), 0)
        return windows

    def _match_windows(self, query):
        q = str(query or "").strip().lower()
        if not q:
            return []
        qn = self._normalize_text(q)
        aliases = {
            "msedge": "microsoft edge",
            "microsoftedge": "microsoft edge",
            "edge": "microsoft edge",
            "ms edge": "microsoft edge",
        }
        qn = aliases.get(qn, qn)
        q_tokens = [t for t in qn.split(" ") if t]
        wins = self._enum_windows()
        matches = []
        for w in wins:
            title = str(w.get("title", ""))
            process_name = str(w.get("process_name", ""))
            combined_norm = self._normalize_text(f"{title} {process_name}")
            if qn in combined_norm:
                matches.append(w)
                continue
            if q_tokens and all(tok in combined_norm for tok in q_tokens):
                matches.append(w)
        return matches

    def _windows_by_pid(self, pid):
        try:
            target_pid = int(pid)
        except Exception:
            return []
        wins = self._enum_windows()
        return [w for w in wins if int(w.get("pid", -1)) == target_pid]

    def _normalize_text(self, text):
        s = re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()
        return " ".join(s.split())

    def _hide_window_with_verify(self, hwnd):
        if not self._user32.IsWindow(hwnd):
            return False, "invalid_window"
        self._user32.ShowWindow(hwnd, self._SW_HIDE)
        try:
            self._user32.ShowWindowAsync(hwnd, self._SW_HIDE)
        except Exception:
            pass
        try:
            self._user32.SetWindowPos(
                hwnd,
                0,
                0,
                0,
                0,
                0,
                self._SWP_NOMOVE | self._SWP_NOSIZE | self._SWP_NOZORDER | self._SWP_NOACTIVATE | self._SWP_HIDEWINDOW
            )
        except Exception:
            pass
        if not self._user32.IsWindowVisible(hwnd):
            return True, "hidden"
        return False, "still_visible"

    def _get_exstyle(self, hwnd):
        try:
            return int(self._user32.GetWindowLongW(hwnd, self._GWL_EXSTYLE))
        except Exception:
            return None

    def _set_exstyle(self, hwnd, exstyle):
        try:
            self._user32.SetWindowLongW(hwnd, self._GWL_EXSTYLE, int(exstyle))
            self._user32.SetWindowPos(
                hwnd,
                0,
                0,
                0,
                0,
                0,
                self._SWP_NOMOVE | self._SWP_NOSIZE | self._SWP_NOZORDER | self._SWP_NOACTIVATE | self._SWP_FRAMECHANGED
            )
            return True
        except Exception:
            return False

    def _apply_taskbar_exclusion(self, hwnd):
        original = self._get_exstyle(hwnd)
        if original is None:
            return None
        new_style = (original | self._WS_EX_TOOLWINDOW) & (~self._WS_EX_APPWINDOW)
        self._set_exstyle(hwnd, new_style)
        return original

    def _restore_taskbar_style(self, hwnd, original_exstyle):
        if original_exstyle is None:
            return
        self._set_exstyle(hwnd, original_exstyle)

    def hide_app(self, query=None, pid=None):
        targets = []
        if pid is not None:
            targets = self._windows_by_pid(pid)
            if not targets:
                return f"No visible windows found for PID {pid}."
        elif query:
            targets = self._match_windows(query)
        else:
            hwnd = int(self._user32.GetForegroundWindow())
            if hwnd:
                title = self._window_title(hwnd)
                if title:
                    pid = ctypes.c_ulong()
                    self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    targets = [{
                        "hwnd": hwnd,
                        "title": title,
                        "pid": int(pid.value),
                        "process_name": self._process_name(pid.value),
                    }]

        if not targets:
            return f"No app window found to hide for '{query}'." if query else "No active app to hide."

        hidden = []
        for t in targets:
            hwnd = int(t["hwnd"])
            original_exstyle = self._apply_taskbar_exclusion(hwnd)
            ok, _mode = self._hide_window_with_verify(hwnd)
            if not ok:
                self._restore_taskbar_style(hwnd, original_exstyle)
                continue
            tracked = dict(t)
            tracked["original_exstyle"] = original_exstyle
            self._hidden_windows[hwnd] = tracked
            hidden.append(tracked)

        if not hidden:
            if pid is not None:
                return f"Failed to hide windows for PID {pid}."
            return f"Failed to hide any matching windows for '{query}'."

        lines = []
        lines.extend([f"- hidden: {h['process_name'] or 'Unknown'}: {h['title']}" for h in hidden])
        return "App window visibility updated:\n" + "\n".join(lines)

    def show_app(self, query=None, pid=None):
        if not self._hidden_windows:
            return "No hidden app windows to restore."

        items = list(self._hidden_windows.items())
        restored = []
        q = str(query or "").strip().lower()
        pid_filter = None
        if pid is not None:
            try:
                pid_filter = int(pid)
            except Exception:
                return f"Invalid PID: {pid}"

        for hwnd, meta in items:
            title = str(meta.get("title", ""))
            pname = str(meta.get("process_name", ""))
            mpid = int(meta.get("pid", -1))
            if pid_filter is not None and mpid != pid_filter:
                continue
            if q and q not in title.lower() and q not in pname.lower():
                continue
            if not self._user32.IsWindow(hwnd):
                self._hidden_windows.pop(hwnd, None)
                continue
            self._restore_taskbar_style(hwnd, meta.get("original_exstyle"))
            self._user32.ShowWindow(hwnd, self._SW_RESTORE)
            self._user32.ShowWindow(hwnd, self._SW_SHOW)
            self._hidden_windows.pop(hwnd, None)
            restored.append(meta)

        if not restored:
            if pid_filter is not None:
                return f"No hidden apps matched PID {pid_filter}."
            return f"No hidden apps matched '{query}'."

        lines = [f"- {r.get('process_name') or 'Unknown'}: {r.get('title', '')}" for r in restored]
        return "Restored app windows:\n" + "\n".join(lines)

    def list_hidden_apps(self):
        if not self._hidden_windows:
            return "No hidden app windows."
        lines = []
        for meta in self._hidden_windows.values():
            lines.append(f"- {meta.get('process_name') or 'Unknown'}: {meta.get('title', '')}")
        return "Hidden app windows:\n" + "\n".join(lines)

