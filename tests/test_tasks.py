"""Tâches partagées : toujours visibles des deux profils, pas de notion de visibilité."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient


def test_create_task(alice_client: TestClient):
    r = alice_client.post("/tasks", data={"label": "vider le lave-vaisselle", "assigned_to": ""})
    assert r.status_code == 200
    assert "vider le lave-vaisselle" in r.text


def test_task_visible_to_both_users_regardless_of_creator(
    alice_client: TestClient, bob_client: TestClient
):
    alice_client.post("/tasks", data={"label": "SHARED_TASK", "assigned_to": ""})
    r = bob_client.get("/tasks")
    assert "SHARED_TASK" in r.text


def test_update_task_status_and_assignment(alice_client: TestClient, two_users):
    r = alice_client.post("/tasks", data={"label": "courses", "assigned_to": ""})
    task_id = re.search(r'id="task-(\d+)"', r.text).group(1)

    r2 = alice_client.patch(
        f"/tasks/{task_id}", data={"status": "done", "assigned_to": str(two_users[1])}
    )
    assert r2.status_code == 200
    assert "task-done" in r2.text


def test_update_nonexistent_task_returns_404(alice_client: TestClient):
    r = alice_client.patch("/tasks/999", data={"status": "done", "assigned_to": ""})
    assert r.status_code == 404
