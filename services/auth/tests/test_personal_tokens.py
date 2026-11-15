"""Tokens personales para scripts de researcher (RF-ACC-11, T-ANT-18)."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from auth.main import create_app
from auth.store import DB_FILE, PERSONAL_MAX_ACTIVE, PERSONAL_PREFIX, hash_token

T0 = datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc)
PASSWORD = "una frase larga cualquiera"


class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(tmp_path, clock):
    return TestClient(create_app(data_dir=tmp_path, clock=clock, cookie_secure="false", cookie_path="/"))


def session(client, email="ana@example.org", role="researcher"):
    body = client.post("/register", json={"email": email, "password": PASSWORD, "role": role}).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


def create(client, headers, name="exportación", days=30):
    return client.post("/tokens", json={"name": name, "expires_in_days": days}, headers=headers)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_researcher_creates_a_token_shown_once_and_stored_as_a_hash(client, tmp_path):
    headers = session(client)
    response = create(client, headers, days=90)
    assert response.status_code == 201
    body = response.json()
    token = body["token"]
    assert token.startswith(PERSONAL_PREFIX) and len(token) > 40
    assert body["prefix"] == token[:10] and body["status"] == "active" and body["revoked_at"] is None
    assert body["created_at"] == "2026-11-14T18:00:00Z" and body["expires_at"] == "2027-02-12T18:00:00Z"
    listed = client.get("/tokens", headers=headers).json()
    assert listed["max_days"] == 90 and [t["id"] for t in listed["tokens"]] == [body["id"]]
    assert "token" not in listed["tokens"][0]
    db = sqlite3.connect(tmp_path / DB_FILE)
    stored = db.execute("SELECT hash, prefix FROM personal_tokens").fetchall()
    db.close()
    assert stored == [(hash_token(token), token[:10])]
    assert token not in (tmp_path / DB_FILE).read_bytes().decode("latin-1")


def test_the_token_works_in_verify_and_me_with_the_researcher_role(client):
    headers = session(client)
    token = create(client, headers).json()["token"]
    sub = client.get("/me", headers=headers).json()["sub"]
    verified = client.get("/verify", headers=bearer(token))
    assert verified.status_code == 200
    assert verified.headers["X-Auth-Role"] == "researcher" and verified.headers["X-Auth-Sub"] == sub
    me = client.get("/me", headers=bearer(token))
    assert me.status_code == 200 and me.json()["role"] == "researcher" and me.json()["sub"] == sub


def test_revoking_takes_effect_on_the_next_request(client, clock):
    headers = session(client)
    created = create(client, headers).json()
    assert client.get("/verify", headers=bearer(created["token"])).status_code == 200
    clock.now = T0 + timedelta(minutes=1)
    assert client.delete(f"/tokens/{created['id']}", headers=headers).status_code == 204
    rejected = client.get("/verify", headers=bearer(created["token"]))
    assert rejected.status_code == 401 and "revocado" in rejected.json()["detail"]
    assert rejected.headers["WWW-Authenticate"].startswith("Bearer")
    listed = client.get("/tokens", headers=headers).json()["tokens"][0]
    assert listed["status"] == "revoked" and listed["revoked_at"] == "2026-11-14T18:01:00Z"
    # Revocarlo otra vez no cambia la fecha.
    clock.now = T0 + timedelta(minutes=5)
    assert client.delete(f"/tokens/{created['id']}", headers=headers).status_code == 204
    assert client.get("/tokens", headers=headers).json()["tokens"][0]["revoked_at"] == "2026-11-14T18:01:00Z"


def test_expired_and_unknown_tokens_get_401_never_public(client, clock):
    headers = session(client)
    token = create(client, headers, days=1).json()["token"]
    clock.now = T0 + timedelta(days=1)
    response = client.get("/verify", headers=bearer(token))
    assert response.status_code == 401 and "caducado" in response.json()["detail"]
    assert "X-Auth-Role" not in response.headers
    assert client.get("/verify", headers=bearer(PERSONAL_PREFIX + "inventado")).status_code == 401
    # Una sesión nueva (la anterior caducó con el reloj) lo ve caducado.
    login = client.post("/login", json={"email": "ana@example.org", "password": PASSWORD}).json()
    listed = client.get("/tokens", headers=bearer(login["access_token"])).json()["tokens"]
    assert listed[0]["status"] == "expired"


@pytest.mark.parametrize("days", [0, 91, -5])
def test_lifetime_is_between_1_and_90_days(client, days):
    assert create(client, session(client), days=days).status_code == 422


@pytest.mark.parametrize("name", ["", "   ", "x" * 65])
def test_name_is_required_and_short(client, name):
    assert create(client, session(client), name=name).status_code == 422


def test_only_researcher_sessions_manage_tokens(client):
    student = session(client, "eva@example.org", "student")
    for response in (create(client, student), client.get("/tokens", headers=student), client.delete("/tokens/x", headers=student)):
        assert response.status_code == 403
        assert response.json() == {"detail": "Hace falta una cuenta con el perfil Investigador.", "required_role": "researcher"}
    assert create(client, {}).status_code == 401
    assert client.get("/tokens").status_code == 401


def test_a_personal_token_cannot_create_or_revoke_tokens(client):
    headers = session(client)
    created = create(client, headers).json()
    personal = bearer(created["token"])
    assert create(client, personal).status_code == 403
    assert client.get("/tokens", headers=personal).status_code == 403
    response = client.delete(f"/tokens/{created['id']}", headers=personal)
    assert response.status_code == 403 and response.json()["required_role"] == "researcher"
    assert client.get("/verify", headers=personal).status_code == 200


def test_nobody_revokes_another_accounts_token(client):
    ana = session(client)
    created = create(client, ana).json()
    luis = session(client, "luis@example.org")
    assert client.delete(f"/tokens/{created['id']}", headers=luis).status_code == 404
    assert client.get("/tokens", headers=luis).json()["tokens"] == []
    assert client.get("/verify", headers=bearer(created["token"])).status_code == 200


def test_active_tokens_are_capped_and_revoking_frees_a_slot(client):
    headers = session(client)
    ids = [create(client, headers, name=f"t{i}").json()["id"] for i in range(PERSONAL_MAX_ACTIVE)]
    assert create(client, headers).status_code == 409
    client.delete(f"/tokens/{ids[0]}", headers=headers)
    assert create(client, headers).status_code == 201


def test_session_tokens_still_verify_without_touching_personal_tokens(client):
    headers = session(client, role="student")
    response = client.get("/verify", headers=headers)
    assert response.status_code == 200 and response.headers["X-Auth-Role"] == "student"


def test_contract_declares_the_routes_and_the_required_role(client):
    spec = client.get("/openapi.json").json()
    for method in ("post", "get"):
        operation = spec["paths"]["/tokens"][method]
        assert operation["x-required-role"] == "researcher" and operation["security"] == [{"bearerAuth": []}]
    assert spec["paths"]["/tokens/{token_id}"]["delete"]["x-required-role"] == "researcher"
    assert "bearerAuth" in spec["components"]["securitySchemes"]
