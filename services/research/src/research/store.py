"""Persistencia en SQLite: investigaciones e historias como documentos JSON con su versión.

Cada documento guarda todo lo necesario para reproducirlo: la pregunta, el plan, las respuestas normalizadas de
cada proveedor con su procedencia y los cálculos. Borrar la caché de otros servicios no borra esto.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
import threading
import uuid
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS research (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  doc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stories (
  id TEXT PRIMARY KEY,
  research_id TEXT NOT NULL REFERENCES research(id),
  created_at TEXT NOT NULL,
  doc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS stories_research ON stories(research_id);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""
SCHEMA_VERSION = "1"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.executescript(SCHEMA)
        self._db.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)", (SCHEMA_VERSION,))
        self._db.commit()

    def create_research(self, doc: dict) -> dict:
        doc = {**doc, "id": doc.get("id") or "R-" + uuid.uuid4().hex[:10], "created_at": now(), "updated_at": now()}
        with self._lock:
            self._db.execute("INSERT INTO research VALUES (?, ?, ?, ?)", (doc["id"], doc["created_at"], doc["updated_at"], json.dumps(doc)))
            self._db.commit()
        return doc

    def get_research(self, rid: str) -> dict | None:
        row = self._db.execute("SELECT doc FROM research WHERE id = ?", (rid,)).fetchone()
        return json.loads(row[0]) if row else None

    def save_research(self, doc: dict) -> dict:
        doc["updated_at"] = now()
        with self._lock:
            self._db.execute("UPDATE research SET updated_at = ?, doc = ? WHERE id = ?", (doc["updated_at"], json.dumps(doc), doc["id"]))
            self._db.commit()
        return doc

    def list_research(self, limit: int = 50) -> list[dict]:
        rows = self._db.execute("SELECT doc FROM research ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def create_story(self, story: dict) -> dict:
        story = {**story, "id": "S-" + uuid.uuid4().hex[:10], "created_at": now()}
        with self._lock:
            self._db.execute("INSERT INTO stories VALUES (?, ?, ?, ?)", (story["id"], story["research_id"], story["created_at"], json.dumps(story)))
            self._db.commit()
        return story

    def get_story(self, sid: str) -> dict | None:
        row = self._db.execute("SELECT doc FROM stories WHERE id = ?", (sid,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_stories(self, research_id: str | None = None, limit: int = 50) -> list[dict]:
        if research_id:
            rows = self._db.execute("SELECT doc FROM stories WHERE research_id = ? ORDER BY created_at DESC LIMIT ?", (research_id, limit)).fetchall()
        else:
            rows = self._db.execute("SELECT doc FROM stories ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(r[0]) for r in rows]
