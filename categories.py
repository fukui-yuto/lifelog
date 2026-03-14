import json
from pathlib import Path
from urllib.parse import urlparse

CATEGORIES_PATH = Path(__file__).parent / "categories.json"

DEFAULT = {
    "labels": {
        "work":    {"label": "作業",      "color": "#10b981"},
        "leisure": {"label": "娯楽",      "color": "#f43f5e"},
        "social":  {"label": "SNS/通信",  "color": "#f59e0b"},
        "browser": {"label": "ブラウザ",  "color": "#3b82f6"},
        "system":  {"label": "システム",  "color": "#64748b"},
        "other":   {"label": "その他",    "color": "#4b607a"},
    },
    "rules": [
        {
            "category": "work",
            "url_patterns": [
                "github.com", "gitlab.com", "stackoverflow.com",
                "docs.python.org", "jira.", "confluence.", "notion.so",
                "figma.com", "linear.app", "vercel.com", "aws.amazon.com",
                "developer.mozilla.org", "npmjs.com", "pypi.org",
            ],
            "app_patterns": [
                "code.exe", "code - insiders.exe", "devenv.exe",
                "pycharm", "idea", "webstorm", "rider",
                "notepad++.exe", "sublime_text.exe",
                "excel.exe", "winword.exe", "powerpnt.exe",
                "postman.exe",
            ],
        },
        {
            "category": "leisure",
            "url_patterns": [
                "youtube.com", "netflix.com", "twitch.tv",
                "nicovideo.jp", "niconico.jp", "abema.tv",
                "hulu.com", "primevideo.com", "steamcommunity.com",
                "dlsite.com",
            ],
            "app_patterns": [
                "steam.exe", "epicgameslauncher.exe",
                "discord.exe", "vlc.exe", "mpc-hc64.exe",
                "spotify.exe", "foobar2000.exe",
            ],
        },
        {
            "category": "social",
            "url_patterns": [
                "twitter.com", "x.com", "instagram.com",
                "facebook.com", "reddit.com", "linkedin.com",
                "tiktok.com", "line.me",
            ],
            "app_patterns": ["line.exe", "twitterforwindows.exe"],
        },
        {
            "category": "work",
            "url_patterns": [],
            "app_patterns": [
                "slack.exe", "teams.exe", "zoom.exe",
                "windowsterminal.exe", "powershell.exe", "cmd.exe",
            ],
        },
        {
            "category": "browser",
            "url_patterns": [],
            "app_patterns": [
                "chrome.exe", "msedge.exe", "firefox.exe",
                "brave.exe", "opera.exe",
            ],
        },
        {
            "category": "system",
            "url_patterns": [],
            "app_patterns": [
                "explorer.exe", "(desktop)", "(unknown)",
                "taskmgr.exe", "regedit.exe",
            ],
        },
    ],
    "limits": {
        "youtube.com": 3600,
        "steam.exe":   7200,
        "twitter.com": 1800,
        "x.com":       1800,
    },
}

_cache: dict | None = None
_cache_mtime: float = 0.0


def load() -> dict:
    global _cache, _cache_mtime
    if not CATEGORIES_PATH.exists():
        CATEGORIES_PATH.write_text(
            json.dumps(DEFAULT, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _cache = DEFAULT
        _cache_mtime = CATEGORIES_PATH.stat().st_mtime
        return _cache

    mtime = CATEGORIES_PATH.stat().st_mtime
    if _cache is None or mtime != _cache_mtime:
        try:
            _cache = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
            _cache_mtime = mtime
        except Exception:
            _cache = DEFAULT
    return _cache


def classify(app_name: str, url: str | None) -> str:
    cats = load()
    app_lower = (app_name or "").lower()
    domain = urlparse(url).netloc.lower().lstrip("www.") if url else ""

    for rule in cats.get("rules", []):
        cat = rule.get("category", "other")
        if domain:
            for pat in rule.get("url_patterns", []):
                if pat in domain:
                    return cat
        for pat in rule.get("app_patterns", []):
            if pat.lower() in app_lower:
                return cat
    return "other"


def label(cat_key: str) -> str:
    return load()["labels"].get(cat_key, {}).get("label", cat_key)


def color(cat_key: str) -> str:
    return load()["labels"].get(cat_key, {}).get("color", "#4b607a")


def all_labels() -> dict:
    cats = load()
    result = dict(cats.get("labels", {}))
    result.setdefault("other", {"label": "その他", "color": "#4b607a"})
    return result


def limits() -> dict:
    return load().get("limits", {})
