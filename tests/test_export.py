"""Export PDF des événements négatifs sur une période."""

from __future__ import annotations

import datetime

from fastapi.testclient import TestClient


def test_export_pdf_returns_pdf_document(alice_client: TestClient):
    alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "trigger export",
            "emotion": "tristesse",
            "intensity": 4,
            "visibility": "private",
        },
    )
    today = datetime.date.today().isoformat()
    r = alice_client.get(f"/export/pdf?date_from={today}&date_to={today}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_export_pdf_scoped_to_requesting_user(alice_client: TestClient, bob_client: TestClient):
    """Bob ne doit pas pouvoir récupérer les événements négatifs d'Alice via son propre export."""
    alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "trigger alice only",
            "emotion": "colère",
            "intensity": 5,
            "visibility": "public",
        },
    )
    today = datetime.date.today().isoformat()
    r_alice = alice_client.get(f"/export/pdf?date_from={today}&date_to={today}")
    r_bob = bob_client.get(f"/export/pdf?date_from={today}&date_to={today}")
    assert len(r_bob.content) < len(r_alice.content)
