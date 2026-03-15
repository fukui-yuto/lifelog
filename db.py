import sqlite3
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).parent / "data" / "lifelog.db"


def _connect(read_only=False):
    if read_only:
        uri = DB_PATH.as_uri() + "?mode=ro"
        return sqlite3.connect(uri, uri=True, check_same_thread=False)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    con = _connect()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at  TEXT NOT NULL,
            ended_at    TEXT NOT NULL,
            app_name    TEXT NOT NULL,
            win_title   TEXT NOT NULL,
            url         TEXT,
            idle        INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
        CREATE INDEX IF NOT EXISTS idx_sessions_started_idle ON sessions(started_at, idle);
    """)
    con.commit()
    con.close()


def insert_session(app_name: str, win_title: str, url: str | None,
                   idle: bool, started_at: str) -> int:
    con = _connect()
    cur = con.execute(
        "INSERT INTO sessions (started_at, ended_at, app_name, win_title, url, idle) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (started_at, started_at, app_name, win_title, url, int(idle)),
    )
    row_id = cur.lastrowid
    con.commit()
    con.close()
    return row_id


def update_session_end(row_id: int, ended_at: str):
    con = _connect()
    con.execute("UPDATE sessions SET ended_at=? WHERE id=?", (ended_at, row_id))
    con.commit()
    con.close()


def get_sessions(target_date: str) -> list[dict]:
    con = _connect(read_only=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM sessions WHERE date(started_at) = ? ORDER BY started_at",
        (target_date,),
    ).fetchall()
    con.close()

    result = []
    for r in rows:
        from datetime import datetime
        fmt = "%Y-%m-%dT%H:%M:%S"
        try:
            start = datetime.fromisoformat(r["started_at"])
            end = datetime.fromisoformat(r["ended_at"])
            duration = max(1, int((end - start).total_seconds()))
        except Exception:
            duration = 0
        result.append({
            "id":          r["id"],
            "started_at":  r["started_at"],
            "ended_at":    r["ended_at"],
            "app_name":    r["app_name"],
            "win_title":   r["win_title"],
            "url":         r["url"],
            "idle":        bool(r["idle"]),
            "duration_s":  duration,
        })
    return result


def get_summary(target_date: str) -> list[dict]:
    con = _connect(read_only=True)
    rows = con.execute("""
        SELECT app_name,
               SUM(
                 CAST((julianday(ended_at) - julianday(started_at)) * 86400 AS INTEGER)
               ) AS total_s
        FROM sessions
        WHERE date(started_at) = ?
        GROUP BY app_name
        ORDER BY total_s DESC
    """, (target_date,)).fetchall()
    con.close()
    return [{"app_name": r[0], "total_s": max(1, r[1] or 0)} for r in rows]


def get_days() -> list[str]:
    con = _connect(read_only=True)
    rows = con.execute(
        "SELECT DISTINCT date(started_at) AS d FROM sessions ORDER BY d DESC"
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def get_sessions_range(start_date: str, end_date: str) -> list[dict]:
    from datetime import datetime
    con = _connect(read_only=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM sessions WHERE date(started_at) BETWEEN ? AND ? ORDER BY started_at",
        (start_date, end_date),
    ).fetchall()
    con.close()
    result = []
    for r in rows:
        try:
            start = datetime.fromisoformat(r["started_at"])
            end = datetime.fromisoformat(r["ended_at"])
            duration = max(1, int((end - start).total_seconds()))
        except Exception:
            duration = 0
        result.append({
            "id":         r["id"],
            "date":       r["started_at"][:10],
            "started_at": r["started_at"],
            "ended_at":   r["ended_at"],
            "app_name":   r["app_name"],
            "win_title":  r["win_title"],
            "url":        r["url"],
            "idle":       bool(r["idle"]),
            "duration_s": duration,
        })
    return result


def get_summary_range(start_date: str, end_date: str) -> list[dict]:
    con = _connect(read_only=True)
    rows = con.execute("""
        SELECT date(started_at) AS d, app_name,
               SUM(CAST((julianday(ended_at) - julianday(started_at)) * 86400 AS INTEGER)) AS total_s
        FROM sessions
        WHERE date(started_at) BETWEEN ? AND ?
          AND idle = 0
        GROUP BY d, app_name
        ORDER BY d, total_s DESC
    """, (start_date, end_date)).fetchall()
    con.close()
    return [{"date": r[0], "app_name": r[1], "total_s": max(1, r[2] or 0)} for r in rows]


def get_heatmap_data(start_date: str, end_date: str) -> list[dict]:
    con = _connect(read_only=True)
    rows = con.execute("""
        SELECT date(started_at) AS d,
               SUM(CAST((julianday(ended_at) - julianday(started_at)) * 86400 AS INTEGER)) AS total_s
        FROM sessions
        WHERE date(started_at) BETWEEN ? AND ?
          AND idle = 0
        GROUP BY d
        ORDER BY d
    """, (start_date, end_date)).fetchall()
    con.close()
    return [{"date": r[0], "total_s": max(0, r[1] or 0)} for r in rows]


def get_hourly(target_date: str) -> list[dict]:
    """Returns per-hour (app_name, url, total_s) for the given date, active sessions only."""
    con = _connect(read_only=True)
    rows = con.execute("""
        SELECT
            CAST(strftime('%H', started_at) AS INTEGER) AS hour,
            app_name, url,
            SUM(CAST((julianday(ended_at) - julianday(started_at)) * 86400 AS INTEGER)) AS total_s
        FROM sessions
        WHERE date(started_at) = ? AND idle = 0
        GROUP BY hour, app_name, url
        ORDER BY hour
    """, (target_date,)).fetchall()
    con.close()
    return [{"hour": r[0], "app_name": r[1], "url": r[2], "total_s": max(1, r[3] or 0)} for r in rows]


def get_monthly(year_month: str) -> list[dict]:
    """Returns daily (date, app_name, url, total_s) for the given month (YYYY-MM)."""
    con = _connect(read_only=True)
    rows = con.execute("""
        SELECT date(started_at) AS d, app_name, url,
               SUM(CAST((julianday(ended_at) - julianday(started_at)) * 86400 AS INTEGER)) AS total_s
        FROM sessions
        WHERE strftime('%Y-%m', started_at) = ? AND idle = 0
        GROUP BY d, app_name, url
        ORDER BY d
    """, (year_month,)).fetchall()
    con.close()
    return [{"date": r[0], "app_name": r[1], "url": r[2], "total_s": max(1, r[3] or 0)} for r in rows]


def get_all_daily_totals() -> list[dict]:
    """Returns (date, app_name, url, total_s) grouped by day for streak/trend calculations.
    Limited to last 730 days to keep performance fast."""
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=730)).isoformat()
    con = _connect(read_only=True)
    rows = con.execute("""
        SELECT date(started_at) AS d, app_name, url,
               SUM(CAST((julianday(ended_at) - julianday(started_at)) * 86400 AS INTEGER)) AS total_s
        FROM sessions
        WHERE date(started_at) >= ? AND idle = 0
        GROUP BY d, app_name, url
        ORDER BY d
    """, (cutoff,)).fetchall()
    con.close()
    return [{"date": r[0], "app_name": r[1], "url": r[2], "total_s": max(1, r[3] or 0)} for r in rows]


def get_ranking(target_date: str, limit: int = 10) -> list[dict]:
    con = _connect(read_only=True)
    rows = con.execute("""
        SELECT app_name, url,
               SUM(CAST((julianday(ended_at) - julianday(started_at)) * 86400 AS INTEGER)) AS total_s
        FROM sessions
        WHERE date(started_at) = ? AND idle = 0
        GROUP BY app_name, url
        ORDER BY total_s DESC
        LIMIT ?
    """, (target_date, limit)).fetchall()
    con.close()
    return [{"app_name": r[0], "url": r[1], "total_s": max(1, r[2] or 0)} for r in rows]
