"""Cuentas de prueba con contraseñas del `.env` (T-ANT-15, specs/06-acceso).

No hay perfil de administración en la API: las cuentas de prueba se crean con esta orden, que habla
directamente con la base de datos del servicio. Solo lee las variables `AUTH_TEST_*`; nunca imprime
una contraseña.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from .store import Store

MIN_PASSWORD = 12
PREFIX = "AUTH_TEST_"
ROLES = {
    "student": ("AUTH_TEST_STUDENT_EMAIL", "AUTH_TEST_STUDENT_PASSWORD", "estudiante@prueba.test"),
    "researcher": ("AUTH_TEST_RESEARCHER_EMAIL", "AUTH_TEST_RESEARCHER_PASSWORD", "investigacion@prueba.test"),
}


@dataclass(frozen=True)
class Outcome:
    role: str
    email: str
    status: str  # created, updated, unchanged, skipped_role, invalid
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status in ("created", "updated", "unchanged")


def read_env_file(path: Path) -> dict[str, str]:
    """Las variables `AUTH_TEST_*` de un archivo .env (KEY=valor, comentarios con #, comillas opcionales)."""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        if not key.startswith(PREFIX):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def settings(environ: Mapping[str, str], env_file: Path | None) -> dict[str, str]:
    """Las variables del archivo, con las del entorno por encima. Solo `AUTH_TEST_*`."""
    merged = read_env_file(env_file) if env_file else {}
    merged.update({k: v for k, v in environ.items() if k.startswith(PREFIX)})
    return merged


def seed(
    store: Store,
    config: Mapping[str, str],
    hasher: PasswordHasher | None = None,
    now: Callable[[], datetime] | None = None,
) -> list[Outcome]:
    """Crea o actualiza una cuenta por perfil con contraseña configurada. Idempotente."""
    hasher = hasher or PasswordHasher()
    now = now or (lambda: datetime.now(timezone.utc))
    outcomes = []
    for role, (email_var, password_var, default_email) in ROLES.items():
        password = config.get(password_var, "")
        if not password:
            continue
        email = (config.get(email_var) or default_email).strip().lower()
        if len(password) < MIN_PASSWORD:
            outcomes.append(Outcome(role, email, "invalid", f"{password_var} tiene menos de {MIN_PASSWORD} caracteres"))
            continue
        user = store.user_by_email(email)
        if user is None:
            store.create_user(email, hasher.hash(password), role, now())
            outcomes.append(Outcome(role, email, "created"))
        elif user.role != role:
            outcomes.append(
                Outcome(role, email, "skipped_role", f"ya existe con el perfil {user.role}; no se cambia en silencio")
            )
        elif _matches(hasher, user.password_hash, password):
            outcomes.append(Outcome(role, email, "unchanged"))
        else:
            store.update_password_hash(user.id, hasher.hash(password))
            outcomes.append(Outcome(role, email, "updated", "contraseña cambiada a la del .env"))
    return outcomes


def _matches(hasher: PasswordHasher, password_hash: str, password: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


MESSAGES = {
    "created": "creada",
    "updated": "actualizada",
    "unchanged": "sin cambios",
    "skipped_role": "NO TOCADA",
    "invalid": "NO CREADA",
}


def main(argv: list[str], environ: Mapping[str, str] | None = None) -> int:
    environ = os.environ if environ is None else environ
    env_file = None
    if argv[:1] == ["--env-file"] and len(argv) == 2:
        env_file = Path(argv[1])
    elif argv:
        print("Uso: python -m auth seed-accounts [--env-file RUTA]")
        return 2
    if env_file is not None and not env_file.is_file():
        print(f"No existe {env_file}")
        return 2
    config = settings(environ, env_file)
    if not any(config.get(password_var) for _, password_var, _ in ROLES.values()):
        print("Sin contraseñas de prueba: define AUTH_TEST_STUDENT_PASSWORD o AUTH_TEST_RESEARCHER_PASSWORD en el .env.")
        return 1
    store = Store(Path(environ.get("AUTH_DATA_DIR", "data/auth")))
    try:
        outcomes = seed(store, config)
    finally:
        store.close()
    for item in outcomes:
        detail = f" ({item.detail})" if item.detail else ""
        print(f"{item.role:<10} {item.email}: {MESSAGES[item.status]}{detail}")
    return 0 if all(item.ok for item in outcomes) else 1
