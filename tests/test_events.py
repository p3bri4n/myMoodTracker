"""Événements positifs/négatifs : champs requis/optionnels selon le type, visibilité, besoins,
roue des émotions à 3 niveaux."""

from __future__ import annotations

import datetime
import re

from fastapi.testclient import TestClient


def _extract_event_id(html: str) -> str:
    m = re.search(r'hx-patch="/events/(\d+)/visibility"', html)
    assert m, html
    return m.group(1)


def _get_emotion_id(client: TestClient, core: str = "Anger", secondary: str = "Critical") -> str:
    """Récupère un emotion_id valide en suivant le flux à 3 niveaux (core -> secondary -> specific)."""
    r = client.get(f"/emotions?core={core}&secondary={secondary}")
    assert r.status_code == 200
    m = re.search(r'name="emotion_id" value="(\d+)"', r.text)
    assert m, r.text
    return m.group(1)


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


def test_negative_event_missing_emotion_id_rejected(alice_client: TestClient):
    r = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "remarque désagréable",
            "intensity": 6,
            "visibility": "private",
        },
    )
    assert r.status_code == 422


def test_negative_event_invalid_emotion_id_rejected(alice_client: TestClient):
    r = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "remarque désagréable",
            "emotion_id": 999999,
            "intensity": 6,
            "visibility": "private",
        },
    )
    assert r.status_code == 422


def test_negative_event_happy_path_optional_grid_fields_omitted(alice_client: TestClient):
    emotion_id = _get_emotion_id(alice_client)
    r = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "remarque désagréable",
            "emotion_id": emotion_id,
            "intensity": 6,
            "visibility": "private",
        },
    )
    assert r.status_code == 200
    assert "remarque désagréable" in r.text
    assert "Colère" in r.text  # breadcrumb core de la roue des émotions


def test_negative_event_full_grid(alice_client: TestClient):
    emotion_id = _get_emotion_id(alice_client)
    r = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "dispute",
            "aggravating_factors": "fatigue",
            "first_signs": "tension à la mâchoire",
            "emotion_id": emotion_id,
            "intensity": 8,
            "thoughts": "je ne suis pas écouté",
            "physiological_reactions": "cœur qui bat vite",
            "behavior": "je me suis isolé",
            "consequences": "soirée tendue",
            "visibility": "private",
        },
    )
    assert r.status_code == 200
    for expected in ["dispute", "fatigue", "je ne suis pas écouté", "soirée tendue"]:
        assert expected in r.text


def test_intensity_out_of_range_rejected(alice_client: TestClient):
    emotion_id = _get_emotion_id(alice_client)
    r = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "x",
            "emotion_id": emotion_id,
            "intensity": 11,
            "visibility": "private",
        },
    )
    assert r.status_code == 422


def test_private_negative_event_not_visible_to_other_user(
    alice_client: TestClient, bob_client: TestClient
):
    emotion_id = _get_emotion_id(alice_client)
    alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "SECRET_TRIGGER",
            "emotion_id": emotion_id,
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


def test_event_can_reference_a_prior_event_as_its_cause(alice_client: TestClient):
    emotion_id = _get_emotion_id(alice_client)
    r1 = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "CAUSE_EVENT",
            "emotion_id": emotion_id,
            "intensity": 4,
            "visibility": "private",
        },
    )
    cause_id = _extract_event_id(r1.text)

    r2 = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "pas de voiture pour chercher ma fille",
            "emotion_id": emotion_id,
            "intensity": 7,
            "visibility": "private",
            "caused_by_event_id": cause_id,
        },
    )
    assert r2.status_code == 200
    assert "CAUSE_EVENT" in r2.text


def test_cannot_link_to_another_users_event(alice_client: TestClient, bob_client: TestClient):
    emotion_id = _get_emotion_id(alice_client)
    r_bob = bob_client.post(
        "/events",
        data={
            "type": "positive",
            "description": "BOB_EVENT",
            "visibility": "public",
        },
    )
    bob_event_id = _extract_event_id(r_bob.text)

    r_alice = alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "x",
            "emotion_id": emotion_id,
            "intensity": 3,
            "visibility": "private",
            "caused_by_event_id": bob_event_id,
        },
    )
    assert r_alice.status_code == 422


def test_caused_by_hidden_when_cause_later_made_private(
    alice_client: TestClient, bob_client: TestClient
):
    r1 = alice_client.post(
        "/events",
        data={"type": "positive", "description": "CAUSE_TEXT", "visibility": "public"},
    )
    cause_id = _extract_event_id(r1.text)

    r2 = alice_client.post(
        "/events",
        data={
            "type": "positive",
            "description": "EFFECT_TEXT",
            "visibility": "public",
            "caused_by_event_id": cause_id,
        },
    )
    assert "CAUSE_TEXT" in r2.text

    alice_client.patch(f"/events/{cause_id}/visibility")

    today = datetime.date.today().isoformat()
    r3 = bob_client.get(f"/history?date={today}")
    assert "EFFECT_TEXT" in r3.text
    assert "CAUSE_TEXT" not in r3.text


# --- Roue des émotions ----------------------------------------------------


def test_emotions_no_params_returns_six_cores(alice_client: TestClient):
    r = alice_client.get("/emotions")
    assert r.status_code == 200
    assert r.text.count('class="emotion-tile emotion-tile-core emotion-core-') == 6
    assert "Colère" in r.text and "Joie" in r.text


def test_emotions_core_only_returns_secondaries(alice_client: TestClient):
    r = alice_client.get("/emotions?core=Anger")
    assert r.status_code == 200
    assert "Critique" in r.text  # secondary_critical


def test_emotions_core_and_secondary_returns_specifics(alice_client: TestClient):
    r = alice_client.get("/emotions?core=Anger&secondary=Critical")
    assert r.status_code == 200
    assert 'name="emotion_id"' in r.text
    assert "Sarcastique" in r.text


def test_positive_event_optional_emotion_wheel(alice_client: TestClient):
    emotion_id = _get_emotion_id(alice_client, core="Joy", secondary="Interested")
    r = alice_client.post(
        "/events",
        data={
            "type": "positive",
            "description": "belle découverte",
            "visibility": "private",
            "emotion_id": emotion_id,
        },
    )
    assert r.status_code == 200
    assert "Joie" in r.text and "Intéressé" in r.text


def test_emotion_breadcrumb_shown_in_history(alice_client: TestClient):
    emotion_id = _get_emotion_id(alice_client, core="Sadness", secondary="Guilty")
    alice_client.post(
        "/events",
        data={
            "type": "negative",
            "trigger": "BREADCRUMB_TEST",
            "emotion_id": emotion_id,
            "intensity": 5,
            "visibility": "private",
        },
    )
    today = datetime.date.today().isoformat()
    r = alice_client.get(f"/history?date={today}")
    assert "Tristesse" in r.text and "Coupable" in r.text
