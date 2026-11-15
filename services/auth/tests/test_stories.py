"""Historias de la comunidad (RF-ACC-13 a 17, T-ANT-20)."""
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from auth.main import create_app
from auth.stories import NOTES_MAX, PAIRS_MAX

T0 = datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc)
PASSWORD = "una frase larga cualquiera"


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(data_dir=tmp_path, clock=lambda: T0, cookie_secure="false", cookie_path="/"))


def session(client, email, role):
    body = client.post("/register", json={"email": email, "password": PASSWORD, "role": role}).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


def story(**over):
    body = {
        "title": "Agosto en Parral",
        "aoi": "parral",
        "series": "T048A-F015",
        "from_date": "2026-08-01",
        "to_date": "2026-09-10",
        "pairs": [
            {"series": "T048A-F015", "pair": "20260816_20260828"},
            {"series": "T048A-F015", "pair": "20260828_20260909"},
        ],
        "notes": "Mis notas: miré las calles del centro.",
    }
    body.update(over)
    return body


@pytest.fixture
def ana(client):
    return session(client, "ana@example.org", "student")


def test_anyone_reads_stories_without_account_and_never_sees_the_email(client, ana):
    created = client.post("/stories", json=story(), headers=ana)
    assert created.status_code == 201
    body = created.json()
    assert body["author_role"] == "student" and body["is_mine"] is True and body["my_stars"] is None
    assert body["created_at"] == "2026-11-14T18:00:00Z" and body["downloads"] == 0
    assert body["author_alias"].startswith("GL-") and len(body["author_alias"]) == 9
    assert client.get("/stories").json()["stories"][0]["author_alias"] == body["author_alias"]
    assert body["pairs"][0] == {"series": "T048A-F015", "pair": "20260816_20260828"}

    listed = client.get("/stories")
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 1 and page["stories"][0]["id"] == body["id"]
    assert page["stories"][0]["is_mine"] is False
    assert "ana@example.org" not in listed.text
    assert client.get(f"/stories/{body['id']}").json()["notes"] == "Mis notas: miré las calles del centro."


def test_a_story_stores_references_and_notes_but_no_verdict_text(client, ana):
    body = client.post("/stories", json=story(summary={"detected": "texto inventado"}), headers=ana).json()
    assert "summary" not in body and "texto inventado" not in json.dumps(body)


def test_creating_and_rating_need_a_session(client, ana):
    sid = client.post("/stories", json=story(), headers=ana).json()["id"]
    assert client.post("/stories", json=story()).status_code == 401
    assert client.post(f"/stories/{sid}/rating", json={"stars": 4}).status_code == 401
    # Descargar no pide sesión desde el 2026-11-14: cuenta igual.
    assert client.post(f"/stories/{sid}/download").json()["downloads"] == 1
    assert client.delete(f"/stories/{sid}").status_code == 401
    # Un token roto da 401 también en la lectura: nunca se degrada a public (RF-ACC-06).
    assert client.get("/stories", headers={"Authorization": "Bearer roto"}).status_code == 401


def test_stars_average_with_breakdown_by_declared_profile(client, ana):
    sid = client.post("/stories", json=story(), headers=ana).json()["id"]
    beto = session(client, "beto@example.org", "student")
    cora = session(client, "cora@example.org", "researcher")
    dani = session(client, "dani@example.org", "researcher")
    client.post(f"/stories/{sid}/rating", json={"stars": 4}, headers=beto)
    client.post(f"/stories/{sid}/rating", json={"stars": 5}, headers=cora)
    rated = client.post(f"/stories/{sid}/rating", json={"stars": 2}, headers=dani).json()
    assert rated["my_stars"] == 2
    assert rated["ratings"] == {
        "count": 3,
        "average": 3.67,
        "by_role": {"student": {"count": 1, "average": 4.0}, "researcher": {"count": 2, "average": 3.5}},
    }
    # Valorar otra vez sustituye la valoración anterior.
    again = client.post(f"/stories/{sid}/rating", json={"stars": 5}, headers=dani).json()
    assert again["ratings"]["count"] == 3 and again["ratings"]["by_role"]["researcher"]["average"] == 5.0
    removed = client.delete(f"/stories/{sid}/rating", headers=dani).json()
    assert removed["my_stars"] is None and removed["ratings"]["count"] == 2


