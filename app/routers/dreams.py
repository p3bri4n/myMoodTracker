"""Journal de rêves : entrée optionnelle par jour."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Form, Request

from app import auth, db
from app.rendering import render

router = APIRouter()


@router.post("/dreams")
def create_dream(
    request: Request,
    content: str = Form(...),
    tag: Literal["pleasant", "neutral", "nightmare", ""] = Form(""),
    visibility: Literal["private", "public"] = Form("private"),
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Ajoute un rêve pour aujourd'hui."""
    today = date.today().isoformat()
    entry = db.create_dream(conn, user.id, today, content, tag or None, visibility)
    return render(request, "partials/dream_card.html", {"entry": entry}, user=user)
