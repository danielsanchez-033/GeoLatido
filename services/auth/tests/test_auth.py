import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from auth.main import create_app
from auth.store import DB_FILE
from auth.tokens import AUDIENCE, ISSUER, KEY_FILE

ROOT = Path(__file__).resolve().parents[3]
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
    # Cookie en "/" y sin Secure: el cliente de pruebas habla HTTP con "testserver".
    app = create_app(data_dir=tmp_path, clock=clock, cookie_secure="false", cookie_path="/")
    return TestClient(app)


def register(client, email="ana@example.org", role="researcher", password=PASSWORD):
    return client.post("/register", json={"email": email, "password": password, "role": role})


def decode(token, client):
    key = jwt.PyJWK(client.get("/.well-known/jwks.json").json()["keys"][0])
    return jwt.decode(token, key, algorithms=["EdDSA"], audience=AUDIENCE, issuer=ISSUER, options={"verify_exp": False})


# --- Registro e inicio de sesión (RF-ACC-01, 02, 04 y 12) ---


def test_register_returns_a_15_minute_eddsa_token_and_a_strict_httponly_cookie(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "Bearer" and body["expires_in"] == 900 and body["role"] == "researcher"
    assert body["email_verified"] is False
    assert jwt.get_unverified_header(body["access_token"])["alg"] == "EdDSA"
    claims = decode(body["access_token"], client)
    assert claims["iss"] == "nisar-veredictos" and claims["aud"] == "nisar-api" and claims["role"] == "researcher"
    assert claims["exp"] - claims["iat"] == 900 and claims["jti"] and claims["sub"]
    cookie = response.headers["set-cookie"].lower()
    assert "refresh=" in cookie and "httponly" in cookie and "samesite=strict" in cookie and "max-age=604800" in cookie


def test_me_reads_the_account_and_says_the_email_is_not_verified(client):
    token = register(client, email=" Ana@Example.org ").json()["access_token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["email"] == "ana@example.org" and me["role"] == "researcher" and me["email_verified"] is False
    assert me["created_at"] == "2026-11-14T18:00:00Z"
    assert client.get("/me").status_code == 401


def test_register_rejects_short_passwords_bad_emails_public_role_and_duplicates(client):
    assert register(client, password="corta").status_code == 422
    assert register(client, email="sin-arroba").status_code == 422
    assert register(client, role="public").status_code == 422
    assert register(client, role="admin").status_code == 422
    assert register(client).status_code == 201
    assert register(client, email="ANA@example.org").status_code == 409


def test_passwords_have_no_composition_rules(client):
    assert register(client, password="aaaaaaaaaaaa").status_code == 201


def test_login_gives_the_same_answer_for_unknown_email_and_wrong_password(client):
    register(client)
    unknown = client.post("/login", json={"email": "nadie@example.org", "password": PASSWORD})
    wrong = client.post("/login", json={"email": "ana@example.org", "password": "otra frase larga cualquiera"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()
    ok = client.post("/login", json={"email": "ANA@example.org", "password": PASSWORD})
    assert ok.status_code == 200 and ok.json()["role"] == "researcher"


def test_passwords_and_refresh_tokens_are_stored_only_as_hashes(client, tmp_path):
    response = register(client)
    refresh_token = response.cookies["refresh"]
    db = sqlite3.connect(tmp_path / DB_FILE)
    (stored,) = db.execute("SELECT password_hash FROM users").fetchone()
    assert stored.startswith("$argon2id$") and PASSWORD not in stored
    dump = "\n".join(db.iterdump())
    assert refresh_token not in dump and PASSWORD not in dump


# --- Renovación y cierre (RF-ACC-03) ---


def test_refresh_rotates_the_cookie_and_returns_a_new_access_token(client):
    first = register(client).cookies["refresh"]
    response = client.post("/refresh")
    assert response.status_code == 200 and response.json()["role"] == "researcher"
    assert response.cookies["refresh"] != first


def test_reusing_a_rotated_refresh_token_revokes_the_whole_session(client):
    old = register(client).cookies["refresh"]
    new = client.post("/refresh").cookies["refresh"]
    client.cookies.clear()
    client.cookies.set("refresh", old)
    reused = client.post("/refresh")
    assert reused.status_code == 401 and "reutilizado" in reused.json()["detail"]
    client.cookies.clear()
    client.cookies.set("refresh", new)
    assert client.post("/refresh").status_code == 401, "el token nuevo también queda revocado"


def test_refresh_expires_after_seven_days(client, clock):
    register(client)
    clock.now = T0 + timedelta(days=7)
    assert client.post("/refresh").status_code == 401


def test_logout_closes_the_session_and_clears_the_cookie(client):
    token = register(client).cookies["refresh"]
    response = client.post("/logout")
    assert response.status_code == 204 and 'refresh=""' in response.headers["set-cookie"]
    client.cookies.clear()
    client.cookies.set("refresh", token)
    assert client.post("/refresh").status_code == 401


def test_refresh_without_cookie_is_401(client):
    assert client.post("/refresh").status_code == 401


# --- /verify para el gateway (RF-ACC-05 y 06) ---


def test_verify_without_authorization_is_public(client):
    response = client.get("/verify")
    assert response.status_code == 200 and response.headers["x-auth-role"] == "public"
    assert "x-auth-sub" not in response.headers


def test_verify_with_a_valid_token_passes_role_and_subject(client):
    token = register(client, role="student").json()["access_token"]
    response = client.get("/verify", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.headers["x-auth-role"] == "student" and response.headers["x-auth-sub"] == decode(token, client)["sub"]


def test_verify_never_degrades_a_bad_token_to_public(client, clock):
    token = register(client).json()["access_token"]
    other = Ed25519PrivateKey.generate()
    now = int(T0.timestamp())
    base = {"iss": ISSUER, "aud": AUDIENCE, "sub": "x", "role": "researcher", "iat": now, "exp": now + 900, "jti": "j"}
    cases = {
        "otra clave": jwt.encode(base, other, algorithm="EdDSA"),
        "texto": "no-es-un-jwt",
        "sin firma": jwt.encode(base, None, algorithm="none"),
    }
    for name, bad in cases.items():
        response = client.get("/verify", headers={"Authorization": f"Bearer {bad}"})
        assert response.status_code == 401, name
        assert "x-auth-role" not in response.headers, name
    assert client.get("/verify", headers={"Authorization": f"Basic {token}"}).status_code == 401
    clock.now = T0 + timedelta(seconds=900)
    assert client.get("/verify", headers={"Authorization": f"Bearer {token}"}).status_code == 401, "caducado"


def test_verify_rejects_another_audience_or_an_unknown_role(tmp_path, clock):
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    client = TestClient(create_app(data_dir=tmp_path, private_key_pem=pem, clock=clock))
    now = int(T0.timestamp())
    base = {"iss": ISSUER, "aud": AUDIENCE, "sub": "x", "role": "researcher", "iat": now, "exp": now + 900, "jti": "j"}
    for change in ({"aud": "otra-api"}, {"iss": "otro"}, {"role": "admin"}, {"role": "public"}):
        token = jwt.encode({**base, **change}, key, algorithm="EdDSA")
        assert client.get("/verify", headers={"Authorization": f"Bearer {token}"}).status_code == 401, change
    ok = jwt.encode(base, key, algorithm="EdDSA")
    assert client.get("/verify", headers={"Authorization": f"Bearer {ok}"}).headers["x-auth-role"] == "researcher"


def test_verify_does_not_touch_the_database(client, tmp_path):
    token = register(client).json()["access_token"]
    client.app.state.store.close()  # Cualquier consulta a la base daría error a partir de aquí.
    assert client.get("/verify", headers={"Authorization": f"Bearer {token}"}).status_code == 200


# --- Clave y JWKS ---


def test_jwks_publishes_the_key_that_signs_the_tokens(client):
    keys = client.get("/.well-known/jwks.json").json()["keys"]
    assert len(keys) == 1 and keys[0]["kty"] == "OKP" and keys[0]["crv"] == "Ed25519" and keys[0]["alg"] == "EdDSA"
    token = register(client).json()["access_token"]
    assert jwt.get_unverified_header(token)["kid"] == keys[0]["kid"]
    assert decode(token, client)["role"] == "researcher"
    assert "d" not in keys[0], "la clave privada nunca sale"


def test_the_generated_key_is_kept_in_the_volume_and_reused(tmp_path, clock):
    first = TestClient(create_app(data_dir=tmp_path, clock=clock)).get("/.well-known/jwks.json").json()
    assert (tmp_path / KEY_FILE).exists()
    second = TestClient(create_app(data_dir=tmp_path, clock=clock)).get("/.well-known/jwks.json").json()
    assert first == second


def test_auth_private_key_wins_over_the_volume(tmp_path, clock):
    pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    client = TestClient(create_app(data_dir=tmp_path, private_key_pem=pem, clock=clock))
    assert client.get("/health").json() == {"status": "ok"}
    assert not (tmp_path / KEY_FILE).exists()


# --- Cookie Secure (RF-ACC-03) ---


def test_cookie_is_secure_except_on_localhost(tmp_path, clock):
    client = TestClient(create_app(data_dir=tmp_path, clock=clock))
    local = client.post(
        "/register", json={"email": "a@example.org", "password": PASSWORD, "role": "student"}, headers={"host": "localhost:8080"}
    )
    assert "secure" not in local.headers["set-cookie"].lower()
    assert "path=/api/auth/" in local.headers["set-cookie"].lower()
    public = client.post(
        "/register", json={"email": "b@example.org", "password": PASSWORD, "role": "student"},
        headers={"x-forwarded-host": "veredictos.example.org"},
    )
    assert "secure" in public.headers["set-cookie"].lower()


# --- Contrato ---


def test_contract_is_current(tmp_path):
    committed = json.loads((ROOT / "contracts" / "auth.openapi.json").read_text(encoding="utf-8"))
    app = create_app(data_dir=tmp_path)
    assert committed == json.loads(json.dumps(app.openapi())), "Regenera el contrato con export_openapi"
