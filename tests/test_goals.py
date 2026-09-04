"""Objectifs quotidiens : ajout, coche/décoche, visibilité."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient


def _extract_goal_id(html: str) -> str:
    m = re.search(r"/goals/(\d+)", html)
    assert m, html
    return m.group(1)


def test_create_goal(alice_client: TestClient):
    r = alice_client.post("/goals", data={"label": "lire 20 pages", "visibility": "private"})
    assert r.status_code == 200
    assert "lire 20 pages" in r.text


def test_toggle_goal_done(alice_client: TestClient):
    r = alice_client.post("/goals", data={"label": "sport", "visibility": "private"})
    goal_id = _extract_goal_id(r.text)

    r2 = alice_client.patch(f"/goals/{goal_id}", data={"done": "true"})
    assert r2.status_code == 200
    assert "goal-done" in r2.text

    r3 = alice_client.patch(f"/goals/{goal_id}", data={"done": "false"})
    assert "goal-done" not in r3.text


def test_cannot_toggle_other_users_goal(alice_client: TestClient, bob_client: TestClient):
    r = alice_client.post("/goals", data={"label": "objectif prive", "visibility": "private"})
    goal_id = _extract_goal_id(r.text)

    r2 = bob_client.patch(f"/goals/{goal_id}", data={"done": "true"})
    assert r2.status_code == 404


def test_private_goal_not_visible_to_other_user(alice_client: TestClient, bob_client: TestClient):
    import datetime

    alice_client.post("/goals", data={"label": "SECRET_GOAL", "visibility": "private"})
    today = datetime.date.today().isoformat()
    r = bob_client.get(f"/history?date={today}")
    assert "SECRET_GOAL" not in r.text


def test_public_goal_visible_to_other_user(alice_client: TestClient, bob_client: TestClient):
    import datetime

    alice_client.post("/goals", data={"label": "SHARED_GOAL", "visibility": "public"})
    today = datetime.date.today().isoformat()
    r = bob_client.get(f"/history?date={today}")
    assert "SHARED_GOAL" in r.text


def test_goal_owner_name_shown(alice_client: TestClient):
    r = alice_client.post("/goals", data={"label": "objectif", "visibility": "private"})
    assert "Alice" in r.text


def test_edit_goal_label(alice_client: TestClient):
    r = alice_client.post("/goals", data={"label": "ancien libellé", "visibility": "private"})
    goal_id = _extract_goal_id(r.text)

    r2 = alice_client.get(f"/goals/{goal_id}/edit")
    assert r2.status_code == 200
    assert 'value="ancien libellé"' in r2.text

    r3 = alice_client.patch(f"/goals/{goal_id}", data={"label": "nouveau libellé"})
    assert r3.status_code == 200
    assert "nouveau libellé" in r3.text
    assert "ancien libellé" not in r3.text


def test_editing_label_preserves_done_state(alice_client: TestClient):
    r = alice_client.post("/goals", data={"label": "sport", "visibility": "private"})
    goal_id = _extract_goal_id(r.text)
    alice_client.patch(f"/goals/{goal_id}", data={"done": "true"})

    r2 = alice_client.patch(f"/goals/{goal_id}", data={"label": "sport (renommé)"})
    assert "goal-done" in r2.text


def test_cannot_edit_other_users_goal(alice_client: TestClient, bob_client: TestClient):
    r = alice_client.post("/goals", data={"label": "prive", "visibility": "private"})
    goal_id = _extract_goal_id(r.text)

    r2 = bob_client.get(f"/goals/{goal_id}/edit")
    assert r2.status_code == 404

    r3 = bob_client.patch(f"/goals/{goal_id}", data={"label": "hacked"})
    assert r3.status_code == 404


def test_delete_own_goal(alice_client: TestClient):
    r = alice_client.post("/goals", data={"label": "à supprimer", "visibility": "private"})
    goal_id = _extract_goal_id(r.text)

    r2 = alice_client.delete(f"/goals/{goal_id}")
    assert r2.status_code == 204

    r3 = alice_client.get(f"/goals/{goal_id}")
    assert r3.status_code == 404


def test_cannot_delete_other_users_goal(alice_client: TestClient, bob_client: TestClient):
    r = alice_client.post("/goals", data={"label": "prive", "visibility": "private"})
    goal_id = _extract_goal_id(r.text)

    r2 = bob_client.delete(f"/goals/{goal_id}")
    assert r2.status_code == 404

    r3 = alice_client.get(f"/goals/{goal_id}")
    assert r3.status_code == 200
