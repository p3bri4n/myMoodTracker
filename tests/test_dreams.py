"""Journal de rêves : entrée optionnelle, tag, visibilité."""

from __future__ import annotations

import datetime

from fastapi.testclient import TestClient


def test_create_dream_happy_path(alice_client: TestClient):
    r = alice_client.post(
        "/dreams", data={"content": "Je volais", "tag": "pleasant", "visibility": "private"}
    )
    assert r.status_code == 200
    assert "Je volais" in r.text


def test_dream_tag_is_optional(alice_client: TestClient):
    r = alice_client.post("/dreams", data={"content": "Sans tag", "tag": "", "visibility": "private"})
    assert r.status_code == 200


def test_private_dream_not_visible_to_other_user(alice_client: TestClient, bob_client: TestClient):
    alice_client.post(
        "/dreams", data={"content": "SECRET_DREAM", "tag": "", "visibility": "private"}
    )
    today = datetime.date.today().isoformat()
    r = bob_client.get(f"/history?date={today}")
    assert "SECRET_DREAM" not in r.text


def test_public_dream_visible_to_other_user(alice_client: TestClient, bob_client: TestClient):
    alice_client.post(
        "/dreams", data={"content": "SHARED_DREAM", "tag": "", "visibility": "public"}
    )
    today = datetime.date.today().isoformat()
    r = bob_client.get(f"/history?date={today}")
    assert "SHARED_DREAM" in r.text
