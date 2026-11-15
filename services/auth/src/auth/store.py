"""Cuentas y sesiones en SQLite (RF-ACC-03 y 04). De los tokens de renovación solo se guarda el hash."""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

REFRESH_DAYS = 7
DB_FILE = "auth.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS families (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL,
  revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS refresh_tokens (
  hash TEXT PRIMARY KEY,
  family_id TEXT NOT NULL REFERENCES families(id),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  rotated_at TEXT
);
CREATE TABLE IF NOT EXISTS personal_tokens (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  hash TEXT NOT NULL UNIQUE,
  prefix TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT
);
CREATE INDEX IF NOT EXISTS personal_tokens_user ON personal_tokens(user_id);
-- Historias de la comunidad (RF-ACC-13 a 17, T-ANT-20). Solo referencias a veredictos: nunca sus textos.
CREATE TABLE IF NOT EXISTS stories (
  id TEXT PRIMARY KEY,
  author_id TEXT NOT NULL REFERENCES users(id),
  author_role TEXT NOT NULL,
  title TEXT NOT NULL,
  aoi TEXT NOT NULL,
  series TEXT NOT NULL,
  from_date TEXT NOT NULL,
  to_date TEXT NOT NULL,
  pairs TEXT NOT NULL,
  notes TEXT NOT NULL,
  created_at TEXT NOT NULL,
  downloads INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS stories_aoi ON stories(aoi, created_at);
CREATE TABLE IF NOT EXISTS story_ratings (
  story_id TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id),
  role TEXT NOT NULL,
  stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
  updated_at TEXT NOT NULL,
  PRIMARY KEY (story_id, user_id)
);
"""

# Tokens personales para scripts (RF-ACC-11, T-ANT-18): opacos, con prefijo para reconocerlos y distinguirlos
# de un JWT, y de ellos solo se guarda el SHA-256.
PERSONAL_PREFIX = "nvp_"
PERSONAL_MAX_DAYS = 90
PERSONAL_MAX_ACTIVE = 10


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class User:
    id: str
    email: str
    password_hash: str
    role: str
    created_at: datetime


@dataclass(frozen=True)
class PersonalToken:
    id: str
    user_id: str
    name: str
    prefix: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None

    def status(self, now: datetime) -> str:
        if self.revoked_at is not None:
            return "revoked"
        return "expired" if self.expires_at <= now else "active"


@dataclass(frozen=True)
class RatingSummary:
    count: int
    average: float | None


@dataclass(frozen=True)
class Story:
    id: str
    author_id: str
    author_role: str
    title: str
    aoi: str
    series: str
    from_date: str
    to_date: str
    pairs: list[dict[str, str]]
    notes: str
    created_at: datetime
    downloads: int
    ratings: RatingSummary
    by_role: dict[str, RatingSummary]


# Historia con sus estrellas agregadas: total y desglose por perfil declarado (RF-ACC-15).
STORY_SELECT = """
SELECT s.*,
  COUNT(r.stars) AS n, SUM(r.stars) AS total,
  SUM(CASE WHEN r.role = 'student' THEN 1 ELSE 0 END) AS n_student,
  SUM(CASE WHEN r.role = 'student' THEN r.stars END) AS total_student,
  SUM(CASE WHEN r.role = 'researcher' THEN 1 ELSE 0 END) AS n_researcher,
  SUM(CASE WHEN r.role = 'researcher' THEN r.stars END) AS total_researcher