def test_without_ratings_the_average_is_null(client, ana):
    body = client.post("/stories", json=story(), headers=ana).json()
    assert body["ratings"] == {
        "count": 0,
        "average": None,
        "by_role": {"student": {"count": 0, "average": None}, "researcher": {"count": 0, "average": None}},
    }


def test_nobody_rates_their_own_story_and_stars_go_from_1_to_5(client, ana):
    sid = client.post("/stories", json=story(), headers=ana).json()["id"]
    assert client.post(f"/stories/{sid}/rating", json={"stars": 5}, headers=ana).status_code == 409
    beto = session(client, "beto@example.org", "student")
    for stars in (0, 6):
        assert client.post(f"/stories/{sid}/rating", json={"stars": stars}, headers=beto).status_code == 422


def test_only_the_author_deletes_and_ratings_go_with_the_story(client, ana):
    sid = client.post("/stories", json=story(), headers=ana).json()["id"]
    beto = session(client, "beto@example.org", "researcher")
    client.post(f"/stories/{sid}/rating", json={"stars": 3}, headers=beto)
    assert client.delete(f"/stories/{sid}", headers=beto).status_code == 403
    assert client.delete(f"/stories/{sid}", headers=ana).status_code == 204
    assert client.get(f"/stories/{sid}").status_code == 404
    assert client.post(f"/stories/{sid}/rating", json={"stars": 3}, headers=beto).status_code == 404


def test_download_counts_and_returns_the_story(client, ana):
    sid = client.post("/stories", json=story(), headers=ana).json()["id"]
    beto = session(client, "beto@example.org", "student")
    client.post(f"/stories/{sid}/download", headers=beto)
    body = client.post(f"/stories/{sid}/download", headers=ana).json()
    assert body["downloads"] == 2 and body["title"] == "Agosto en Parral"


def test_list_filters_by_zone_sorts_by_stars_and_pages(client, ana):
    first = client.post("/stories", json=story(title="Primera"), headers=ana).json()["id"]
    second = client.post("/stories", json=story(title="Segunda"), headers=ana).json()["id"]
    client.post("/stories", json=story(title="Otra zona", aoi="boquilla"), headers=ana)
    beto = session(client, "beto@example.org", "student")
    client.post(f"/stories/{first}/rating", json={"stars": 5}, headers=beto)
    client.post(f"/stories/{second}/rating", json={"stars": 2}, headers=beto)

    parral = client.get("/stories", params={"aoi": "parral", "sort": "stars"}).json()
    assert parral["total"] == 2 and [s["id"] for s in parral["stories"]] == [first, second]
    page = client.get("/stories", params={"limit": 1, "offset": 1}).json()
    assert page["total"] == 3 and len(page["stories"]) == 1
    mine = client.get("/stories", params={"aoi": "parral"}, headers=beto).json()
    assert {s["id"]: s["my_stars"] for s in mine["stories"]} == {first: 5, second: 2}


@pytest.mark.parametrize(
    "over",
    [
        {"title": "ab"},
        {"title": "x" * 121},
        {"notes": "n" * (NOTES_MAX + 1)},
        {"pairs": []},
        {"pairs": [{"series": "T048A-F015", "pair": f"2026{m:04d}_2026{m:04d}"} for m in range(PAIRS_MAX + 1)]},
        {"pairs": [{"series": "T048A-F015", "pair": "20260816_20260828"}] * 2},
        {"pairs": [{"series": "T048A-F015", "pair": "agosto"}]},
        {"aoi": "../etc"},
        {"from_date": "2026-09-10", "to_date": "2026-08-01"},
    ],
)
def test_invalid_stories_are_rejected(client, ana, over):
    assert client.post("/stories", json=story(**over), headers=ana).status_code == 422


def test_the_largest_valid_story_fits_in_the_gateway_4_kb_limit():
    # Título, notas y pares al máximo, con letras de dos bytes en UTF-8 en el texto libre (RF-ACC-17).
    body = story(
        title="ñ" * 120,
        notes="á" * NOTES_MAX,
        pairs=[{"series": "S" * 32, "pair": f"2026{m:04d}_2026{m:04d}"} for m in range(PAIRS_MAX)],
    )
    size = len(json.dumps(body, ensure_ascii=False).encode("utf-8"))
    assert size <= 4096, f"{size} bytes"


def test_story_routes_declare_the_session_in_the_contract(client):
    spec = client.get("/openapi.json").json()
    assert spec["paths"]["/stories"]["post"]["x-required-role"] == "student"
    assert "x-required-role" not in spec["paths"]["/stories"]["get"]
