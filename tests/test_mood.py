"""Humeur du jour : upsert, filtrage de visibilité, bornes 1-5 (sélecteur à visages)."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient


def mood_payload(**overrides):
    payload = dict(
        physical_fatigue=3,
        mental_fatigue=2,
        mood=4,
        social_need=3,
        stress=2,
        sleep_quality=4,
        note="ça va",
        visibility="private",
    )
    payload.update(overrides)
    return payload


def _is_checked(html: str, field: str, value: int) -> bool:
    pattern = rf'name="{field}" value="{value}"[^>]*checked'
    return re.search(pattern, html) is not None


def test_create_and_update_mood_is_an_upsert(alice_client: TestClient):
    r1 = alice_client.post("/mood", data=mood_payload(mood=2))
    assert r1.status_code == 200
    r2 = alice_client.post("/mood", data=mood_payload(mood=5))
    assert r2.status_code == 200
    assert _is_checked(r2.text, "mood", 5)

    import datetime

    today = datetime.date.today().isoformat()
    r3 = alice_client.get(f"/history?date={today}")
    # une seule entrée pour ce jour malgré 2 soumissions
    assert r3.text.count('class="card mood-summary"') == 1


def test_mood_values_out_of_range_are_rejected(alice_client: TestClient):
    r = alice_client.post("/mood", data=mood_payload(stress=6))
    assert r.status_code == 422


def test_private_mood_not_visible_to_other_user(
    alice_client: TestClient, bob_client: TestClient
):
    alice_client.post("/mood", data=mood_payload(note="SECRET_MOOD_NOTE", visibility="private"))

    import datetime

    today = datetime.date.today().isoformat()
    r = bob_client.get(f"/history?date={today}")
    assert "SECRET_MOOD_NOTE" not in r.text


def test_public_mood_visible_to_other_user(alice_client: TestClient, bob_client: TestClient):
    alice_client.post("/mood", data=mood_payload(note="PUBLIC_MOOD_NOTE", visibility="public"))

    import datetime

    today = datetime.date.today().isoformat()
    r = bob_client.get(f"/history?date={today}")
    assert "PUBLIC_MOOD_NOTE" in r.text


def test_mood_no_longer_offers_needs_tagging(alice_client: TestClient):
    r = alice_client.post("/mood", data=mood_payload())
    assert r.status_code == 200
    assert 'name="needs"' not in r.text
