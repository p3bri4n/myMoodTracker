"""Événements positifs/négatifs : champs requis/optionnels selon le type, visibilité, besoins."""

from __future__ import annotations

import datetime

from fastapi.testclient import TestClient


def test_positive_event_requires_description(alice_client: TestClient):
    r = alice_client.post("/events", data={"type": "positive", "visibility": "private"})
    assert r.status_code == 422


def test_positive_event_happy_path_time_optional(alice_client: TestClient):
    r = alice_client.post(
        "/events",
        data={"type": "positive", "description": "belle rencontre", "visibility": "private"},
    )
    assert r.status_code == 200
    assert "belle rencontre" in r.text


def test_negative_event_requires_trigger_emotion_intensity(alice_client: TestClient):
    r = alice_client.post(
        "/events",
        data={"type": "negative", "description": "sans grille", "visibility": "private"},
    )
    assert r.status_code == 422


def test_negative_event_happy_path_optional_grid_fields_omitted(alice_client: TestClient):
    r = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "remarque désagréable",
            "emotion": "colère",
            "intensity": 6,
            "visibility": "private",
        },
    )
    assert r.status_code == 200
    assert "remarque désagréable" in r.text
    assert "colère" in r.text


def test_negative_event_full_grid(alice_client: TestClient):
    r = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "dispute",
            "aggravating_factors": "fatigue",
            "first_signs": "tension à la mâchoire",
            "emotion": "frustration",
            "intensity": 8,
            "thoughts": "je ne suis pas écouté",
            "physiological_reactions": "cœur qui bat vite",
            "behavior": "je me suis isolé",
            "consequences": "soirée tendue",
            "visibility": "private",
        },
    )
    assert r.status_code == 200
    for expected in ["dispute", "fatigue", "frustration", "je ne suis pas écouté", "soirée tendue"]:
        assert expected in r.text


def test_intensity_out_of_range_rejected(alice_client: TestClient):
    r = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "x",
            "emotion": "y",
            "intensity": 11,
            "visibility": "private",
        },
    )
    assert r.status_code == 422


def test_private_negative_event_not_visible_to_other_user(
    alice_client: TestClient, bob_client: TestClient
):
    alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "SECRET_TRIGGER",
            "emotion": "colère",
            "intensity": 5,
            "visibility": "private",
        },
    )
    today = datetime.date.today().isoformat()
    r = bob_client.get(f"/history?date={today}")
    assert "SECRET_TRIGGER" not in r.text


def test_public_positive_event_visible_to_other_user(
    alice_client: TestClient, bob_client: TestClient
):
    alice_client.post(
        "/events",
        data={"type": "positive", "description": "SHARED_GOOD_NEWS", "visibility": "public"},
    )
    today = datetime.date.today().isoformat()
    r = bob_client.get(f"/history?date={today}")
    assert "SHARED_GOOD_NEWS" in r.text


def test_event_needs_tagging(alice_client: TestClient):
    needs_resp = alice_client.get("/needs")
    assert needs_resp.status_code == 200

    r = alice_client.post(
        "/events",
        data={
            "type": "positive",
            "description": "moment de calme",
            "visibility": "private",
            "needs": [1, 2],
        },
    )
    assert r.status_code == 200


def test_list_events_for_date(alice_client: TestClient):
    alice_client.post(
        "/events", data={"type": "positive", "description": "evt du jour", "visibility": "private"}
    )
    today = datetime.date.today().isoformat()
    r = alice_client.get(f"/events?date={today}")
    assert r.status_code == 200
    assert "evt du jour" in r.text
