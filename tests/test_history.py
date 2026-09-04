"""Historique : agrégation du jour, mes données + données publiques du partenaire."""

from __future__ import annotations

import datetime

from fastapi.testclient import TestClient


def test_history_defaults_to_today(alice_client: TestClient):
    r = alice_client.get("/history")
    assert r.status_code == 200


def test_history_requires_authentication(client: TestClient, two_users):
    r = client.get("/history")
    assert r.status_code == 401


def test_history_aggregates_all_entry_types(alice_client: TestClient):
    today = datetime.date.today().isoformat()
    alice_client.post(
        "/mood",
        data={
            "physical_fatigue": 5,
            "mental_fatigue": 5,
            "mood": 5,
            "social_need": 5,
            "stress": 5,
            "sleep_quality": 5,
            "visibility": "private",
        },
    )
    alice_client.post("/dreams", data={"content": "un reve", "tag": "", "visibility": "private"})
    alice_client.post("/goals", data={"label": "un objectif", "visibility": "private"})
    alice_client.post(
        "/events", data={"type": "positive", "description": "un evenement", "visibility": "private"}
    )

    r = alice_client.get(f"/history?date={today}")
    assert r.status_code == 200
    for expected in ["un reve", "un objectif", "un evenement"]:
        assert expected in r.text
