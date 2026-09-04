"""Réglages : changement de langue du profil connecté uniquement."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_update_language(alice_client: TestClient):
    r = alice_client.patch("/settings/language", data={"language": "en"})
    assert r.status_code == 200
    r2 = alice_client.get("/dashboard")
    assert "Today's mood" in r2.text or "Today" in r2.text


def test_invalid_language_rejected(alice_client: TestClient):
    r = alice_client.patch("/settings/language", data={"language": "de"})
    assert r.status_code == 422


def test_language_change_is_per_profile(alice_client: TestClient, bob_client: TestClient):
    alice_client.patch("/settings/language", data={"language": "en"})
    r_bob = bob_client.get("/dashboard")
    assert "Réglages" in r_bob.text
    assert 'html lang="fr"' in r_bob.text
