"""Événements notables (positifs/négatifs) et référentiel des besoins fondamentaux."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Request

from app import auth, db
from app.rendering import render

router = APIRouter()


@router.post("/events")
def create_event(
    request: Request,
    type: Literal["positive", "negative"] = Form(...),
    description: str | None = Form(None),
    time: str | None = Form(None),
    visibility: Literal["private", "public"] = Form("private"),
    trigger: str | None = Form(None),
    aggravating_factors: str | None = Form(None),
    first_signs: str | None = Form(None),
    emotion: str | None = Form(None),
    intensity: int | None = Form(None, ge=0, le=10),
    thoughts: str | None = Form(None),
    physiological_reactions: str | None = Form(None),
    behavior: str | None = Form(None),
    consequences: str | None = Form(None),
    needs: list[int] = Form([]),
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Ajoute un événement : entrée simple si positif, grille d'analyse si négatif."""
    if type == "positive":
        if not description:
            raise HTTPException(status_code=422, detail="description is required for positive events")
        grid_fields = dict(
            trigger=None,
            aggravating_factors=None,
            first_signs=None,
            emotion=None,
            intensity=None,
            thoughts=None,
            physiological_reactions=None,
            behavior=None,
            consequences=None,
        )
    else:
        if not trigger or not emotion or intensity is None:
            raise HTTPException(
                status_code=422,
                detail="trigger, emotion and intensity are required for negative events",
            )
        grid_fields = dict(
            trigger=trigger,
            aggravating_factors=aggravating_factors,
            first_signs=first_signs,
            emotion=emotion,
            intensity=intensity,
            thoughts=thoughts,
            physiological_reactions=physiological_reactions,
            behavior=behavior,
            consequences=consequences,
        )

    entry = db.create_event(
        conn,
        user_id=user.id,
        date=date.today().isoformat(),
        time=time or None,
        type=type,
        description=description,
        visibility=visibility,
        **grid_fields,
    )
    db.replace_needs(conn, "event", entry["id"], needs)
    entry_needs = db.get_needs_for_entry(conn, "event", entry["id"])
    return render(
        request,
        "partials/event_row.html",
        {"entry": entry, "entry_needs": entry_needs},
        user=user,
    )


@router.get("/events")
def list_events(
    request: Request,
    date: str,
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Liste mes événements du jour + les événements publics du partenaire."""
    rows = db.list_visible_for_date(conn, "events", date, user.id)
    entries = [
        {"entry": row, "entry_needs": db.get_needs_for_entry(conn, "event", row["id"])}
        for row in rows
    ]
    return render(request, "partials/event_list.html", {"entries": entries}, user=user)


@router.get("/needs")
def list_needs(
    request: Request,
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Liste le référentiel des besoins fondamentaux, groupés par catégorie."""
    needs_grouped = db.get_needs_grouped(conn)
    return render(
        request, "partials/needs_select.html", {"needs_grouped": needs_grouped}, user=user
    )
