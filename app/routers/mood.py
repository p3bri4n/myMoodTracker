"""Humeur du jour : une entrée par utilisateur et par jour (upsert)."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Form, Request

from app import auth, db
from app.rendering import render

router = APIRouter()


@router.post("/mood")
def upsert_mood(
    request: Request,
    physical_fatigue: int = Form(..., ge=1, le=10),
    mental_fatigue: int = Form(..., ge=1, le=10),
    mood: int = Form(..., ge=1, le=10),
    social_need: int = Form(..., ge=1, le=10),
    stress: int = Form(..., ge=1, le=10),
    sleep_quality: int = Form(..., ge=1, le=10),
    note: str | None = Form(None),
    visibility: Literal["private", "public"] = Form("private"),
    needs: list[int] = Form([]),
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Crée ou met à jour l'entrée d'humeur du jour pour l'utilisateur courant."""
    today = date.today().isoformat()
    entry = db.upsert_mood_entry(
        conn,
        user.id,
        today,
        physical_fatigue,
        mental_fatigue,
        mood,
        social_need,
        stress,
        sleep_quality,
        note,
        visibility,
    )
    db.replace_needs(conn, "mood", entry["id"], needs)
    entry_needs = db.get_needs_for_entry(conn, "mood", entry["id"])
    return render(
        request,
        "partials/mood_card.html",
        {
            "entry": entry,
            "entry_needs": entry_needs,
            "needs_grouped": db.get_needs_grouped(conn),
        },
        user=user,
    )
