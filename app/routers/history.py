"""Historique : revue d'un jour passé (mes données + données publiques du partenaire)."""

from __future__ import annotations

import sqlite3
from datetime import date as date_type

from fastapi import APIRouter, Depends, Request

from app import auth, db
from app.rendering import render

router = APIRouter()


@router.get("/history")
def show_history(
    request: Request,
    date: str | None = None,
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Affiche l'humeur, les rêves, les objectifs et les événements d'un jour donné (aujourd'hui par défaut)."""
    date = date or date_type.today().isoformat()
    mood_entries = db.list_visible_for_date(conn, "mood_entries", date, user.id)
    dreams = db.list_visible_for_date(conn, "dreams", date, user.id)
    goals = db.list_visible_for_date(conn, "daily_goals", date, user.id)
    events = db.list_visible_for_date(conn, "events", date, user.id)
    context = {
        "selected_date": date,
        "mood_entries": mood_entries,
        "dreams": dreams,
        "goals": goals,
        "users_by_id": db.list_users_by_id(conn),
        "events": [db.build_event_view(conn, row, user.id) for row in events],
    }
    return render(request, "history.html", context, user=user)
