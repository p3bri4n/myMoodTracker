"""Export PDF des événements négatifs sur une période."""

from __future__ import annotations

import datetime
import re

from fastapi.testclient import TestClient


def _get_emotion_id(client: TestClient, core: str = "Sadness", secondary: str = "Guilty") -> str:
    r = client.get(f"/emotions?core={core}&secondary={secondary}")
    m = re.search(r'name="emotion_id" value="(\d+)"', r.text)
    assert m, r.text
    return m.group(1)


def test_export_pdf_returns_pdf_document(alice_client: TestClient):
    emotion_id = _get_emotion_id(alice_client)
    alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "trigger export",
            "emotion_id": emotion_id,
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
    emotion_id = _get_emotion_id(alice_client)
    alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "trigger alice only",
            "emotion_id": emotion_id,
            "intensity": 5,
            "visibility": "public",
        },
    )
    today = datetime.date.today().isoformat()
    r_alice = alice_client.get(f"/export/pdf?date_from={today}&date_to={today}")
    r_bob = bob_client.get(f"/export/pdf?date_from={today}&date_to={today}")
    assert len(r_bob.content) < len(r_alice.content)
