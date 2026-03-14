"""
Windows notification system for lifelog.
- Checks app time limits every 60s, sends alert when first exceeded
- Sends daily summary at 21:00
"""
import threading
import time
import logging
from datetime import datetime, date

log = logging.getLogger(__name__)

# Track which limits have already been notified today
_notified: set = set()
_notified_date: date | None = None


def _notify(title: str, message: str):
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="lifelog",
            timeout=10,
        )
    except Exception as e:
        log.warning("Notification failed: %s", e)


def check_limits():
    global _notified, _notified_date
    import db
    import categories

    today = date.today()
    if _notified_date != today:
        _notified = set()
        _notified_date = today

    lims = categories.limits()
    if not lims:
        return

    summary = db.get_summary(today.isoformat())
    for item in summary:
        app = item["app_name"]
        total = item["total_s"]
        for pattern, limit_s in lims.items():
            key = f"{app}:{pattern}"
            if key in _notified:
                continue
            if pattern.lower() in app.lower() and total >= limit_s:
                mins = limit_s // 60
                _notify(
                    "lifelog - 時間制限",
                    f"{app} の使用時間が {mins}分 を超えました\n本日: {total // 60}分",
                )
                _notified.add(key)


def send_daily_summary():
    import db
    import categories

    today = date.today().isoformat()
    summary = db.get_summary(today)
    if not summary:
        return

    total_s = sum(s["total_s"] for s in summary)
    total_h = total_s // 3600
    total_m = (total_s % 3600) // 60

    cat_totals: dict[str, int] = {}
    for s in summary:
        cat = categories.classify(s["app_name"], None)
        cat_totals[cat] = cat_totals.get(cat, 0) + s["total_s"]

    top_cat = max(cat_totals, key=cat_totals.get) if cat_totals else "other"
    top_label = categories.label(top_cat)
    top_s = cat_totals.get(top_cat, 0)
    top_m = top_s // 60

    _notify(
        "lifelog - 本日のまとめ",
        f"合計: {total_h}時間{total_m}分\n最多: {top_label} ({top_m}分)",
    )


def _scheduler_loop():
    daily_sent_date: date | None = None

    while True:
        try:
            now = datetime.now()
            check_limits()

            today = now.date()
            if now.hour == 21 and now.minute == 0 and daily_sent_date != today:
                send_daily_summary()
                daily_sent_date = today

        except Exception as e:
            log.error("Notifier error: %s", e)

        time.sleep(60)


def start():
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="notifier")
    t.start()
    log.info("Notifier started")
