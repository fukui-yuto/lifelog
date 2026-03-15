"""
PC activity tracker - run this as a background process.
Polls the active window every second and writes sessions to lifelog.db.
"""

import ctypes
import http.client
import json
import os
import time
import sys
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

import psutil
import win32gui
import win32process

import db

# -------------------------------------------------------------------
# Single-instance lock
# -------------------------------------------------------------------
LOCK_PATH = Path(__file__).parent / "data" / "tracker.lock"

_lock_fd = None

def _acquire_lock() -> bool:
    """Return True if this process acquired the lock, False if another instance is running."""
    global _lock_fd
    try:
        import msvcrt
        _lock_fd = open(LOCK_PATH, "w")
        msvcrt.locking(_lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
        _lock_fd.write(str(os.getpid()))
        _lock_fd.flush()
        return True
    except OSError:
        if _lock_fd:
            _lock_fd.close()
            _lock_fd = None
        return False

def _release_lock():
    global _lock_fd
    try:
        if _lock_fd:
            import msvcrt
            msvcrt.locking(_lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
            _lock_fd.close()
            _lock_fd = None
        LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------
POLL_INTERVAL = 1.0        # seconds
IDLE_THRESHOLD = 300       # seconds of no input = idle
BROWSER_EXES = {"chrome.exe", "msedge.exe", "firefox.exe"}
URL_TIMEOUT   = 0.3        # seconds to wait for uiautomation URL lookup

LOG_PATH = Path(__file__).parent / "data" / "tracker.log"
LOG_PATH.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [tracker] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Windows helpers
# -------------------------------------------------------------------
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds() -> float:
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(lii)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return millis / 1000.0


def _get_window_title(hwnd: int) -> str:
    """Get window title as proper Unicode string using GetWindowTextW directly."""
    buf = ctypes.create_unicode_buffer(512)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def get_active_window() -> tuple[str, str]:
    """Returns (app_exe_name, window_title). Falls back to empty strings on error."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "(desktop)", ""
        title = _get_window_title(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            app = psutil.Process(pid).name().lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            app = "(unknown)"
        return app, title
    except Exception as e:
        log.debug("get_active_window error: %s", e)
        return "(error)", ""


# Persistent HTTP connections for Chrome DevTools Protocol (reused each poll cycle)
_cdp_conns: dict[int, http.client.HTTPConnection | None] = {}


def _fetch_cdp_tabs(port: int) -> list | None:
    """Fetch tab list from Chrome DevTools using a persistent HTTP connection."""
    conn = _cdp_conns.get(port)
    try:
        if conn is None:
            conn = http.client.HTTPConnection("localhost", port, timeout=URL_TIMEOUT)
            _cdp_conns[port] = conn
        conn.request("GET", "/json")
        resp = conn.getresponse()
        body = resp.read()
        return json.loads(body)
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        _cdp_conns[port] = None
        return None


def get_browser_url(app_name: str, win_title: str) -> str | None:
    """Get active tab URL via Chrome DevTools Protocol (CDP).
    Matches window title against tab titles to find the correct tab.
    Requires Chrome/Edge launched with --remote-debugging-port=9222.
    """
    if app_name not in BROWSER_EXES:
        return None

    # ウィンドウタイトルからブラウザ名のサフィックスを除去
    SUFFIXES = [" - Google Chrome", " - Microsoft Edge", " - Mozilla Firefox"]
    page_title = win_title
    for suffix in SUFFIXES:
        if win_title.endswith(suffix):
            page_title = win_title[:-len(suffix)]
            break

    ports = [9222, 9223]  # Chrome=9222, Edge=9223
    for port in ports:
        tabs = _fetch_cdp_tabs(port)
        if tabs is None:
            continue
        pages = [t for t in tabs if t.get("type") == "page"]

        # タイトル完全一致で検索
        for tab in pages:
            if tab.get("title", "") == page_title:
                url = tab.get("url", "")
                if url.startswith("http"):
                    return url

        # 完全一致なければ部分一致で検索
        for tab in pages:
            if page_title and page_title.lower() in tab.get("title", "").lower():
                url = tab.get("url", "")
                if url.startswith("http"):
                    return url

    return None


# -------------------------------------------------------------------
# Session state
# -------------------------------------------------------------------
class Session:
    __slots__ = ("row_id", "app_name", "win_title", "url", "idle")

    def __init__(self, row_id, app_name, win_title, url, idle):
        self.row_id    = row_id
        self.app_name  = app_name
        self.win_title = win_title
        self.url       = url
        self.idle      = idle

    def matches(self, app_name, win_title, url, idle) -> bool:
        return (
            self.app_name  == app_name  and
            self.win_title == win_title and
            self.url       == url       and
            self.idle      == idle
        )


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# -------------------------------------------------------------------
# Main loop
# -------------------------------------------------------------------
def main():
    if not _acquire_lock():
        print("Another tracker instance is already running. Exiting.")
        sys.exit(0)
    try:
        _run()
    finally:
        _release_lock()


def _run():
    db.init_db()
    import notifier
    import backup
    notifier.start()
    backup.start()
    log.info("Tracker started. Press Ctrl+C to stop.")

    current: Session | None = None

    while True:
        try:
            tick_start = time.monotonic()

            app_name, win_title = get_active_window()
            idle = get_idle_seconds() >= IDLE_THRESHOLD
            url = get_browser_url(app_name, win_title) if not idle else None
            ts  = now_iso()

            if current is None or not current.matches(app_name, win_title, url, idle):
                # Start a new session
                row_id = db.insert_session(app_name, win_title, url, idle, ts)
                current = Session(row_id, app_name, win_title, url, idle)
                log.info("New session: [%s] %s%s",
                         app_name, win_title[:60],
                         f" ({url[:50]})" if url else "")
            else:
                # Extend the current session
                db.update_session_end(current.row_id, ts)

            elapsed = time.monotonic() - tick_start
            sleep_for = max(0.0, POLL_INTERVAL - elapsed)
            time.sleep(sleep_for)

        except KeyboardInterrupt:
            log.info("Tracker stopped.")
            sys.exit(0)
        except Exception as e:
            log.error("Unexpected error: %s", e, exc_info=True)
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
