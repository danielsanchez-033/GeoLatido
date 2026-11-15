"""Clave Ed25519 y tokens de acceso JWT (RF-ACC-02)."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ISSUER = "nisar-veredictos"
AUDIENCE = "nisar-api"
ACCESS_SECONDS = 15 * 60
ROLES = ("student", "researcher")
KEY_FILE = "ed25519.pem"

log = logging.getLogger("auth")


class InvalidToken(Exception):
    """Token roto, caducado, con otra firma, otra audiencia o sin los campos que exige el servicio."""


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def load_or_create_key(data_dir: Path, pem: str | None = None) -> Ed25519PrivateKey:
    """La clave de `AUTH_PRIVATE_KEY` si viene; si no, la del volumen; si no hay, se genera y se avisa.

    Nunca se escribe en el repositorio: el volumen está en `data/`, que git ignora.
    """
    if pem:
        key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("AUTH_PRIVATE_KEY no es una clave Ed25519")
        return key
    path = data_dir / KEY_FILE
    if path.exists():
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError(f"{path} no es una clave Ed25519")
        return key
    data_dir.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    # Se crea con permisos solo para el dueño antes de escribir la clave.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
    log.warning("Sin AUTH_PRIVATE_KEY: se generó una clave de firma nueva en %s", path)
    return key


@dataclass(frozen=True)
class Claims:
    sub: str
    role: str


class Signer:
    def __init__(self, key: Ed25519PrivateKey):
        self._key = key
        self._public: Ed25519PublicKey = key.public_key()
        raw = self._public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self._x = _b64url(raw)
        # Huella RFC 7638: SHA-256 del JWK con sus campos obligatorios en orden.
        thumb = json.dumps({"crv": "Ed25519", "kty": "OKP", "x": self._x}, separators=(",", ":"), sort_keys=True)
        self.kid = _b64url(hashlib.sha256(thumb.encode("utf-8")).digest())

    def jwks(self) -> dict:
        return {"keys": [{"kty": "OKP", "crv": "Ed25519", "x": self._x, "kid": self.kid, "alg": "EdDSA", "use": "sig"}]}

    def issue(self, sub: str, role: str, now: datetime) -> str:
        if role not in ROLES:
            raise ValueError(f"Perfil sin token: {role}")
        payload = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": sub,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ACCESS_SECONDS)).timestamp()),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self._key, algorithm="EdDSA", headers={"kid": self.kid})

    def verify(self, token: str, now: datetime) -> Claims:
        try:
            payload = self._decode(token, now)
        except jwt.PyJWTError as error:
            raise InvalidToken(str(error)) from error
        if payload.get("role") not in ROLES or not isinstance(payload.get("sub"), str):
            raise InvalidToken("Perfil o sujeto no válidos")
        return Claims(sub=payload["sub"], role=payload["role"])

    def _decode(self, token: str, now: datetime) -> dict:
        payload = jwt.decode(
            token,
            self._public,
            algorithms=["EdDSA"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["iss", "aud", "sub", "role", "iat", "exp", "jti"], "verify_exp": False, "verify_iat": False},
        )
        # La caducidad se comprueba aquí con el reloj del servicio, para poder probarla sin esperar.
        if int(payload["exp"]) <= int(now.timestamp()):
            raise jwt.ExpiredSignatureError("El token caducó")
        return payload
