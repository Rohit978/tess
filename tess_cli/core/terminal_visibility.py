import ctypes
import ctypes.wintypes
import threading

from .logger import setup_logger

logger = setup_logger("TerminalVisibility")


class TerminalVisibilityController:
    """
    Global hotkey toggle for TESS terminal window visibility.
    Default hotkey: Ctrl + Shift + H
    """

    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    VK_H = 0x48

    SW_HIDE = 0
    SW_SHOW = 5
    SW_RESTORE = 9

    def __init__(self, hotkey_id=0xBEEF):
        self.hotkey_id = int(hotkey_id)
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self._hwnd = self._kernel32.GetConsoleWindow()
        self._thread = None
        self._thread_id = 0
        self._running = False
        self._hidden = False

    def _register(self):
        return bool(
            self._user32.RegisterHotKey(
                None,
                self.hotkey_id,
                self.MOD_CONTROL | self.MOD_SHIFT,
                self.VK_H,
            )
        )

    def _unregister(self):
        try:
            self._user32.UnregisterHotKey(None, self.hotkey_id)
        except Exception:
            pass

    def hide(self):
        if not self._hwnd:
            return "Terminal window handle not found."
        self._user32.ShowWindow(self._hwnd, self.SW_HIDE)
        self._hidden = True
        return "TESS terminal hidden."

    def show(self):
        if not self._hwnd:
            return "Terminal window handle not found."
        self._user32.ShowWindow(self._hwnd, self.SW_RESTORE)
        self._user32.ShowWindow(self._hwnd, self.SW_SHOW)
        self._user32.SetForegroundWindow(self._hwnd)
        self._hidden = False
        return "TESS terminal visible."

    def toggle(self):
        return self.show() if self._hidden else self.hide()

    def _loop(self):
        self._thread_id = int(self._kernel32.GetCurrentThreadId())
        if not self._register():
            logger.warning("Could not register hotkey Ctrl+Shift+H.")
            self._running = False
            return

        self._running = True
        msg = ctypes.wintypes.MSG()  # type: ignore[attr-defined]
        while self._running and self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == self.WM_HOTKEY and msg.wParam == self.hotkey_id:
                self.toggle()
            self._user32.TranslateMessage(ctypes.byref(msg))
            self._user32.DispatchMessageW(ctypes.byref(msg))

        self._unregister()
        self._running = False

    def start(self):
        if self._running:
            return "Terminal visibility hotkey already active."
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return "Terminal visibility hotkey active: Ctrl+Shift+H"

    def stop(self):
        self._running = False
        if self._thread_id:
            try:
                self._user32.PostThreadMessageW(self._thread_id, self.WM_QUIT, 0, 0)
            except Exception:
                pass
        self._unregister()
        return "Terminal visibility hotkey stopped."

