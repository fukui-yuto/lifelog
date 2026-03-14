import sqlite3
from pathlib import Path
from collections import Counter

con = sqlite3.connect(Path(__file__).parent.parent / "data" / "lifelog.db")
rows = con.execute(
    "SELECT id, started_at, app_name, win_title, url FROM sessions WHERE date(started_at)='2026-03-14' AND idle=0"
).fetchall()
con.close()

dups = [(k, v) for k, v in Counter(r[1] for r in rows).items() if v > 1]
print(f"重複 started_at: {len(dups)}件")
for ts, count in sorted(dups):
    entries = [r for r in rows if r[1] == ts]
    print(f"\n{ts} ({count}件):")
    for r in entries:
        print(f"  id={r[0]} app={r[2][:15]} title={r[3][:20]} url={str(r[4])[:30]}")
