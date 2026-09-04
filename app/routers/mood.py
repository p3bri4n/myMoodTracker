"""Humeur du jour : une entrée par utilisateur et par jour (upsert).

Chaque indicateur est saisi via un sélecteur à 5 visages (😢🙁😐🙂😄) plutôt
qu'un slider numérique : 1 = ressenti très négatif sur cet axe, 5 = très positif,
de façon uniforme pour les 6 indicateurs (y compris fatigue/stress, où 5 signifie
donc "peu de fatigue/stress ressenti").
"""

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
    physical_fatigue: int = Form(..., ge=1, le=5),
    mental_fatigue: int = Form(..., ge=1, le=5),
    mood: int = Form(..., ge=1, le=5),
    social_need: int = Form(..., ge=1, le=5),
    stress: int = Form(..., ge=1, le=5),
    sleep_quality: int = Form(..., ge=1, le=5),
    note: str | None = Form(None),
    visibility: Literal["private", "public"] = Form("private"),
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
    return render(request, "partials/mood_card.html", {"entry": entry}, user=user)
