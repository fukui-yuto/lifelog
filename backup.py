"""
Weekly database backup.
Copies lifelog.db to data/backups/ every Sunday at 03:00.
Keeps the last MAX_BACKUPS copies.
"""
import shutil
import threading
import time
import logging
from datetime import datetime, date
from pathlib import Path

import db

BACKUP_DIR = db.DB_PATH.parent / "backups"
MAX_BACKUPS = 7

log = logging.getLogger(__name__)


def do_backup():
    BACKUP_DIR.mkdir(exist_ok=True)
    if not db.DB_PATH.exists():
        log.warning("DB not found, skipping backup")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    dest = BACKUP_DIR / f"lifelog_{stamp}.db"
    shutil.copy2(db.DB_PATH, dest)
    log.info("Backup created: %s", dest)

    backups = sorted(BACKUP_DIR.glob("lifelog_*.db"))
    for old in backups[:-MAX_BACKUPS]:
        old.unlink()
        log.info("Old backup removed: %s", old)


def _scheduler_loop():
    last_backup_date: date | None = None

    while True:
        try:
            now = datetime.now()
            if now.weekday() == 6 and now.hour == 3 and last_backup_date != now.date():
                do_backup()
                last_backup_date = now.date()
        except Exception as e:
            log.error("Backup error: %s", e)

        time.sleep(3600)


def start():
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="backup")
    t.start()
    log.info("Backup scheduler started")
