"""Setup initial, login/logout, et protection des routes par session."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_setup_redirects_to_login_once_two_profiles_exist(client: TestClient):
    client.post(
        "/setup",
        data={
            "name1": "Alice",
            "color1": "#ff0000",
            "password1": "alice-pass",
            "name2": "Bob",
            "color2": "#00ff00",
            "password2": "bob-pass",
        },
    )
    r = client.get("/setup", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_login_happy_path(client: TestClient, two_users: tuple[int, int]):
    r = client.post(
        "/login", data={"user_id": two_users[0], "password": "alice-pass"}, follow_redirects=False
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/dashboard"
    assert "session" in client.cookies


def test_login_wrong_password_shows_error(client: TestClient, two_users: tuple[int, int]):
    r = client.post("/login", data={"user_id": two_users[0], "password": "WRONG"})
    assert r.status_code == 200
    assert "session" not in client.cookies


def test_dashboard_requires_authentication(client: TestClient, two_users: tuple[int, int]):
    r = client.get("/dashboard")
    assert r.status_code == 401


def test_logout_clears_session(alice_client: TestClient):
    alice_client.post("/logout", follow_redirects=False)
    r = alice_client.get("/dashboard")
    assert r.status_code == 401


def test_current_user_resolved_from_session_not_client_param(alice_client: TestClient, two_users):
    """La session détermine l'utilisateur, un id client-fourni ne doit avoir aucun effet."""
    r = alice_client.post(
        "/mood",
        data={
            "physical_fatigue": 5,
            "mental_fatigue": 5,
            "mood": 5,
            "social_need": 5,
            "stress": 5,
            "sleep_quality": 5,
            "visibility": "private",
            "user_id": two_users[1],
        },
    )
    assert r.status_code == 200
