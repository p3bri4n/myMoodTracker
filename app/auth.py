"""Hash des mots de passe et résolution de l'utilisateur courant depuis la session."""

from __future__ import annotations

import os
import secrets
import sqlite3
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from passlib.hash import bcrypt

from app import db

SECRET_KEY_PATH = Path("db/.secret_key")


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.verify(password, password_hash)


def get_session_secret() -> str:
    """Clé de session : variable d'env, sinon générée une fois et persistée."""
    env_secret = os.environ.get("SECRET_KEY")
    if env_secret:
        return env_secret
    SECRET_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SECRET_KEY_PATH.exists():
        return SECRET_KEY_PATH.read_text().strip()
    secret = secrets.token_hex(32)
    SECRET_KEY_PATH.write_text(secret)
    return secret


def get_current_user(
    request: Request, conn: sqlite3.Connection = Depends(db.get_db)
) -> db.User:
    """Résout l'utilisateur connecté depuis la session — jamais depuis un id client."""
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.get_user_by_id(conn, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
