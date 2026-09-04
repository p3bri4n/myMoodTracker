"""Liste de tâches partagée : toujours visible des deux profils, pas de visibilité."""

from __future__ import annotations

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Request

from app import auth, db
from app.rendering import render

router = APIRouter()


@router.get("/tasks")
def list_tasks(
    request: Request,
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Page des tâches partagées (ou fragment de rafraîchissement si appelé en HTMX)."""
    tasks = db.list_tasks(conn)
    users_by_id = db.list_users_by_id(conn)
    if request.headers.get("hx-request"):
        return render(
            request,
            "partials/task_list.html",
            {"tasks": tasks, "users_by_id": users_by_id},
            user=user,
        )
    return render(
        request,
        "tasks.html",
        {"tasks": tasks, "users": db.list_users(conn), "users_by_id": users_by_id},
        user=user,
    )


@router.post("/tasks")
def create_task(
    request: Request,
    label: str = Form(...),
    assigned_to: str = Form(""),
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Crée une tâche partagée, assignée à un profil ou à personne en particulier ('les deux')."""
    entry = db.create_task(conn, label, int(assigned_to) if assigned_to else None)
    return render(
        request,
        "partials/task_row.html",
        {"entry": entry, "users_by_id": db.list_users_by_id(conn)},
        user=user,
    )


@router.patch("/tasks/{task_id}")
def update_task(
    request: Request,
    task_id: int,
    status: Literal["todo", "done"] = Form(...),
    assigned_to: str = Form(""),
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Met à jour le statut et/ou l'assignation d'une tâche."""
    entry = db.update_task(conn, task_id, status, int(assigned_to) if assigned_to else None)
    if entry is None:
        raise HTTPException(status_code=404)
    return render(
        request,
        "partials/task_row.html",
        {"entry": entry, "users_by_id": db.list_users_by_id(conn)},
        user=user,
    )
