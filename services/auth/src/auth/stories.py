"""Historias de la comunidad (specs/06-acceso, RF-ACC-13 a 17, T-ANT-20).

Una historia guarda solo referencias (zona, serie, rango de fechas y pares) y las notas de quien la escribe.
Los textos de cada veredicto los vuelve a pedir la interfaz a la API de veredictos: así una historia guardada
nunca congela ni cambia lo que dice un veredicto. Las notas van siempre aparte y rotuladas como de su autora.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator, model_validator

from .store import RatingSummary, Store, Story, User

ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
PAIR = re.compile(r"^\d{8}_\d{8}$")
TITLE_MIN, TITLE_MAX = 3, 120
NOTES_MAX = 800
PAIRS_MAX = 24
# El gateway admite 4 KB en /api/auth/ (RF-ACC-17): con estos límites, una historia siempre cabe.

NOTES_LABEL = (
    "Notas de quien escribió la historia. No son texto de la API ni están comprobadas: se muestran y se descargan "
    "aparte de los veredictos (RF-ACC-16)."
)


def _utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_id(value: str, what: str) -> str:
    if not ID.match(value):
        raise ValueError(f"{what} no válida: letras, cifras, guion y guion bajo, hasta 32")
    return value


class StoryPair(BaseModel):
    series: str = Field(description="Serie del par, p. ej. T048A-F015.")
    pair: str = Field(description="Identificador del par, AAAAMMDD_AAAAMMDD.")

    @field_validator("series")
    @classmethod
    def _series(cls, value: str) -> str:
        return _check_id(value, "Serie")

    @field_validator("pair")
    @classmethod
    def _pair(cls, value: str) -> str:
        if not PAIR.match(value):
            raise ValueError("Par no válido: AAAAMMDD_AAAAMMDD")
        return value


class StoryIn(BaseModel):
    title: str = Field(description=f"De {TITLE_MIN} a {TITLE_MAX} caracteres.")
    aoi: str = Field(description="Zona, p. ej. parral.")
    series: str = Field(description="Serie de la búsqueda, o 'all' si abarca todas.")
    from_date: date = Field(description="Inicio del rango de fechas de la búsqueda.")
    to_date: date = Field(description="Fin del rango de fechas de la búsqueda.")
    pairs: list[StoryPair] = Field(description=f"Veredictos de la historia, de 1 a {PAIRS_MAX}, sin repetir.")
    notes: str = Field(default="", description=f"Hasta {NOTES_MAX} caracteres. {NOTES_LABEL}")

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        value = " ".join(value.split())
        if not TITLE_MIN <= len(value) <= TITLE_MAX:
            raise ValueError(f"El título debe tener de {TITLE_MIN} a {TITLE_MAX} caracteres")
        return value

    @field_validator("aoi")
    @classmethod
    def _aoi(cls, value: str) -> str:
        return _check_id(value, "Zona")

    @field_validator("series")
    @classmethod
    def _series(cls, value: str) -> str:
        return _check_id(value, "Serie")

    @field_validator("notes")
    @classmethod
    def _notes(cls, value: str) -> str:
        value = value.strip()
        if len(value) > NOTES_MAX:
            raise ValueError(f"Las notas admiten hasta {NOTES_MAX} caracteres")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> StoryIn:
        if self.from_date > self.to_date:
            raise ValueError("El inicio del rango no puede ser posterior al final")
        if not 1 <= len(self.pairs) <= PAIRS_MAX:
            raise ValueError(f"Una historia lleva de 1 a {PAIRS_MAX} pares")
        keys = [(p.series, p.pair) for p in self.pairs]
        if len(set(keys)) != len(keys):
            raise ValueError("Hay pares repetidos")
        return self


class Stars(BaseModel):
    count: int = Field(description="Cuántas valoraciones hay.")
    average: float | None = Field(description="Promedio de 1 a 5 con dos decimales, o null sin valoraciones.")


class StarsByRole(BaseModel):
    student: Stars
    researcher: Stars


class StoryRatings(Stars):
    by_role: StarsByRole = Field(description="Desglose por perfil declarado de quien valoró (RF-ACC-15).")


class StoryOut(BaseModel):
    id: str
    title: str
    aoi: str
    series: str
    from_date: str
    to_date: str
    pairs: list[StoryPair]
    notes: str = Field(description=NOTES_LABEL)
    author_role: Literal["student", "researcher"] = Field(
        description="Perfil declarado de quien la escribió. Nunca se muestra el correo (RF-ACC-16)."
    )
    author_alias: str = Field(
        description=(
            "Seudónimo estable de la cuenta autora (GL-XXXXXX, del SHA-256 de su id): identifica a quien publica "
            "sin revelar el correo (RF-ACC-16)."
        )
    )
    created_at: str = Field(description="Hora UTC de creación, ISO 8601.")
    downloads: int = Field(description="Descargas, con o sin sesión.")
    ratings: StoryRatings
    is_mine: bool = Field(description="La escribió la cuenta del token. False sin token.")
    my_stars: int | None = Field(description="Estrellas que le dio la cuenta del token, o null.")


class StoryList(BaseModel):
    stories: list[StoryOut]
    total: int = Field(description="Historias que cumplen el filtro, sin paginar.")


class RatingIn(BaseModel):
    stars: int = Field(ge=1, le=5, description="De 1 a 5.")


def _stars(summary: RatingSummary) -> Stars:
    return Stars(count=summary.count, average=summary.average)


def author_alias(author_id: str) -> str:
    """Seudónimo de la cuenta: igual en todas sus historias y sin forma de volver al correo."""
    return "GL-" + hashlib.sha256(author_id.encode("utf-8")).hexdigest()[:6].upper()


def story_out(story: Story, viewer: str | None, mine: int | None) -> StoryOut:
    return StoryOut(
        id=story.id,
        title=story.title,
        aoi=story.aoi,
        series=story.series,
        from_date=story.from_date,
        to_date=story.to_date,
        pairs=[StoryPair(**p) for p in story.pairs],
        notes=story.notes,
        author_role=story.author_role,
        author_alias=author_alias(story.author_id),
        created_at=_utc(story.created_at),
        downloads=story.downloads,
        ratings=StoryRatings(
            **_stars(story.ratings).model_dump(),
            by_role=StarsByRole(student=_stars(story.by_role["student"]), researcher=_stars(story.by_role["researcher"])),
        ),
        is_mine=viewer is not None and viewer == story.author_id,
        my_stars=mine,
    )


def story_routes(
    store: Store,
    viewer_of: Callable[[str | None], User | None],
    now: Callable[[], datetime],
) -> APIRouter:
    """`viewer_of(authorization)`: la cuenta del token, None sin cabecera; 401 si el token no vale."""
    router = APIRouter(prefix="/stories", tags=["historias"])
    session = {"security": [{"bearerAuth": []}], "x-required-role": "student"}
    no_session = {401: {"description": "Sin sesión o con un token no válido"}}
    not_found = {404: {"description": "No hay una historia con ese id"}}

    def account(authorization: str | None) -> User:
        user = viewer_of(authorization)
        if user is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Hace falta iniciar sesión con una cuenta de estudiante o de investigación",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    def existing(story_id: str) -> Story:
        story = store.story(story_id)
        if story is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay una historia con ese id")
        return story

    def out(story: Story, user: User | None) -> StoryOut:
        mine = store.my_stars([story.id], user.id).get(story.id) if user else None
        return story_out(story, user.id if user else None, mine)

    @router.get("", response_model=StoryList, responses=no_session)
    def list_stories(
        aoi: str | None = Query(default=None, description="Solo las de esta zona."),
        sort: Literal["recent", "stars"] = Query(default="recent", description="Más nuevas o mejor valoradas."),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        authorization: str | None = Header(default=None),
    ) -> StoryList:
        """Sin cuenta (RF-ACC-14). Con token, cada historia dice si es propia y cuántas estrellas le diste."""
        user = viewer_of(authorization)
        stories, total = store.stories(aoi, sort, limit, offset)
        mine = store.my_stars([s.id for s in stories], user.id) if user else {}
        return StoryList(stories=[story_out(s, user.id if user else None, mine.get(s.id)) for s in stories], total=total)

    @router.get("/{story_id}", response_model=StoryOut, responses={**no_session, **not_found})
    def get_story(story_id: str, authorization: str | None = Header(default=None)) -> StoryOut:
        user = viewer_of(authorization)
        return out(existing(story_id), user)

    @router.post(
        "",
        status_code=status.HTTP_201_CREATED,
        response_model=StoryOut,
        responses=no_session,
        openapi_extra=session,
    )
    def create_story(body: StoryIn, authorization: str | None = Header(default=None)) -> StoryOut:
        """Guarda las referencias y las notas; nunca textos de veredictos (RF-ACC-13)."""
        user = account(authorization)
        fields = body.model_dump()
        fields["from_date"] = body.from_date.isoformat()
        fields["to_date"] = body.to_date.isoformat()
        return out(store.create_story(user, fields, now()), user)

    @router.delete(
        "/{story_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={**no_session, **not_found, 403: {"description": "La historia es de otra cuenta"}},
        openapi_extra=session,
    )
    def delete_story(story_id: str, authorization: str | None = Header(default=None)) -> Response:
        user = account(authorization)
        if existing(story_id).author_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo quien escribió la historia puede borrarla")
        store.delete_story(story_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/{story_id}/rating",
        response_model=StoryOut,
        responses={**no_session, **not_found, 409: {"description": "No se puede valorar la historia propia"}},
        openapi_extra=session,
    )
    def rate(story_id: str, body: RatingIn, authorization: str | None = Header(default=None)) -> StoryOut:
        """De 1 a 5 estrellas, una por cuenta (valorar otra vez la cambia). Devuelve la historia con el promedio nuevo."""
        user = account(authorization)
        if existing(story_id).author_id == user.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "No se puede valorar la historia propia")
        store.rate_story(story_id, user, body.stars, now())
        return out(existing(story_id), user)

    @router.delete(
        "/{story_id}/rating",
        response_model=StoryOut,
        responses={**no_session, **not_found},
        openapi_extra=session,
    )
    def unrate(story_id: str, authorization: str | None = Header(default=None)) -> StoryOut:
        """Quita la valoración de la cuenta, si la había."""
        user = account(authorization)
        existing(story_id)
        store.unrate_story(story_id, user.id)
        return out(existing(story_id), user)

    @router.post(
        "/{story_id}/download",
        response_model=StoryOut,
        responses={**not_found},
    )
    def download(story_id: str, authorization: str | None = Header(default=None)) -> StoryOut:
        """Cuenta la descarga y devuelve la historia. El archivo lo arma la interfaz con los veredictos actuales de la
        API y las notas aparte. Desde el 2026-11-14 no pide sesión: toda la información es pública y la cuenta solo
        hace falta para publicar, valorar y borrar (constitución II.4)."""
        user = viewer_of(authorization)
        existing(story_id)
        store.count_download(story_id)
        return out(existing(story_id), user)

    return router
