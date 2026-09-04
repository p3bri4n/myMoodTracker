"""Rendu Jinja2 centralisé : injecte t()/lang/user dans le contexte de chaque page.

Évite le boilerplate d'i18n dans chaque route (cf. CLAUDE.md, section i18n).
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

from app import db, i18n

templates = Jinja2Templates(directory="app/templates")


def render(
    request: Request,
    template_name: str,
    context: dict,
    user: db.User | None = None,
) -> Response:
    language = user.language if user else "fr"
    full_context = {
        "t": i18n.get_translator(language),
        "lang": language,
        "user": user,
        **context,
    }
    return templates.TemplateResponse(request, template_name, full_context)
