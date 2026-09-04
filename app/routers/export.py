"""Export PDF des événements négatifs sur une période (suivi psychologique)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from weasyprint import HTML

from app import auth, db, i18n

router = APIRouter()

pdf_templates = Jinja2Templates(directory="app/pdf")


@router.get("/export/pdf")
def export_negative_events_pdf(
    date_from: str,
    date_to: str,
    user: db.User = Depends(auth.get_current_user),
    conn: sqlite3.Connection = Depends(db.get_db),
):
    """Génère un PDF (tableau) des événements négatifs de l'utilisateur sur la période."""
    events = db.list_negative_events_for_period(conn, user.id, date_from, date_to)
    t = i18n.get_translator(user.language)
    html_string = pdf_templates.get_template("negative_events_template.html").render(
        events=events, date_from=date_from, date_to=date_to, t=t
    )
    pdf_bytes = HTML(string=html_string).write_pdf()
    filename = f"negative_events_{date_from}_{date_to}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
