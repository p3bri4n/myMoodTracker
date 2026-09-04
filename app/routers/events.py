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
    emotion_id: int | None = Form(None),
    intensity: int | None = Form(None, ge=0, le=10),
    thoughts: str | None = Form(None),
    physiological_reactions: str | None = Form(None),
    behavior: str | None = Form(None),
    consequences: str | None = Form(None),
    needs: list[int] = Form([]),
    caused_by_event_id: int | None = Form(None),
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Ajoute un événement : entrée simple si positif, grille d'analyse si négatif."""
    if caused_by_event_id is not None:
        cause = db.get_event_if_visible(conn, caused_by_event_id, user.id)
        if cause is None or cause["user_id"] != user.id:
            raise HTTPException(
                status_code=422, detail="caused_by_event_id must reference one of your own events"
            )
    if emotion_id is not None and db.get_emotion_by_id(conn, emotion_id) is None:
        raise HTTPException(status_code=422, detail="emotion_id does not reference a known emotion")

    if type == "positive":
        if not description:
            raise HTTPException(status_code=422, detail="description is required for positive events")
        grid_fields = dict(
            trigger=None,
            aggravating_factors=None,
            first_signs=None,
            intensity=None,
            thoughts=None,
            physiological_reactions=None,
            behavior=None,
            consequences=None,
        )
    else:
        if not trigger or emotion_id is None or intensity is None:
            raise HTTPException(
                status_code=422,
                detail="trigger, emotion_id and intensity are required for negative events",
            )
        grid_fields = dict(
            trigger=trigger,
            aggravating_factors=aggravating_factors,
            first_signs=first_signs,
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
        caused_by_event_id=caused_by_event_id,
        emotion_id=emotion_id,
        **grid_fields,
    )
    db.replace_needs(conn, "event", entry["id"], needs)
    return render(
        request,
        "partials/event_row.html",
        db.build_event_view(conn, entry, user.id),
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
    entries = [db.build_event_view(conn, row, user.id) for row in rows]
    return render(request, "partials/event_list.html", {"entries": entries}, user=user)


@router.get("/emotions")
def emotion_options(
    request: Request,
    core: str | None = None,
    secondary: str | None = None,
    form_id: str = "default",
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Étape suivante de la roue des émotions : cores, puis secondaires, puis spécifiques."""
    if core and secondary:
        specifics = db.list_emotion_specifics(conn, core, secondary)
        return render(
            request,
            "partials/emotion_specific_options.html",
            {"core": core, "secondary": secondary, "specifics": specifics, "form_id": form_id},
            user=user,
        )
    if core:
        secondaries = db.list_emotion_secondaries(conn, core)
        return render(
            request,
            "partials/emotion_secondary_options.html",
            {"core": core, "secondaries": secondaries, "form_id": form_id},
            user=user,
        )
    cores = db.list_emotion_cores(conn)
    return render(
        request,
        "partials/emotion_core_options.html",
        {"cores": cores, "form_id": form_id},
        user=user,
    )


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
