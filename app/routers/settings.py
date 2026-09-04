"""Paramètres du profil : langue de l'interface."""

from __future__ import annotations

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Form, Request

from app import auth, db
from app.i18n import SUPPORTED_LANGUAGES
from app.rendering import render

router = APIRouter()


@router.get("/settings")
def settings_page(request: Request, user: db.User = Depends(auth.get_current_user)):
    """Page de paramètres : sélecteur de langue de l'interface."""
    return render(request, "settings.html", {}, user=user)


@router.patch("/settings/language")
def update_language(
    request: Request,
    language: Literal[SUPPORTED_LANGUAGES] = Form(...),
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Change la langue d'interface du profil connecté."""
    db.set_user_language(conn, user.id, language)
    user.language = language
    return render(request, "partials/language_form.html", {}, user=user)
