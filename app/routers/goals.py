"""Objectifs quotidiens : liste à cocher + taux de complétion."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Request

from app import auth, db
from app.rendering import render

router = APIRouter()


@router.post("/goals")
def create_goal(
    request: Request,
    label: str = Form(...),
    visibility: Literal["private", "public"] = Form("private"),
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Ajoute un objectif pour aujourd'hui."""
    today = date.today().isoformat()
    entry = db.create_goal(conn, user.id, today, label, visibility)
    return render(request, "partials/goal_item.html", {"entry": entry}, user=user)


@router.patch("/goals/{goal_id}")
def toggle_goal(
    request: Request,
    goal_id: int,
    done: bool = Form(...),
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Coche/décoche un objectif de l'utilisateur courant."""
    entry = db.set_goal_done(conn, goal_id, user.id, done)
    if entry is None:
        raise HTTPException(status_code=404)
    return render(request, "partials/goal_item.html", {"entry": entry}, user=user)
