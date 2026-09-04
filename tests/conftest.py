"""Fixtures pytest : DB temporaire par test, clients authentifiés pour 2 profils."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_env() -> Iterator[str]:
    """Isole chaque test avec un fichier SQLite temporaire (jamais la DB réelle)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    os.environ["MYMOODTRACKER_DB_PATH"] = path
    os.environ["SECRET_KEY"] = "test-secret"
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture()
def client(app_env: str) -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def two_users(client: TestClient) -> tuple[int, int]:
    """Crée les 2 profils de test (Alice=1, Bob=2) via /setup."""
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
    return 1, 2


@pytest.fixture()
def alice_client(client: TestClient, two_users: tuple[int, int]) -> TestClient:
    client.post("/login", data={"user_id": two_users[0], "password": "alice-pass"})
    return client


@pytest.fixture()
def bob_client(app_env: str, two_users: tuple[int, int]) -> Iterator[TestClient]:
    """Un second client, avec ses propres cookies de session, connecté en Bob."""
    from app.main import app

    with TestClient(app) as c:
        c.post("/login", data={"user_id": two_users[1], "password": "bob-pass"})
        yield c
