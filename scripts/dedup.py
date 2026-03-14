import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "lifelog.db"
con = sqlite3.connect(DB_PATH)

before = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

# URLが違っても同じ started_at + app_name + idle の重複を削除
# URLがある方(非NULL)を優先して残す
con.execute("""
    DELETE FROM sessions
    WHERE id NOT IN (
        SELECT id FROM (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY app_name, started_at, idle
                       ORDER BY CASE WHEN url IS NOT NULL THEN 0 ELSE 1 END, id
                   ) AS rn
            FROM sessions
        ) ranked
        WHERE rn = 1
    )
""")
con.commit()

after = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
con.close()
print(f"削除前: {before}件 → 削除後: {after}件 ({before - after}件削除)")