FROM stories s LEFT JOIN story_ratings r ON r.story_id = s.id
"""


class RefreshRejected(Exception):
    """Token de renovación inexistente, caducado, revocado o reutilizado."""


class PersonalTokenRejected(Exception):
    """Token personal inexistente, revocado, caducado o de una cuenta que ya no puede tenerlo."""


class TooManyPersonalTokens(Exception):
    """La cuenta ya tiene el máximo de tokens personales activos."""


class Store:
    def __init__(self, data_dir: Path):
        data_dir.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(data_dir / DB_FILE, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(SCHEMA)
        self._lock = threading.Lock()

    def close(self) -> None:
        self._db.close()

    # --- Cuentas ---

    def create_user(self, email: str, password_hash: str, role: str, now: datetime) -> User | None:
        """La cuenta nueva, o None si ya existe una con ese correo."""
        user = User(str(uuid.uuid4()), email, password_hash, role, now)
        with self._lock, self._db:
            try:
                self._db.execute(
                    "INSERT INTO users (id, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                    (user.id, email, password_hash, role, now.isoformat()),
                )
            except sqlite3.IntegrityError:
                return None
        return user

    def user_by_email(self, email: str) -> User | None:
        return self._user("SELECT * FROM users WHERE email = ?", email)

    def user_by_id(self, user_id: str) -> User | None:
        return self._user("SELECT * FROM users WHERE id = ?", user_id)

    def update_password_hash(self, user_id: str, password_hash: str) -> None:
        with self._lock, self._db:
            self._db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))

    def _user(self, query: str, value: str) -> User | None:
        with self._lock:
            row = self._db.execute(query, (value,)).fetchone()
        if row is None:
            return None
        return User(row["id"], row["email"], row["password_hash"], row["role"], datetime.fromisoformat(row["created_at"]))

    # --- Sesiones ---

    def start_session(self, user_id: str, now: datetime) -> str:
        """Familia nueva con su primer token de renovación, que se devuelve en claro una sola vez."""
        family = str(uuid.uuid4())
        with self._lock, self._db:
            self._db.execute("INSERT INTO families (id, user_id, created_at) VALUES (?, ?, ?)", (family, user_id, now.isoformat()))
            return self._new_token(family, now)

    def rotate(self, token: str, now: datetime) -> tuple[str, str]:
        """(token nuevo, user_id). Reutilizar un token ya rotado revoca toda su familia."""
        rejected: str | None = None
        with self._lock, self._db:
            row = self._db.execute(
                "SELECT t.family_id, t.expires_at, t.rotated_at, f.user_id, f.revoked_at "
                "FROM refresh_tokens t JOIN families f ON f.id = t.family_id WHERE t.hash = ?",
                (hash_token(token),),
            ).fetchone()
            if row is None or row["revoked_at"] is not None:
                rejected = "Sesión inexistente o cerrada"
            elif row["rotated_at"] is not None:
                # La revocación se guarda al salir del bloque; la excepción va fuera para no deshacerla.
                self._db.execute("UPDATE families SET revoked_at = ? WHERE id = ?", (now.isoformat(), row["family_id"]))
                rejected = "Token de renovación reutilizado: se cerró la sesión"
            elif datetime.fromisoformat(row["expires_at"]) <= now:
                rejected = "Sesión caducada"
            else:
                self._db.execute(
                    "UPDATE refresh_tokens SET rotated_at = ? WHERE hash = ?", (now.isoformat(), hash_token(token))
                )
                return self._new_token(row["family_id"], now), row["user_id"]
        raise RefreshRejected(rejected)

    def revoke(self, token: str, now: datetime) -> None:
        with self._lock, self._db:
            row = self._db.execute("SELECT family_id FROM refresh_tokens WHERE hash = ?", (hash_token(token),)).fetchone()
            if row is not None:
                self._db.execute(
                    "UPDATE families SET revoked_at = COALESCE(revoked_at, ?) WHERE id = ?", (now.isoformat(), row["family_id"])
                )

    # --- Tokens personales (T-ANT-18) ---

    def create_personal_token(self, user_id: str, name: str, days: int, now: datetime) -> tuple[str, PersonalToken]:
        """(token en claro, que solo se devuelve aquí, y su ficha). Como mucho PERSONAL_MAX_ACTIVE activos."""
        if not 1 <= days <= PERSONAL_MAX_DAYS:
            raise ValueError(f"La vida debe ir de 1 a {PERSONAL_MAX_DAYS} días")
        token = PERSONAL_PREFIX + secrets.token_urlsafe(32)
        item = PersonalToken(
            str(uuid.uuid4()), user_id, name, token[: len(PERSONAL_PREFIX) + 6], now, now + timedelta(days=days), None
        )
        with self._lock, self._db:
            active = self._db.execute(
                "SELECT COUNT(*) FROM personal_tokens WHERE user_id = ? AND revoked_at IS NULL AND expires_at > ?",
                (user_id, now.isoformat()),
            ).fetchone()[0]
            if active >= PERSONAL_MAX_ACTIVE:
                raise TooManyPersonalTokens(f"Ya hay {active} tokens personales activos; revoca alguno antes")
            self._db.execute(
                "INSERT INTO personal_tokens (id, user_id, name, hash, prefix, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (item.id, user_id, name, hash_token(token), item.prefix, now.isoformat(), item.expires_at.isoformat()),
            )
        return token, item

    def personal_tokens(self, user_id: str) -> list[PersonalToken]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM personal_tokens WHERE user_id = ? ORDER BY created_at DESC, id", (user_id,)
            ).fetchall()
        return [self._personal(row) for row in rows]

    def revoke_personal_token(self, user_id: str, token_id: str, now: datetime) -> bool:
        """True si el token existe y es de esa cuenta (revocarlo dos veces no cambia la fecha)."""
        with self._lock, self._db:
            cursor = self._db.execute(
                "UPDATE personal_tokens SET revoked_at = COALESCE(revoked_at, ?) WHERE id = ? AND user_id = ?",
                (now.isoformat(), token_id, user_id),
            )
            return cursor.rowcount == 1

    def check_personal_token(self, token: str, now: datetime) -> User:
        """La cuenta dueña de un token personal válido. Busca por hash: una lectura por clave única."""
        with self._lock:
            row = self._db.execute(
                "SELECT t.expires_at, t.revoked_at, u.* FROM personal_tokens t JOIN users u ON u.id = t.user_id WHERE t.hash = ?",
                (hash_token(token),),
            ).fetchone()
        if row is None:
            raise PersonalTokenRejected("Token personal inexistente")
        if row["revoked_at"] is not None:
            raise PersonalTokenRejected("Token personal revocado")
        if datetime.fromisoformat(row["expires_at"]) <= now:
            raise PersonalTokenRejected("Token personal caducado")
        if row["role"] != "researcher":
            raise PersonalTokenRejected("La cuenta ya no tiene el perfil researcher")
        return User(row["id"], row["email"], row["password_hash"], row["role"], datetime.fromisoformat(row["created_at"]))

    # --- Historias de la comunidad (T-ANT-20) ---

    def create_story(self, author: User, fields: dict, now: datetime) -> Story:
        """Guarda una historia. `fields` ya viene validado: title, aoi, series, from_date, to_date, pairs y notes."""
        story_id = str(uuid.uuid4())
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO stories (id, author_id, author_role, title, aoi, series, from_date, to_date, pairs, notes,"
                " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    story_id,
                    author.id,
                    author.role,
                    fields["title"],
                    fields["aoi"],
                    fields["series"],
                    fields["from_date"],
                    fields["to_date"],
                    json.dumps(fields["pairs"], separators=(",", ":")),
                    fields["notes"],
                    now.isoformat(),
                ),
            )
        story = self.story(story_id)
        assert story is not None
        return story

    def story(self, story_id: str) -> Story | None:
        with self._lock:
            row = self._db.execute(f"{STORY_SELECT} WHERE s.id = ? GROUP BY s.id", (story_id,)).fetchone()
            return self._story(row) if row else None

    def stories(self, aoi: str | None, sort: str, limit: int, offset: int) -> tuple[list[Story], int]:
        """(página de historias, total). `sort`: recent (más nuevas) o stars (mejor promedio, luego más votos)."""
        where, params = ("WHERE s.aoi = ?", [aoi]) if aoi else ("", [])
        order = "s.created_at DESC" if sort == "recent" else "AVG(r.stars) IS NULL, AVG(r.stars) DESC, COUNT(r.stars) DESC, s.created_at DESC"
        with self._lock:
            total = self._db.execute(f"SELECT COUNT(*) FROM stories s {where}", params).fetchone()[0]
            rows = self._db.execute(
                f"{STORY_SELECT} {where} GROUP BY s.id ORDER BY {order}, s.id LIMIT ? OFFSET ?", [*params, limit, offset]
            ).fetchall()
            return [self._story(row) for row in rows], total

    def delete_story(self, story_id: str) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM story_ratings WHERE story_id = ?", (story_id,))
            self._db.execute("DELETE FROM stories WHERE id = ?", (story_id,))

    def rate_story(self, story_id: str, user: User, stars: int, now: datetime) -> None:
        """Una valoración por cuenta e historia: valorar otra vez la sustituye."""
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO story_ratings (story_id, user_id, role, stars, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (story_id, user_id) DO UPDATE SET stars = excluded.stars, role = excluded.role, "
                "updated_at = excluded.updated_at",
                (story_id, user.id, user.role, stars, now.isoformat()),
            )

    def unrate_story(self, story_id: str, user_id: str) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM story_ratings WHERE story_id = ? AND user_id = ?", (story_id, user_id))

    def my_stars(self, story_ids: list[str], user_id: str) -> dict[str, int]:
        if not story_ids:
            return {}
        marks = ",".join("?" for _ in story_ids)
        with self._lock:
            rows = self._db.execute(
                f"SELECT story_id, stars FROM story_ratings WHERE user_id = ? AND story_id IN ({marks})", [user_id, *story_ids]
            ).fetchall()
        return {row["story_id"]: row["stars"] for row in rows}

    def count_download(self, story_id: str) -> None:
        with self._lock, self._db:
            self._db.execute("UPDATE stories SET downloads = downloads + 1 WHERE id = ?", (story_id,))

    @staticmethod
    def _story(row: sqlite3.Row) -> Story:
        def summary(count: int, total: int | None) -> RatingSummary:
            return RatingSummary(count, round(total / count, 2) if count and total is not None else None)

        return Story(
            id=row["id"],
            author_id=row["author_id"],
            author_role=row["author_role"],
            title=row["title"],
            aoi=row["aoi"],
            series=row["series"],
            from_date=row["from_date"],
            to_date=row["to_date"],
            pairs=json.loads(row["pairs"]),
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            downloads=row["downloads"],
            ratings=summary(row["n"], row["total"]),
            by_role={
                "student": summary(row["n_student"], row["total_student"]),
                "researcher": summary(row["n_researcher"], row["total_researcher"]),
            },
        )

    @staticmethod
    def _personal(row: sqlite3.Row) -> PersonalToken:
        return PersonalToken(
            row["id"],
            row["user_id"],
            row["name"],
            row["prefix"],
            datetime.fromisoformat(row["created_at"]),
            datetime.fromisoformat(row["expires_at"]),
            datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
        )

    def _new_token(self, family: str, now: datetime) -> str:
        token = secrets.token_urlsafe(32)
        self._db.execute(
            "INSERT INTO refresh_tokens (hash, family_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (hash_token(token), family, now.isoformat(), (now + timedelta(days=REFRESH_DAYS)).isoformat()),
        )
        return token
