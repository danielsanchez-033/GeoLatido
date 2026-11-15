"""Cuentas de prueba con contraseñas del .env (T-ANT-15)."""
from datetime import datetime, timezone

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from auth import __main__ as cli
from auth.main import create_app
from auth.seed import read_env_file, seed, settings
from auth.store import Store

T0 = datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc)
STUDENT = "frase larga de estudiante"
RESEARCHER = "frase larga de investigacion"
# Argon2 con coste mínimo: las pruebas comprueban la lógica, no el coste del hash.
FAST = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)


def run(store, **config):
    return seed(store, config, hasher=FAST, now=lambda: T0)


def test_creates_one_account_per_role_that_can_log_in(tmp_path):
    store = Store(tmp_path)
    outcomes = run(store, AUTH_TEST_STUDENT_PASSWORD=STUDENT, AUTH_TEST_RESEARCHER_PASSWORD=RESEARCHER)
    store.close()
    assert [(o.role, o.email, o.status) for o in outcomes] == [
        ("student", "estudiante@prueba.test", "created"),
        ("researcher", "investigacion@prueba.test", "created"),
    ]
    client = TestClient(create_app(data_dir=tmp_path, cookie_secure="false", cookie_path="/"))
    for email, password, role in [
        ("estudiante@prueba.test", STUDENT, "student"),
        ("investigacion@prueba.test", RESEARCHER, "researcher"),
    ]:
        response = client.post("/login", json={"email": email, "password": password})
        assert response.status_code == 200 and response.json()["role"] == role


def test_is_idempotent_and_follows_password_changes(tmp_path):
    store = Store(tmp_path)
    run(store, AUTH_TEST_STUDENT_PASSWORD=STUDENT)
    assert run(store, AUTH_TEST_STUDENT_PASSWORD=STUDENT)[0].status == "unchanged"
    assert run(store, AUTH_TEST_STUDENT_PASSWORD="otra frase larga distinta")[0].status == "updated"
    user = store.user_by_email("estudiante@prueba.test")
    assert FAST.verify(user.password_hash, "otra frase larga distinta")


def test_custom_email_is_normalized(tmp_path):
    store = Store(tmp_path)
    outcome = run(store, AUTH_TEST_RESEARCHER_EMAIL=" Demo@Equipo.Test ", AUTH_TEST_RESEARCHER_PASSWORD=RESEARCHER)[0]
    assert outcome.email == "demo@equipo.test" and store.user_by_email("demo@equipo.test").role == "researcher"


def test_never_changes_the_role_of_an_existing_account(tmp_path):
    store = Store(tmp_path)
    store.create_user("estudiante@prueba.test", FAST.hash(STUDENT), "researcher", T0)
    outcome = run(store, AUTH_TEST_STUDENT_PASSWORD=STUDENT)[0]
    assert outcome.status == "skipped_role" and not outcome.ok
    assert store.user_by_email("estudiante@prueba.test").role == "researcher"


def test_rejects_short_passwords_like_the_api(tmp_path):
    store = Store(tmp_path)
    outcome = run(store, AUTH_TEST_STUDENT_PASSWORD="corta")[0]
    assert outcome.status == "invalid" and store.user_by_email("estudiante@prueba.test") is None


def test_env_file_only_yields_auth_test_variables(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# comentario\nEARTHDATA_TOKEN=secreto\nexport AUTH_TEST_STUDENT_PASSWORD='frase con comillas'\n"
        'AUTH_TEST_RESEARCHER_EMAIL="r@x.test"\nSIN_IGUAL\n',
        encoding="utf-8",
    )
    assert read_env_file(env) == {
        "AUTH_TEST_STUDENT_PASSWORD": "frase con comillas",
        "AUTH_TEST_RESEARCHER_EMAIL": "r@x.test",
    }
    merged = settings({"AUTH_TEST_STUDENT_PASSWORD": "del entorno manda", "PATH": "/bin"}, env)
    assert merged["AUTH_TEST_STUDENT_PASSWORD"] == "del entorno manda" and "PATH" not in merged


def test_cli_prints_no_passwords_and_reports_failures(tmp_path, capsys):
    data = tmp_path / "data"
    env = {"AUTH_DATA_DIR": str(data), "AUTH_TEST_STUDENT_PASSWORD": STUDENT, "AUTH_TEST_RESEARCHER_PASSWORD": "corta"}
    from auth import seed as seed_module

    assert seed_module.main([], environ=env) == 1
    out = capsys.readouterr().out
    assert "estudiante@prueba.test: creada" in out and "NO CREADA" in out
    assert STUDENT not in out and "corta" not in out


def test_cli_without_passwords_or_with_bad_arguments(tmp_path, capsys):
    from auth import seed as seed_module

    assert seed_module.main([], environ={"AUTH_DATA_DIR": str(tmp_path)}) == 1
    assert seed_module.main(["--env-file", str(tmp_path / "no-existe")], environ={}) == 2
    assert cli.main(["otra-orden"]) == 2
    assert "AUTH_TEST_STUDENT_PASSWORD" in capsys.readouterr().out
