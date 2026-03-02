"""
Tests for /api/tasks — CRUD and permission rules.
"""
import pytest
from httpx import AsyncClient


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_task_owner(client: AsyncClient, owner_token: str):
    resp = await client.post(
        "/api/tasks",
        json={"title": "Owner task", "description": "desc"},
        headers=auth(owner_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Owner task"
    assert body["status"] == "todo"


@pytest.mark.asyncio
async def test_create_task_member(client: AsyncClient, member_token: str):
    resp = await client.post(
        "/api/tasks",
        json={"title": "Member task"},
        headers=auth(member_token),
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_task_empty_title(client: AsyncClient, owner_token: str):
    resp = await client.post(
        "/api/tasks",
        json={"title": "   "},
        headers=auth(owner_token),
    )
    assert resp.status_code == 422


# ── List ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_owner_sees_all_tasks(
    client: AsyncClient, owner_token: str, member_token: str
):
    # member creates a task
    await client.post("/api/tasks", json={"title": "Member task"}, headers=auth(member_token))
    # owner creates a task
    await client.post("/api/tasks", json={"title": "Owner task"}, headers=auth(owner_token))

    resp = await client.get("/api/tasks", headers=auth(owner_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_member_sees_only_own_tasks(
    client: AsyncClient, owner_token: str, member_token: str
):
    await client.post("/api/tasks", json={"title": "Owner task"}, headers=auth(owner_token))
    await client.post("/api/tasks", json={"title": "Member task"}, headers=auth(member_token))

    resp = await client.get("/api/tasks", headers=auth(member_token))
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Member task"


@pytest.mark.asyncio
async def test_filter_by_status(client: AsyncClient, owner_token: str):
    await client.post("/api/tasks", json={"title": "Todo task", "status": "todo"}, headers=auth(owner_token))
    await client.post("/api/tasks", json={"title": "Done task", "status": "done"}, headers=auth(owner_token))

    resp = await client.get("/api/tasks?status=done", headers=auth(owner_token))
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Done task"


# ── Read ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_task_by_id(client: AsyncClient, owner_token: str):
    create_resp = await client.post(
        "/api/tasks", json={"title": "Specific task"}, headers=auth(owner_token)
    )
    task_id = create_resp.json()["id"]

    resp = await client.get(f"/api/tasks/{task_id}", headers=auth(owner_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == task_id


@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient, owner_token: str):
    resp = await client.get("/api/tasks/99999", headers=auth(owner_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_member_cannot_access_others_task(
    client: AsyncClient, owner_token: str, member_token: str, member_user
):
    create_resp = await client.post(
        "/api/tasks", json={"title": "Owner-only task"}, headers=auth(owner_token)
    )
    task_id = create_resp.json()["id"]

    resp = await client.get(f"/api/tasks/{task_id}", headers=auth(member_token))
    assert resp.status_code == 403


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_task_status(client: AsyncClient, owner_token: str):
    create_resp = await client.post(
        "/api/tasks", json={"title": "Task to update"}, headers=auth(owner_token)
    )
    task_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/tasks/{task_id}",
        json={"status": "in_progress"},
        headers=auth(owner_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_member_cannot_update_others_task(
    client: AsyncClient, owner_token: str, member_token: str
):
    create_resp = await client.post(
        "/api/tasks", json={"title": "Owner task"}, headers=auth(owner_token)
    )
    task_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/tasks/{task_id}",
        json={"status": "done"},
        headers=auth(member_token),
    )
    assert resp.status_code == 403


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, owner_token: str):
    create_resp = await client.post(
        "/api/tasks", json={"title": "To delete"}, headers=auth(owner_token)
    )
    task_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/tasks/{task_id}", headers=auth(owner_token))
    assert resp.status_code == 204

    resp = await client.get(f"/api/tasks/{task_id}", headers=auth(owner_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_member_cannot_delete_others_task(
    client: AsyncClient, owner_token: str, member_token: str
):
    create_resp = await client.post(
        "/api/tasks", json={"title": "Owner task"}, headers=auth(owner_token)
    )
    task_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/tasks/{task_id}", headers=auth(member_token))
    assert resp.status_code == 403


# ── Assignment ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_assign_user_to_task(
    client: AsyncClient, owner_token: str, member_user
):
    create_resp = await client.post(
        "/api/tasks",
        json={"title": "Assigned task", "assigned_user_ids": [member_user.id]},
        headers=auth(owner_token),
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert any(u["id"] == member_user.id for u in body["assigned_users"])


@pytest.mark.asyncio
async def test_assigned_member_can_see_task(
    client: AsyncClient, owner_token: str, member_token: str, member_user
):
    create_resp = await client.post(
        "/api/tasks",
        json={"title": "Assigned to member", "assigned_user_ids": [member_user.id]},
        headers=auth(owner_token),
    )
    task_id = create_resp.json()["id"]

    resp = await client.get(f"/api/tasks/{task_id}", headers=auth(member_token))
    assert resp.status_code == 200
