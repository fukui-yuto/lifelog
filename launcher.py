"""
lifelog launcher - system tray app
Double-click to start. Right-click tray icon to open/stop/exit.
"""
import subprocess
import sys
import time
import threading
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).parent
VENV_PYTHON = Path(sys.executable)
LOCK_PATH = BASE_DIR / "data" / "tracker.lock"

_procs: list[subprocess.Popen] = []


# ── icon ──────────────────────────────────────────────────────────
def _make_icon(color: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=color)
    # simple "L" mark
    d.rectangle([18, 16, 26, 48], fill="white")
    d.rectangle([18, 40, 44, 48], fill="white")
    return img


ICON_GREEN  = _make_icon("#22c55e")
ICON_YELLOW = _make_icon("#f59e0b")


# ── process management ────────────────────────────────────────────
def _start_services():
    LOCK_PATH.parent.mkdir(exist_ok=True)
    LOCK_PATH.unlink(missing_ok=True)

    tracker = subprocess.Popen(
        [str(VENV_PYTHON), "tracker.py"],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    api = subprocess.Popen(
        [str(VENV_PYTHON), "-m", "uvicorn", "api:app", "--port", "8000"],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    _procs.extend([tracker, api])


def _stop_services():
    for p in _procs:
        try:
            p.terminate()
        except Exception:
            pass
    _procs.clear()
    LOCK_PATH.unlink(missing_ok=True)


def _open_browser():
    time.sleep(0.3)
    webbrowser.open("http://localhost:8000")


# ── tray menu ─────────────────────────────────────────────────────
def _on_open(icon, item):
    threading.Thread(target=_open_browser, daemon=True).start()


def _on_stop(icon, item):
    icon.icon = ICON_YELLOW
    icon.title = "lifelog - 停止中..."
    _stop_services()
    icon.icon = ICON_YELLOW
    icon.title = "lifelog - 停止"


def _on_exit(icon, item):
    _stop_services()
    icon.stop()


def main():
    _start_services()

    # open browser after a moment
    threading.Thread(target=_open_browser, daemon=True).start()

    menu = pystray.Menu(
        pystray.MenuItem("ブラウザで開く", _on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("サービス停止", _on_stop),
        pystray.MenuItem("終了", _on_exit),
    )
    icon = pystray.Icon("lifelog", ICON_GREEN, "lifelog - 動作中", menu)
    icon.run()


if __name__ == "__main__":
    main()
