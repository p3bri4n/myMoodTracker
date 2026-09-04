"""Objectifs quotidiens : liste à cocher, édition/suppression par le propriétaire."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response

from app import auth, db
from app.rendering import render

router = APIRouter()


def _goal_context(conn: sqlite3.Connection, entry: sqlite3.Row) -> dict:
    return {"entry": entry, "users_by_id": db.list_users_by_id(conn)}


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
    return render(request, "partials/goal_item.html", _goal_context(conn, entry), user=user)


@router.get("/goals/{goal_id}")
def view_goal(
    request: Request,
    goal_id: int,
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Réaffiche un objectif en mode lecture (utilisé pour annuler une édition)."""
    entry = db.get_goal_if_visible(conn, goal_id, user.id)
    if entry is None:
        raise HTTPException(status_code=404)
    return render(request, "partials/goal_item.html", _goal_context(conn, entry), user=user)


@router.get("/goals/{goal_id}/edit")
def edit_goal_form(
    request: Request,
    goal_id: int,
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Affiche le formulaire d'édition inline, réservé au propriétaire."""
    entry = db.get_goal_if_visible(conn, goal_id, user.id)
    if entry is None or entry["user_id"] != user.id:
        raise HTTPException(status_code=404)
    return render(request, "partials/goal_item_edit.html", {"entry": entry}, user=user)


@router.patch("/goals/{goal_id}")
def update_goal(
    request: Request,
    goal_id: int,
    label: str | None = Form(None),
    done: bool | None = Form(None),
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Coche/décoche et/ou renomme un objectif de l'utilisateur courant."""
    entry = db.update_goal(conn, goal_id, user.id, label=label, done=done)
    if entry is None:
        raise HTTPException(status_code=404)
    return render(request, "partials/goal_item.html", _goal_context(conn, entry), user=user)


@router.delete("/goals/{goal_id}")
def delete_goal(
    goal_id: int,
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Supprime un objectif de l'utilisateur courant."""
    deleted = db.delete_goal(conn, goal_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404)
    return Response(status_code=204)
