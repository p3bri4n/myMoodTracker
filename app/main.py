"""FastAPI app: création de l'application et enregistrement des routes."""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import auth, db, i18n
from app.rendering import render
from app.routers import dreams, events, export, goals, history, mood, settings, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise le schéma SQLite et précharge les traductions au démarrage."""
    conn = db.connect()
    db.init_db(conn)
    conn.close()
    i18n.load_translations()
    yield


app = FastAPI(title="myMoodTracker", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=auth.get_session_secret())
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/setup")
def setup_form(request: Request, conn: sqlite3.Connection = Depends(db.get_db)):
    """Formulaire de création des 2 profils, actif uniquement au premier lancement."""
    if db.count_users(conn) >= 2:
        return RedirectResponse("/", status_code=303)
    return render(request, "setup.html", {})


@app.post("/setup")
def setup_submit(
    name1: str = Form(...),
    color1: str = Form(...),
    password1: str = Form(...),
    name2: str = Form(...),
    color2: str = Form(...),
    password2: str = Form(...),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Crée les 2 profils si aucun n'existe encore, puis redirige vers /."""
    if db.count_users(conn) >= 2:
        return RedirectResponse("/", status_code=303)
    db.create_user(conn, name1, color1, auth.hash_password(password1))
    db.create_user(conn, name2, color2, auth.hash_password(password2))
    return RedirectResponse("/", status_code=303)


@app.get("/")
def login_form(request: Request, conn: sqlite3.Connection = Depends(db.get_db)):
    """Écran de login : sélection de profil + mot de passe."""
    if db.count_users(conn) < 2:
        return RedirectResponse("/setup", status_code=303)
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "login.html", {"users": db.list_users(conn), "error": None})


@app.post("/login")
def login_submit(
    request: Request,
    user_id: int = Form(...),
    password: str = Form(...),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Vérifie le mot de passe et ouvre la session."""
    user = db.get_user_by_id(conn, user_id)
    if user is None or not auth.verify_password(password, user.password_hash):
        return render(
            request,
            "login.html",
            {"users": db.list_users(conn), "error": "login.error"},
        )
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@app.post("/logout")
def logout(request: Request):
    """Ferme la session."""
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/dashboard")
def dashboard(
    request: Request,
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Écran du jour : humeur, rêve, objectifs, événements."""
    today = date.today().isoformat()
    mood_entry = db.get_mood_entry(conn, user.id, today)
    event_rows = db.list_visible_for_date(conn, "events", today, user.id)
    context = {
        "today": today,
        "entry": mood_entry,
        "entry_needs": db.get_needs_for_entry(conn, "mood", mood_entry["id"])
        if mood_entry
        else [],
        "dreams": db.list_visible_for_date(conn, "dreams", today, user.id),
        "goals": db.list_visible_for_date(conn, "daily_goals", today, user.id),
        "goals_progress": db.compute_goal_completion(conn, user.id, today),
        "entries": [
            {"entry": row, "entry_needs": db.get_needs_for_entry(conn, "event", row["id"])}
            for row in event_rows
        ],
        "needs_grouped": db.get_needs_grouped(conn),
    }
    return render(request, "dashboard.html", context, user=user)


@app.patch("/{table}/{entry_id}/visibility")
def toggle_visibility(
    request: Request,
    table: str,
    entry_id: int,
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Bascule privé <-> public pour une entrée dont l'appelant est propriétaire."""
    if table not in db.VISIBILITY_TABLES:
        raise HTTPException(status_code=404)
    row = db.toggle_visibility(conn, table, entry_id, user.id)
    if row is None:
        raise HTTPException(status_code=404)
    return render(
        request, "partials/visibility_badge.html", {"table": table, "row": row}, user=user
    )


app.include_router(mood.router)
app.include_router(dreams.router)
app.include_router(events.router)
app.include_router(goals.router)
app.include_router(tasks.router)
app.include_router(history.router)
app.include_router(export.router)
app.include_router(settings.router)
