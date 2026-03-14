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
