import csv
import io
import json as json_module
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import db
import categories as cats

db.init_db()

app = FastAPI(title="lifelog")

FRONTEND_DIR = Path(__file__).parent / "frontend"


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/days")
def api_days():
    return db.get_days()


@app.get("/api/sessions")
def api_sessions(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    sessions = db.get_sessions(date)
    for s in sessions:
        s["category"] = cats.classify(s["app_name"], s.get("url"))
    return sessions


@app.get("/api/summary")
def api_summary(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    summary = db.get_summary(date)
    for s in summary:
        s["category"] = cats.classify(s["app_name"], None)
    return summary


@app.get("/api/category_summary")
def api_category_summary(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    sessions = db.get_sessions(date)
    all_cats = cats.all_labels()

    cat_totals: dict[str, int] = {}
    for s in sessions:
        if s["idle"]:
            continue
        cat = cats.classify(s["app_name"], s.get("url"))
        cat_totals[cat] = cat_totals.get(cat, 0) + s["duration_s"]

    result = {}
    for cat_key, meta in all_cats.items():
        result[cat_key] = {
            "total_s": cat_totals.get(cat_key, 0),
            "label":   meta.get("label", cat_key),
            "color":   meta.get("color", "#4b607a"),
        }

    total_active = sum(cat_totals.values())
    work_s = cat_totals.get("work", 0)
    focus_score = round(work_s / total_active * 100) if total_active > 0 else 0

    return {
        "categories":    result,
        "focus_score":   focus_score,
        "total_active_s": total_active,
    }


@app.get("/api/weekly")
def api_weekly(date: str):
    try:
        d = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)

    rows = db.get_summary_range(monday.isoformat(), sunday.isoformat())
    all_cats = cats.all_labels()
    dates = [(monday + timedelta(days=i)).isoformat() for i in range(7)]

    by_date: dict[str, dict[str, int]] = {day: {} for day in dates}
    for row in rows:
        cat = cats.classify(row["app_name"], None)
        if row["date"] in by_date:
            by_date[row["date"]][cat] = by_date[row["date"]].get(cat, 0) + row["total_s"]

    return {
        "dates": dates,
        "categories": {
            cat_key: [by_date[day].get(cat_key, 0) for day in dates]
            for cat_key in all_cats
        },
        "labels": {
            k: {"label": v["label"], "color": v["color"]}
            for k, v in all_cats.items()
        },
    }


@app.get("/api/heatmap")
def api_heatmap(start: str, end: str):
    try:
        datetime.strptime(start, "%Y-%m-%d")
        datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="start/end must be YYYY-MM-DD")
    return db.get_heatmap_data(start, end)


@app.get("/api/ranking")
def api_ranking(date: str, limit: int = 10):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    rows = db.get_ranking(date, limit)
    for r in rows:
        r["category"] = cats.classify(r["app_name"], r.get("url"))
    return rows


@app.get("/api/hourly")
def api_hourly(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    rows = db.get_hourly(date)
    all_cats = cats.all_labels()

    hours: dict[int, dict[str, int]] = {h: {} for h in range(24)}
    for r in rows:
        cat = cats.classify(r["app_name"], r.get("url"))
        h = r["hour"]
        hours[h][cat] = hours[h].get(cat, 0) + r["total_s"]

    return {
        "hours": [{"hour": h, "categories": hours[h]} for h in range(24)],
        "labels": {k: {"label": v["label"], "color": v["color"]} for k, v in all_cats.items()},
    }


@app.get("/api/trend")
def api_trend(date: str, weeks: int = 12):
    try:
        d = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    end = d
    start = end - timedelta(weeks=min(weeks, 52))
    rows = db.get_summary_range(start.isoformat(), end.isoformat())
    all_cats = cats.all_labels()

    day_cats: dict[str, dict[str, int]] = {}
    for row in rows:
        day = row["date"]
        cat = cats.classify(row["app_name"], None)
        if day not in day_cats:
            day_cats[day] = {}
        day_cats[day][cat] = day_cats[day].get(cat, 0) + row["total_s"]

    dates = []
    cur = start
    while cur <= end:
        dates.append(cur.isoformat())
        cur += timedelta(days=1)

    focus_scores = []
    total_actives = []
    cat_series: dict[str, list[int]] = {k: [] for k in all_cats}
    for day in dates:
        dc = day_cats.get(day, {})
        total = sum(dc.values())
        work = dc.get("work", 0)
        focus_scores.append(round(work / total * 100) if total > 0 else None)
        total_actives.append(total)
        for k in all_cats:
            cat_series[k].append(dc.get(k, 0))

    return {
        "dates": dates,
        "focus_scores": focus_scores,
        "total_active_s": total_actives,
        "categories": cat_series,
        "labels": {k: {"label": v["label"], "color": v["color"]} for k, v in all_cats.items()},
    }


@app.get("/api/monthly")
def api_monthly(date: str):
    try:
        d = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    year_month = d.strftime("%Y-%m")
    rows = db.get_monthly(year_month)
    all_cats = cats.all_labels()

    cat_totals: dict[str, int] = {}
    day_totals: dict[str, int] = {}
    for r in rows:
        cat = cats.classify(r["app_name"], r.get("url"))
        cat_totals[cat] = cat_totals.get(cat, 0) + r["total_s"]
        day_totals[r["date"]] = day_totals.get(r["date"], 0) + r["total_s"]

    days_active = len(day_totals)
    total_s = sum(cat_totals.values())
    avg_daily_s = round(total_s / days_active) if days_active > 0 else 0
    work_s = cat_totals.get("work", 0)
    avg_focus = round(work_s / total_s * 100) if total_s > 0 else 0

    return {
        "year_month": year_month,
        "days_active": days_active,
        "total_s": total_s,
        "avg_daily_s": avg_daily_s,
        "avg_focus_score": avg_focus,
        "categories": {
            k: {"total_s": cat_totals.get(k, 0), "label": v["label"], "color": v["color"]}
            for k, v in all_cats.items()
        },
    }


@app.get("/api/streak")
def api_streak(category: str = "work", min_hours: float = 1.0):
    from datetime import date as date_cls, timedelta as td
    rows = db.get_all_daily_totals()
    min_s = int(min_hours * 3600)

    day_cats: dict[str, dict[str, int]] = {}
    for r in rows:
        day = r["date"]
        cat = cats.classify(r["app_name"], r.get("url"))
        if day not in day_cats:
            day_cats[day] = {}
        day_cats[day][cat] = day_cats[day].get(cat, 0) + r["total_s"]

    today = date_cls.today().isoformat()

    # Longest streak
    longest_streak = 0
    temp = 1
    prev_d = None
    for day in sorted(day_cats.keys()):
        achieved = day_cats[day].get(category, 0) >= min_s
        if not achieved:
            prev_d = None
            continue
        cur_d = date_cls.fromisoformat(day)
        if prev_d is not None and (cur_d - prev_d).days == 1:
            temp += 1
        else:
            temp = 1
        longest_streak = max(longest_streak, temp)
        prev_d = cur_d

    # Current streak (count backwards from today)
    today_achieved = day_cats.get(today, {}).get(category, 0) >= min_s
    current_streak = 0
    check = date_cls.today() if today_achieved else date_cls.today() - td(days=1)
    while True:
        d_str = check.isoformat()
        if day_cats.get(d_str, {}).get(category, 0) >= min_s:
            current_streak += 1
            check -= td(days=1)
        else:
            break

    return {
        "category": category,
        "min_hours": min_hours,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "today_achieved": today_achieved,
    }


@app.get("/api/export/csv")
def api_export_csv(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    sessions = db.get_sessions(date)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "started_at", "ended_at", "duration_s",
                     "app_name", "win_title", "url", "category", "idle"])
    for s in sessions:
        cat = cats.classify(s["app_name"], s.get("url"))
        writer.writerow([
            s["id"], s["started_at"], s["ended_at"], s["duration_s"],
            s["app_name"], s["win_title"], s.get("url", ""), cat, int(s["idle"]),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename=lifelog_{date}.csv"},
    )


@app.get("/api/export/json")
def api_export_json(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    sessions = db.get_sessions(date)
    for s in sessions:
        s["category"] = cats.classify(s["app_name"], s.get("url"))
    content = json_module.dumps(sessions, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=lifelog_{date}.json"},
    )
